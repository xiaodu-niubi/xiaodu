"""对话记忆管理 - 基于 Redis 的会话记忆"""
from src.database.redis_client import redis_client


class ConversationMemory:
    """管理每个会话在 Redis 中的对话记忆"""

    def add_turn(self, session_id: str, role: str, content: str):
        """添加一轮对话"""
        redis_client.save_message(session_id, role, content)

    def get_history(self, session_id: str, limit: int = 20) -> list[dict]:
        """获取对话历史"""
        return redis_client.get_messages(session_id, limit)

    def get_last_n(self, session_id: str, n: int = 5) -> list[dict]:
        """获取最近 n 条消息"""
        messages = self.get_history(session_id, n * 2)
        return messages[-n:]

    def clear(self, session_id: str):
        """清除会话所有记忆"""
        redis_client.clear_memory(session_id)

    def save_summary(self, session_id: str, summary: str):
        """保存对话摘要"""
        redis_client.save_summary(session_id, summary)

    def get_summary(self, session_id: str) -> str:
        """获取对话摘要"""
        return redis_client.get_summary(session_id) or ""

    def set_metadata(self, session_id: str, **kwargs):
        """设置会话元数据"""
        redis_client.save_metadata(session_id, kwargs)

    def get_metadata(self, session_id: str) -> dict:
        """获取会话元数据"""
        return redis_client.get_metadata(session_id)

    def set_preference(self, session_id: str, key: str, value: str):
        """设置用户偏好"""
        redis_client.save_preference(session_id, key, value)

    def get_preferences(self, session_id: str) -> dict:
        """获取用户偏好"""
        return redis_client.get_preferences(session_id)


conversation_memory = ConversationMemory()
