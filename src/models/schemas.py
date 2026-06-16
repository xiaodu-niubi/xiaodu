"""Pydantic 数据模型 - API 请求/响应模式定义"""
from datetime import datetime
from typing import Optional
from enum import Enum

from pydantic import BaseModel, Field


# ─── 聊天 ───

class ChatRequest(BaseModel):
    """聊天请求"""
    message: str
    conversation_id: Optional[str] = None
    stream: bool = True


class ChatResponse(BaseModel):
    """聊天响应"""
    conversation_id: str
    session_id: str
    message: str
    tool_calls: Optional[list[dict]] = None


class ChatStreamChunk(BaseModel):
    """流式响应块"""
    type: str  # 'token', 'tool_call', 'tool_result', 'done'
    content: str = ""
    metadata: Optional[dict] = None


# ─── 对话 ───

class ConversationCreate(BaseModel):
    """创建对话"""
    title: str = "新对话"


class ConversationUpdate(BaseModel):
    """更新对话标题"""
    title: str


class MessageItem(BaseModel):
    """消息条目"""
    id: int
    role: str
    content: Optional[str]
    tool_calls: Optional[list] = None
    metadata: Optional[dict] = None
    created_at: datetime


class ConversationItem(BaseModel):
    """对话列表项"""
    id: str
    session_id: str
    title: str
    status: str
    created_at: datetime
    updated_at: datetime


class ConversationDetail(BaseModel):
    """对话详情（含消息列表）"""
    id: str
    session_id: str
    title: str
    status: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageItem]


# ─── 知识库 ───

class KnowledgeDocument(BaseModel):
    """知识库文档"""
    id: str
    filename: str
    file_type: str
    chunk_count: int
    status: str
    created_at: datetime


class KnowledgeUploadResponse(BaseModel):
    """文档上传响应"""
    id: str
    filename: str
    chunk_count: int
    status: str


# ─── 工具 ───

class ToolParameter(BaseModel):
    """工具参数定义"""
    type: str
    description: str
    required: bool = True
    enum: Optional[list] = None
    properties: Optional[dict] = None


class ToolDefinition(BaseModel):
    """工具定义"""
    name: str
    description: str
    parameters: dict


# ─── 通用 ───

class ErrorResponse(BaseModel):
    """错误响应"""
    error: str
    detail: Optional[str] = None
