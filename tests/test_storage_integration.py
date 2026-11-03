"""Opt-in integration check against this workspace's configured MySQL and Chroma.

Run: WORKBENCH_STORAGE_TESTS=1 python -m unittest discover -s tests -v
The model is simulated; only the test's own conversation is created and deleted.
"""
import os
import unittest
from unittest.mock import patch
import httpx
from langchain_core.messages import AIMessageChunk
from src.main import app


@unittest.skipUnless(os.environ.get('WORKBENCH_STORAGE_TESTS') == '1', 'opt-in: writes its own integration conversation')
class StorageIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_history_citations_and_saved_artifact_with_real_storage(self):
        class Model:
            async def astream(self, messages):
                yield AIMessageChunk(content='## 资料分析\n\n已整理资料 [1]。')

        client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test')
        conversation_id = None
        try:
            created = await client.post('/api/conversations', json={'title': '存储集成验收'})
            created.raise_for_status()
            conversation_id = created.json()['id']
            docs = (await client.get('/api/knowledge/list')).json()['documents']
            ids = [doc['id'] for doc in docs if doc['status'] == 'ready'][:2]
            self.assertEqual(len(ids), 2, 'Import at least two documents to run this integration check')
            with patch('src.graphs.supervisor_graph.build_llm', return_value=Model()):
                response = await client.post('/api/chat', json={'message': '比较资料内容', 'mode': 'compare',
                    'document_ids': ids, 'conversation_id': conversation_id, 'stream': False})
            response.raise_for_status()
            result = response.json()
            self.assertTrue(result['sources'])
            self.assertTrue({s['document_id'] for s in result['sources']} <= set(ids))
            history = (await client.get('/api/conversations/' + conversation_id)).json()['messages']
            self.assertEqual(len(history), 2)
            assistant = history[-1]
            self.assertEqual(assistant['metadata']['sources'], result['sources'])
            self.assertEqual(assistant['metadata']['status'], 'completed')
            saved = await client.put('/api/artifacts/' + conversation_id + '/' + str(assistant['id']),
                                     json={'title': '保存验收', 'content': '# 已编辑的报告'})
            saved.raise_for_status()
            artifacts = (await client.get('/api/artifacts')).json()['artifacts']
            own = next(a for a in artifacts if a['id'] == assistant['id'])
            self.assertEqual(own['metadata']['artifact']['content'], '# 已编辑的报告')
        finally:
            if conversation_id:
                deleted = await client.delete('/api/conversations/' + conversation_id)
                self.assertEqual(deleted.status_code, 200)
            await client.aclose()
