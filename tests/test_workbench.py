import asyncio
import json
import unittest
from unittest.mock import patch, MagicMock

from langchain_core.messages import AIMessageChunk, ToolMessage
from src.graphs.supervisor_graph import SupervisorGraph
from src.tools.builtin_tools import calculator
from src.models.schemas import ChatRequest
from src.api import chat_router, knowledge_router
from src.rag.document_loader import DocumentLoader
from src.rag.retriever import AgenticRetriever, terms


class FakeLLM:
    def __init__(self, chunks, seen): self.chunks, self.seen = chunks, seen
    async def astream(self, messages):
        self.seen.append(messages[:])
        for chunk in self.chunks:
            await asyncio.sleep(0)
            yield chunk


class WorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def test_fragmented_tools_results_feed_back_before_final_answer(self):
        seen = []
        turns = [
            [AIMessageChunk(content='先计算', tool_call_chunks=[{'name': 'calculator', 'id': 't1', 'index': 0, 'args': '{"expression":'}]),
             AIMessageChunk(content='', tool_call_chunks=[{'name': None, 'id': None, 'index': 0, 'args': '"123*456"}'}])],
            [AIMessageChunk(content='结果是 56088。')],
        ]
        def llm(**kwargs): return FakeLLM(turns.pop(0), seen)
        with patch('src.graphs.supervisor_graph.build_llm', side_effect=llm):
            events = [e async for e in SupervisorGraph().stream_process('123乘456', 's', 'c', mode='chat')]
        self.assertEqual(sum(e['type'] == 'reset' for e in events), 1)
        self.assertEqual(events[-1]['type'], 'done')
        self.assertTrue(any(isinstance(m, ToolMessage) and '56088' in m.content for m in seen[1]))
        self.assertEqual([e['metadata']['status'] for e in events if e['type'] == 'tool'], ['running', 'completed'])

    async def test_nonstream_uses_same_workflow_and_zero_argument_tools(self):
        seen = []
        turns = [[AIMessageChunk(content='', tool_calls=[{'name': 'get_current_time', 'args': {}, 'id': 'time'}])],
                 [AIMessageChunk(content='已查到时间。')]]
        with patch('src.graphs.supervisor_graph.build_llm', side_effect=lambda **kw: FakeLLM(turns.pop(0), seen)):
            result = await SupervisorGraph().aprocess(user_message='时间', session_id='s', conversation_id='c', mode='chat')
        self.assertEqual(result['response'], '已查到时间。')
        self.assertEqual(result['tool_calls'][0]['status'], 'completed')

    async def test_selected_documents_and_sources_reach_the_prompt(self):
        seen = []
        result = {'results': [{'id': 'x', 'content': '退款需在7天内申请。', 'metadata': {'document_id': 'doc', 'filename': '政策.md', 'chunk_index': 2}}]}
        with patch('src.graphs.supervisor_graph.agentic_retriever.retrieve', return_value=result) as retrieve, patch('src.graphs.supervisor_graph.build_llm', return_value=FakeLLM([AIMessageChunk(content='7天内 [1]。')], seen)):
            output = await SupervisorGraph().aprocess(user_message='退款', session_id='s', conversation_id='c', document_ids=['doc'])
        retrieve.assert_called_once_with('退款', ['doc'])
        self.assertEqual(output['sources'][0]['document_id'], 'doc')
        self.assertIn('退款需在7天内', seen[0][0].content)

    async def test_provider_failure_terminates_with_error_not_done(self):
        with self.assertLogs('src.graphs.supervisor_graph', level='ERROR'), patch('src.graphs.supervisor_graph.build_llm', side_effect=RuntimeError('provider failed')):
            events = [e async for e in SupervisorGraph().stream_process('hi', 's', 'c', mode='chat')]
        self.assertEqual(events[-1]['type'], 'error')
        self.assertFalse(any(e['type'] == 'done' for e in events))


class ChatPersistenceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        chat_router._active_conversations.clear()
        self.db = MagicMock()
        self.db.get_conversation.return_value = {'id': 'c', 'session_id': 's', 'status': 'active'}
        self.db.get_messages.return_value = [{'role': 'user', 'content': 'previous'}]
        self.db.save_message.side_effect = [1, 2]

    async def test_stop_immediately_after_session_persists_and_unlocks(self):
        with patch.object(chat_router, 'mysql_client', self.db):
            response = await chat_router.chat(ChatRequest(message='new', conversation_id='c', mode='chat'))
            frame = await anext(response.body_iterator)
            self.assertIn('event: session', frame)
            await response.body_iterator.aclose()
            self.assertFalse(chat_router._active_conversations)
            self.assertEqual(self.db.update_message.call_args.args[-1]['status'], 'stopped')

    async def test_sources_tools_and_partial_text_persist_on_stop(self):
        async def fake(**kwargs):
            yield {'type': 'token', 'content': 'partial'}
            yield {'type': 'sources', 'metadata': {'sources': [{'number': 1}]}}
            yield {'type': 'tool', 'metadata': {'id': 't', 'status': 'completed'}}
            await asyncio.sleep(100)
        with patch.object(chat_router, 'mysql_client', self.db), patch.object(chat_router.supervisor_graph, 'stream_process', fake):
            response = await chat_router.chat(ChatRequest(message='new', conversation_id='c', mode='chat'))
            for _ in range(4): await anext(response.body_iterator)
            await response.body_iterator.aclose()
            args = self.db.update_message.call_args.args
            self.assertEqual(args[1], 'partial')
            self.assertEqual(args[2][0]['id'], 't')
            self.assertEqual(args[3]['sources'], [{'number': 1}])
            self.assertFalse(chat_router._active_conversations)

    async def test_nonstream_failure_also_persists_error_and_releases_lock(self):
        async def fake(**kwargs): yield {'type': 'error', 'content': 'failure'}
        with patch.object(chat_router, 'mysql_client', self.db), patch.object(chat_router.supervisor_graph, 'stream_process', fake):
            with self.assertRaises(Exception) as raised:
                await chat_router.chat(ChatRequest(message='new', conversation_id='c', mode='chat', stream=False))
            self.assertEqual(raised.exception.status_code, 502)
            self.assertEqual(self.db.update_message.call_args.args[-1]['status'], 'error')
            self.assertFalse(chat_router._active_conversations)


class KnowledgeTests(unittest.TestCase):
    def test_calculator_rejects_python_objects_and_unbounded_powers(self):
        self.assertIn('56088', calculator('123*456'))
        self.assertIn('4.0', calculator('sqrt(16)'))
        for expression in ['().__class__', '__import__("os")', '2**1000000000', '[x for x in range(10)]']:
            self.assertIn('计算错误', calculator(expression))
    def test_path_traversal_and_absolute_paths_are_rejected(self):
        for name in ['../evil.md', '..\\evil.md', 'C:\\evil.md', '/evil.md', 'a:b.md', 'file\x00.md']:
            with self.assertRaises(Exception): knowledge_router.safe_path(name)
        self.assertEqual(knowledge_router.safe_path('正常资料.md').name, '正常资料.md')

    def test_long_paragraphs_are_bounded_and_overlap(self):
        from src.config import settings
        with patch.object(settings, 'chunk_size', 100), patch.object(settings, 'chunk_overlap', 20):
            chunks = DocumentLoader()._chunk_text('甲乙丙丁' * 200)
        self.assertTrue(all(len(c) <= 100 for c in chunks))
        self.assertTrue(len(chunks) > 1)
        self.assertEqual(chunks[0][-20:], chunks[1][:20])

    def test_chinese_rerank_and_distinct_document_sources(self):
        self.assertIn('退款', terms('如何申请退款'))
        results = [{'id': 'a', 'content': '退款政策', 'metadata': {'document_id': 'a'}, 'distance': .2},
                   {'id': 'b', 'content': '退款政策', 'metadata': {'document_id': 'b'}, 'distance': .2},
                   {'id': 'c', 'content': '其他内容', 'metadata': {'document_id': 'c'}, 'distance': .2}]
        ranked = AgenticRetriever()._deduplicate_and_rerank(results, '退款政策')
        self.assertEqual(len(ranked), 3)
        self.assertEqual([r['id'] for r in ranked[:2]], ['a', 'b'])


if __name__ == '__main__': unittest.main()
