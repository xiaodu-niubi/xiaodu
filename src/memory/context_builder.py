"""上下文构建器 - 智能上下文窗口管理

处理：
- 接近令牌限制时截断旧消息
- 对较早的对话轮次进行摘要
- 将相关记忆注入智能体上下文
"""
from src.config import settings
from src.memory.conversation import conversation_memory


class ContextBuilder:
    """为 LLM 调用构建优化的上下文"""

    def build_context(
        self,
        session_id: str,
        system_prompt: str,
        current_message: str,
        max_messages: int = None,
    ) -> list[dict]:
        """构建 LLM 调用的完整消息上下文"""
        max_msgs = max_messages or settings.max_context_messages
        history = conversation_memory.get_history(session_id, max_msgs * 2)

        messages = [{"role": "system", "content": system_prompt}]

        # 历史过长时注入早期消息摘要
        if len(history) > max_msgs:
            summary = self._build_rolling_summary(session_id, history[:-max_msgs])
            if summary:
                messages.append({
                    "role": "system",
                    "content": f"[历史对话摘要]\n{summary}",
                })
            history = history[-max_msgs:]

        messages.extend(history)
        messages.append({"role": "user", "content": current_message})
        return messages

    def _build_rolling_summary(self, session_id: str, old_messages: list[dict]) -> str:
        """为较早的消息创建简短摘要"""
        if not old_messages:
            return ""

        existing = conversation_memory.get_summary(session_id) or ""

        user_msgs = [m["content"] for m in old_messages if m["role"] == "user"]
        assistant_msgs = [m["content"] for m in old_messages if m["role"] == "assistant"]

        summary_parts = []
        if existing:
            summary_parts.append(f"之前：{existing[:200]}")

        if user_msgs:
            topics = [m[:80] for m in user_msgs[-5:]]
            summary_parts.append(f"话题：{'；'.join(topics)}")

        summary = "。".join(summary_parts)
        conversation_memory.save_summary(session_id, summary)
        return summary

    def build_scratchpad_context(self, session_id: str, agent_name: str) -> dict:
        """加载智能体特定的工作区状态"""
        from src.database.redis_client import redis_client
        return redis_client.get_agent_state(session_id, agent_name) or {}

    def save_scratchpad(self, session_id: str, agent_name: str, state: dict):
        """持久化智能体工作区状态"""
        from src.database.redis_client import redis_client
        redis_client.save_agent_state(session_id, agent_name, state)


context_builder = ContextBuilder()
