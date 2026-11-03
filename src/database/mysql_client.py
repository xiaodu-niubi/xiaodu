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
        self._pool = None

    @property # 将这个方法“伪装”成属性来调用。
    def pool(self):
        if self._pool is None:
            self._pool = pymysql.connect(
                host=settings.mysql_host,
                port=settings.mysql_port,
                user=settings.mysql_user,
                password=settings.mysql_password,
                database=settings.mysql_database,
                charset='utf8mb4',
                cursorclass=DictCursor, # 启用字典游标
                autocommit=True, # 自动提交
            )
        return self._pool

    @contextmanager
    def get_cursor(self):
        """Use one connection per operation; connections aren't shared across worker threads."""
        conn = pymysql.connect(
            host=settings.mysql_host, port=settings.mysql_port,
            user=settings.mysql_user, password=settings.mysql_password,
            database=settings.mysql_database, charset='utf8mb4',
            cursorclass=DictCursor, autocommit=True, connect_timeout=5,
            read_timeout=10, write_timeout=10,
        )
        cursor = conn.cursor()
        try:
            yield cursor
        finally:
            cursor.close()
            conn.close()

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

    def update_message(self, message_id, content, tool_calls, metadata):
        with self.get_cursor() as cur:
            cur.execute("UPDATE messages SET content=%s, tool_calls=%s, metadata=%s WHERE id=%s",
                        (content, json.dumps(tool_calls, ensure_ascii=False),
                         json.dumps(metadata, ensure_ascii=False), message_id))
            cur.execute("UPDATE conversations SET updated_at=CURRENT_TIMESTAMP WHERE id=(SELECT conversation_id FROM messages WHERE id=%s)", (message_id,))

    def get_messages(self, conversation_id: str, limit: int = 50) -> list:
        """获取对话的所有消息"""
        with self.get_cursor() as cur:
            cur.execute(
                "SELECT * FROM (SELECT * FROM messages WHERE conversation_id = %s ORDER BY id DESC LIMIT %s) recent ORDER BY id ASC",
                (conversation_id, limit),
            )
            rows = cur.fetchall()
            for row in rows:
                for field in ('tool_calls', 'metadata'):
                    if isinstance(row.get(field), str):
                        row[field] = json.loads(row[field])
            return rows

    # ─── 知识库文档管理 ───

    def register_document(self, filename: str, file_type: str, chunk_count: int = 0) -> str:
        """注册新文档"""
        doc_id = str(uuid.uuid4())
        with self.get_cursor() as cur:
            cur.execute("SELECT id FROM knowledge_documents WHERE filename=%s ORDER BY created_at DESC LIMIT 1", (filename,))
            existing = cur.fetchone()
            if existing:
                return existing['id']
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
            cur.execute("SELECT * FROM knowledge_documents ORDER BY created_at DESC")
            return cur.fetchall()

    def get_document(self, doc_id):
        with self.get_cursor() as cur:
            cur.execute("SELECT * FROM knowledge_documents WHERE id=%s", (doc_id,))
            return cur.fetchone()

    def delete_document(self, doc_id):
        with self.get_cursor() as cur:
            cur.execute("DELETE FROM knowledge_documents WHERE id=%s", (doc_id,))

    def list_artifacts(self):
        with self.get_cursor() as cur:
            cur.execute("SELECT m.id, m.conversation_id, m.metadata, m.created_at, c.title AS conversation_title FROM messages m JOIN conversations c ON c.id=m.conversation_id WHERE c.status!='deleted' AND JSON_EXTRACT(m.metadata, '$.artifact') IS NOT NULL ORDER BY m.id DESC LIMIT 100")
            rows = cur.fetchall()
            for row in rows:
                if isinstance(row.get('metadata'), str):
                    row['metadata'] = json.loads(row['metadata'])
            return rows

    def save_artifact(self, conversation_id, message_id, artifact):
        with self.get_cursor() as cur:
            cur.execute("SELECT m.metadata FROM messages m JOIN conversations c ON c.id=m.conversation_id WHERE m.id=%s AND m.conversation_id=%s AND m.role='assistant' AND c.status!='deleted'", (message_id, conversation_id))
            row = cur.fetchone()
            if not row:
                return None
            metadata = row['metadata'] or {}
            if isinstance(metadata, str):
                metadata = json.loads(metadata)
            if metadata.get('status') == 'running':
                return None
            metadata['artifact'] = artifact
            cur.execute("UPDATE messages SET metadata=%s WHERE id=%s", (json.dumps(metadata, ensure_ascii=False), message_id))
            return {'id': message_id, 'conversation_id': conversation_id, 'metadata': metadata}


mysql_client = MySQLClient()
