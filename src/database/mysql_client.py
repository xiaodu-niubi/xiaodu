"""MySQL 客户端 - 对话和消息持久化存储"""
import uuid
import json
from typing import Optional
from contextlib import contextmanager

import pymysql
from pymysql.cursors import DictCursor

from src.config import settings


class MySQLClient:
    """MySQL 数据库操作封装"""

    def __init__(self):
        self._conn = None

    @property
    def connection(self):
        if self._conn is None:
            self._conn = pymysql.connect(
                host=settings.mysql_host,
                port=settings.mysql_port,
                user=settings.mysql_user,
                password=settings.mysql_password,
                database=settings.mysql_database,
                charset='utf8mb4',
                cursorclass=DictCursor,
                autocommit=True,
            )
        return self._conn

    @contextmanager
    def get_cursor(self):
        """获取数据库游标，自动处理重连"""
        conn = self.connection
        try:
            conn.ping(reconnect=True)
        except Exception:
            self._conn = None
            conn = self.connection
        cursor = conn.cursor()
        try:
            yield cursor
        finally:
            cursor.close()

    # ─── 对话管理 ───

    def create_conversation(self, title: str = "新对话") -> dict:
        """创建新的对话记录"""
        conv_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())[:12]
        with self.get_cursor() as cur:
            cur.execute(
                "INSERT INTO conversations (id, session_id, title) VALUES (%s, %s, %s)",
                (conv_id, session_id, title),
            )
        return {"id": conv_id, "session_id": session_id, "title": title}

    def get_conversation(self, conv_id: str) -> Optional[dict]:
        """获取单个对话详情"""
        with self.get_cursor() as cur:
            cur.execute("SELECT * FROM conversations WHERE id = %s", (conv_id,))
            return cur.fetchone()

    def list_conversations(self, limit: int = 50, offset: int = 0) -> list:
        """获取对话列表（按更新时间倒序）"""
        with self.get_cursor() as cur:
            cur.execute(
                "SELECT * FROM conversations WHERE status != 'deleted' ORDER BY updated_at DESC LIMIT %s OFFSET %s",
                (limit, offset),
            )
            return cur.fetchall()

    def update_conversation_title(self, conv_id: str, title: str):
        """更新对话标题"""
        with self.get_cursor() as cur:
            cur.execute(
                "UPDATE conversations SET title = %s WHERE id = %s",
                (title, conv_id),
            )

    def delete_conversation(self, conv_id: str):
        """软删除对话"""
        with self.get_cursor() as cur:
            cur.execute(
                "UPDATE conversations SET status = 'deleted' WHERE id = %s",
                (conv_id,),
            )

    # ─── 消息管理 ───

    def save_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        tool_calls: Optional[list] = None,
        metadata: Optional[dict] = None,
    ) -> int:
        """保存一条消息"""
        with self.get_cursor() as cur:
            cur.execute(
                "INSERT INTO messages (conversation_id, role, content, tool_calls, metadata) VALUES (%s, %s, %s, %s, %s)",
                (
                    conversation_id,
                    role,
                    content,
                    json.dumps(tool_calls) if tool_calls else None,
                    json.dumps(metadata) if metadata else None,
                ),
            )
            return cur.lastrowid

    def get_messages(self, conversation_id: str, limit: int = 500) -> list:
        """获取对话的所有消息"""
        with self.get_cursor() as cur:
            cur.execute(
                "SELECT * FROM messages WHERE conversation_id = %s ORDER BY created_at ASC LIMIT %s",
                (conversation_id, limit),
            )
            return cur.fetchall()

    # ─── 知识库文档管理 ───

    def register_document(self, filename: str, file_type: str, chunk_count: int = 0) -> str:
        """注册新文档"""
        doc_id = str(uuid.uuid4())
        with self.get_cursor() as cur:
            cur.execute(
                "INSERT INTO knowledge_documents (id, filename, file_type, chunk_count) VALUES (%s, %s, %s, %s)",
                (doc_id, filename, file_type, chunk_count),
            )
        return doc_id

    def update_document_status(self, doc_id: str, status: str, chunk_count: int = 0):
        """更新文档处理状态"""
        with self.get_cursor() as cur:
            cur.execute(
                "UPDATE knowledge_documents SET status = %s, chunk_count = %s WHERE id = %s",
                (status, chunk_count, doc_id),
            )

    def list_documents(self) -> list:
        """列出所有知识库文档"""
        with self.get_cursor() as cur:
            cur.execute("SELECT * FROM knowledge_documents WHERE status != 'error' ORDER BY created_at DESC")
            return cur.fetchall()


mysql_client = MySQLClient()
