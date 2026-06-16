"""聊天 API 路由 - 核心对话端点，支持 SSE 流式传输"""
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from src.models.schemas import ChatRequest, ChatResponse
from src.graphs.supervisor_graph import supervisor_graph
from src.database.mysql_client import mysql_client
from src.memory.conversation import conversation_memory

router = APIRouter(prefix="/api", tags=["聊天"])


@router.post("/chat")
async def chat(request: ChatRequest):
    """主聊天端点，支持流式和非流式响应"""
    # 获取或创建对话
    conv_id = request.conversation_id
    if not conv_id:
        conv = mysql_client.create_conversation()
        conv_id = conv["id"]
        session_id = conv["session_id"]
    else:
        conv = mysql_client.get_conversation(conv_id)
        if not conv:
            raise HTTPException(status_code=404, detail="对话未找到")
        session_id = conv["session_id"]

    # 保存用户消息到 MySQL
    mysql_client.save_message(conv_id, "user", request.message)

    # 保存到 Redis 记忆
    conversation_memory.add_turn(session_id, "user", request.message)

    # 从 Redis 获取对话历史
    history = conversation_memory.get_history(session_id, 20)

    if request.stream:
        async def event_generator():
            response_text = ""
            async for chunk in supervisor_graph.stream_process(
                user_message=request.message,
                session_id=session_id,
                conversation_id=conv_id,
                history=history,
            ):
                # 收集完整回复
                if chunk['type'] == 'token':
                    response_text += chunk['content']
                yield f"event: {chunk['type']}\ndata: {json.dumps(chunk, ensure_ascii=False)}\n\n"

            # 保存助手回复
            if response_text.strip():
                mysql_client.save_message(conv_id, "assistant", response_text)
                conversation_memory.add_turn(session_id, "assistant", response_text)

                # 自动生成标题（取第一个完整短句，最长30字）
                if conv.get("title") == "新对话":
                    raw = request.message.replace('\n', ' ').strip()
                    title = raw[:30] if len(raw) <= 30 else raw[:30] + "…"
                    mysql_client.update_conversation_title(conv_id, title)

            yield f"event: done\ndata: {json.dumps({'type': 'done', 'conversation_id': conv_id})}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    else:
        # 非流式：获取完整结果
        result = supervisor_graph.process(
            user_message=request.message,
            session_id=session_id,
            conversation_id=conv_id,
            history=history,
        )

        response_text = result.get("response", "")
        tool_calls_data = result.get("tool_calls", [])

        mysql_client.save_message(
            conv_id, "assistant", response_text,
            tool_calls=tool_calls_data if tool_calls_data else None,
        )
        conversation_memory.add_turn(session_id, "assistant", response_text)

        if conv.get("title") == "新对话":
            raw = request.message.replace('\n', ' ').strip()
            title = raw[:30] if len(raw) <= 30 else raw[:30] + "…"
            mysql_client.update_conversation_title(conv_id, title)

        return ChatResponse(
            conversation_id=conv_id,
            session_id=session_id,
            message=response_text,
            tool_calls=tool_calls_data,
        )
