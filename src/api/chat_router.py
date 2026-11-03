"""Chat API with one execution path, durable task status and structured SSE events."""
import asyncio
import json
import logging
import uuid
from contextlib import aclosing

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from src.models.schemas import ChatRequest, ChatResponse
from src.config import settings
from src.graphs.supervisor_graph import supervisor_graph
from src.database.mysql_client import mysql_client
from src.memory.conversation import conversation_memory

router = APIRouter(prefix="/api", tags=["聊天"])
logger = logging.getLogger(__name__)
_active_conversations: set[str] = set()


def sse(event):
    return f"event: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"


@router.post("/chat")
async def chat(request: ChatRequest):
    if not request.message.strip():
        raise HTTPException(422, "请输入内容。")
    if request.mode == 'compare' and len(set(request.document_ids)) < 2:
        raise HTTPException(400, "对比文档需要选择至少两份不同的资料。")
    if request.document_ids:
        docs = await asyncio.to_thread(mysql_client.list_documents)
        ready = {d["id"] for d in docs if d["status"] == "ready"}
        if not set(request.document_ids) <= ready:
            raise HTTPException(400, "部分资料尚未就绪或已被删除，请重新选择。")
    conv_id = request.conversation_id
    if conv_id:
        conv = await asyncio.to_thread(mysql_client.get_conversation, conv_id)
        if not conv or conv.get("status") == "deleted":
            raise HTTPException(404, "对话未找到。")
    else:
        conv = await asyncio.to_thread(mysql_client.create_conversation, request.message.strip()[:60])
        conv_id = conv["id"]
    if conv_id in _active_conversations:
        raise HTTPException(409, "此对话有任务正在执行，请先停止或等待完成。")
    _active_conversations.add(conv_id)
    session_id = conv["session_id"]
    task_id = str(uuid.uuid4())
    try:
        # MySQL is authoritative; Redis can be unavailable without losing context.
        previous = await asyncio.to_thread(mysql_client.get_messages, conv_id, 20)
        history = [{"role": m["role"], "content": m["content"]} for m in previous if m.get("content")]
        await asyncio.to_thread(mysql_client.save_message, conv_id, "user", request.message.strip())
        assistant_id = await asyncio.to_thread(
            mysql_client.save_message, conv_id, "assistant", "",
            metadata={"task_id": task_id, "status": "running", "mode": request.mode},
        )
    except BaseException:
        _active_conversations.discard(conv_id)
        raise

    async def events():
        response, sources, tools = "", [], {}
        status = "stopped"
        error = None
        try:
            yield {"type": "session", "conversation_id": conv_id, "task_id": task_id, "message_id": assistant_id}
            async with aclosing(supervisor_graph.stream_process(
                user_message=request.message.strip(), session_id=session_id,
                conversation_id=conv_id, history=history, mode=request.mode,
                document_ids=request.document_ids, use_web=request.use_web,
            )) as execution:
                async for event in execution:
                    kind = event["type"]
                    if kind == "token": response += event["content"]
                    elif kind == "reset": response = ""
                    elif kind == "sources": sources = event["metadata"]["sources"]
                    elif kind == "tool": tools[event["metadata"]["id"]] = event["metadata"]
                    elif kind == "error":
                        status, error = "error", event["content"]
                        yield event
                        break
                    elif kind == "done":
                        status = "completed"
                        break
                    yield event
        except asyncio.CancelledError:
            status = "stopped"
            raise
        except Exception:
            logger.exception("Chat failed")
            status, error = "error", "任务执行失败，请重试。"
            yield {"type": "error", "content": error}
        finally:
            metadata = {"task_id": task_id, "status": status, "mode": request.mode, "sources": sources, "error": error}
            try:
                await asyncio.shield(asyncio.to_thread(
                    mysql_client.update_message, assistant_id, response, list(tools.values()), metadata,
                ))
            finally:
                _active_conversations.discard(conv_id)
        if status == "completed":
            if settings.redis_enabled:
                try:
                    await asyncio.to_thread(conversation_memory.add_turn, session_id, "user", request.message)
                    await asyncio.to_thread(conversation_memory.add_turn, session_id, "assistant", response)
                except Exception:
                    logger.warning("Redis cache unavailable; history remains in MySQL")
            yield {"type": "done", "conversation_id": conv_id, "task_id": task_id}

    if request.stream:
        async def event_generator():
            stream = events()
            try:
                async for event in stream:
                    yield sse(event)
            finally:
                await stream.aclose()
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    response, sources, tools, failure = "", [], {}, None
    async for event in events():
        kind = event["type"]
        if kind == "token": response += event["content"]
        elif kind == "reset": response = ""
        elif kind == "sources": sources = event["metadata"]["sources"]
        elif kind == "tool": tools[event["metadata"]["id"]] = event["metadata"]
        elif kind == "error": failure = event["content"]
    if failure:
        raise HTTPException(502, failure)
    return ChatResponse(conversation_id=conv_id, session_id=session_id, message=response,
                        tool_calls=list(tools.values()), sources=sources)
