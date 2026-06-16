"""记忆智能体 - 对话上下文管理专家

单一职责：管理和检索对话记忆、用户偏好和会话上下文。
"""
from src.agents.base_agent import BaseAgent
from src.memory.conversation import conversation_memory


MEMORY_AGENT_PROMPT = """你是一个记忆智能体。你的职责是帮助用户处理对话历史和偏好。

## 你的能力：
- 回忆之前的对话主题和细节
- 记住用户提到过的偏好
- 总结历史对话
- 追踪用户之前询问过什么

## 工作流程：
1. 搜索对话记忆中的相关历史
2. 识别历史对话中的用户偏好
3. 提供引用过去交互的上下文感知回复

## 规则：
- 仅使用实际的对话记忆中的信息
- 如果没有相关记忆，请诚实说明
- 记录用户偏好以供将来参考"""


class MemoryAgent(BaseAgent):
    """记忆智能体"""

    name: str = "memory_agent"
    system_prompt: str = MEMORY_AGENT_PROMPT
    tools: list = []
    max_iterations: int = 5

    def __init__(self, session_id: str = ""):
        super().__init__()
        self.session_id = session_id

    def run(self, user_message: str, history: list[dict] = None) -> dict:
        """注入记忆上下文后执行"""
        if self.session_id:
            mem_history = conversation_memory.get_history(self.session_id, 10)
            prefs = conversation_memory.get_preferences(self.session_id)

            memory_context = ""
            if mem_history:
                recent = [f"- {m['role']}：{m['content'][:100]}" for m in mem_history[-5:]]
                memory_context += "最近的对话：\n" + "\n".join(recent) + "\n\n"
            if prefs:
                memory_context += "用户偏好：\n" + "\n".join(
                    f"- {k}：{v}" for k, v in prefs.items()
                ) + "\n\n"

            if memory_context:
                self.system_prompt = MEMORY_AGENT_PROMPT + f"\n\n## 当前上下文\n{memory_context}"

        return super().run(user_message, history)
