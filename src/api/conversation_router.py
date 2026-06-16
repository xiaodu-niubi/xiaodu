"""对话管理 API 路由"""
from fastapi import APIRouter, HTTPException

from src.models.schemas import ConversationCreate, ConversationUpdate
from src.database.mysql_client import mysql_client

router = APIRouter(prefix="/api/conversations", tags=["对话"])


@router.get("")
async def list_conversations(limit: int = 50, offset: int = 0):
    """获取对话列表"""
    conversations = mysql_client.list_conversations(limit, offset)
    return {"conversations": conversations, "total": len(conversations)}


@router.post("")
async def create_conversation(body: ConversationCreate):
    """创建新对话"""
    conv = mysql_client.create_conversation(title=body.title)
    return conv


@router.get("/{conv_id}")
async def get_conversation(conv_id: str):
    """获取对话详情（含消息列表）"""
    conv = mysql_client.get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="对话未找到")
    messages = mysql_client.get_messages(conv_id)
    conv["messages"] = messages
    return conv


@router.delete("/{conv_id}")
async def delete_conversation(conv_id: str):
    """删除对话"""
    conv = mysql_client.get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="对话未找到")
    mysql_client.delete_conversation(conv_id)
    # 同时清除 Redis 记忆
    from src.memory.conversation import conversation_memory
    conversation_memory.clear(conv["session_id"])
    return {"status": "已删除"}


@router.put("/{conv_id}")
async def update_conversation(conv_id: str, body: ConversationUpdate):
    """更新对话标题"""
    conv = mysql_client.get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="对话未找到")
    mysql_client.update_conversation_title(conv_id, body.title)
    return {"status": "已更新"}
