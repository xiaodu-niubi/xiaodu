"""Redis 客户端 - 对话记忆和智能体状态管理"""
import json
from typing import Optional

import redis

from src.config import settings


class RedisClient:
    """Redis 操作封装 - 管理会话记忆和智能体状态"""

    def __init__(self):
        self._client = None

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password or None,
                decode_responses=True,
            )
        try:
            self._client.ping()
        except (redis.ConnectionError, redis.TimeoutError):
            self._client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password or None,
                decode_responses=True,
            )
        return self._client

    def _check_connection(self) -> bool:
        try:
            return self.client.ping()
        except Exception:
            return False

    # ─── 对话记忆 ───

    def save_message(self, session_id: str, role: str, content: str):
        """保存单条消息到 Redis 列表"""
        key = f"memory:{session_id}:messages"
        msg = json.dumps({"role": role, "content": content}, ensure_ascii=False)
        self.client.rpush(key, msg)
        self.client.expire(key, settings.memory_ttl_seconds)

    def get_messages(self, session_id: str, limit: int = 20) -> list:
        """获取最近的对话消息"""
        key = f"memory:{session_id}:messages"
        raw = self.client.lrange(key, -limit, -1)
        return [json.loads(m) for m in raw]

    def clear_memory(self, session_id: str):
        """清除会话所有记忆"""
        pattern = f"memory:{session_id}:*"
        keys = self.client.keys(pattern)
        if keys:
            self.client.delete(*keys)

    # ─── 智能体工作区 ───

    def save_agent_state(self, session_id: str, agent_name: str, state: dict):
        """保存智能体的工作状态"""
        key = f"memory:{session_id}:agent:{agent_name}"
        self.client.setex(key, settings.memory_ttl_seconds, json.dumps(state, ensure_ascii=False))

    def get_agent_state(self, session_id: str, agent_name: str) -> Optional[dict]:
        """获取智能体的工作状态"""
        key = f"memory:{session_id}:agent:{agent_name}"
        raw = self.client.get(key)
        return json.loads(raw) if raw else None

    # ─── 会话元数据 ───

    def save_metadata(self, session_id: str, metadata: dict):
        """保存会话元数据"""
        key = f"memory:{session_id}:metadata"
        self.client.setex(key, settings.memory_ttl_seconds, json.dumps(metadata, ensure_ascii=False))

    def get_metadata(self, session_id: str) -> Optional[dict]:
        """获取会话元数据"""
        key = f"memory:{session_id}:metadata"
        raw = self.client.get(key)
        return json.loads(raw) if raw else {}

    # ─── 用户偏好 ───

    def save_preference(self, session_id: str, key_name: str, value: str):
        """保存用户偏好设置"""
        key = f"memory:{session_id}:prefs"
        self.client.hset(key, key_name, value)
        self.client.expire(key, settings.memory_ttl_seconds)

    def get_preferences(self, session_id: str) -> dict:
        """获取所有用户偏好"""
        key = f"memory:{session_id}:prefs"
        return self.client.hgetall(key)

    # ─── 对话摘要 ───

    def save_summary(self, session_id: str, summary: str):
        """保存对话摘要"""
        key = f"memory:{session_id}:summary"
        self.client.setex(key, settings.memory_ttl_seconds, summary)

    def get_summary(self, session_id: str) -> Optional[str]:
        """获取对话摘要"""
        key = f"memory:{session_id}:summary"
        return self.client.get(key)


redis_client = RedisClient()
