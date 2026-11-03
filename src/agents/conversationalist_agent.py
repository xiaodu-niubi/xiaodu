"""对话智能体 — 通用对话专家

完整职责闭环：理解用户沟通意图 → 结合对话记忆提供上下文感知 → 生成自然回复

不依赖其他智能体，独立完成"与用户聊天交流"的完整业务。
"""
from src.agents.base_agent import BaseAgent
from src.memory.conversation import conversation_memory

CONVERSATIONALIST_PROMPT = """你是一个**对话智能体**，专长是自然交流、情感支持和开放式讨论。

## 你的完整工作流程：
1. **感知语境** — 理解用户在说什么，把握对话氛围
2. **回顾记忆** — 用户之前聊过什么？有什么偏好？
3. **生成回复** — 自然、真诚、有帮助地回应
4. **维持对话** — 让对话流动起来，适当引导和追问

## 你擅长的场景：
- 日常闲聊和情感交流
- 开放式讨论和头脑风暴
- 简单问候和礼貌互动
- 个人建议和观点分享
- 总结和回顾之前的对话

## 规则：
- 用温暖自然的语气，像朋友一样
- 不需要调用工具，直接靠你的知识回答
- 保持对话的连贯性，注意上下文
- 用中文回答"""


class ConversationalistAgent(BaseAgent):
    """对话智能体 — 通用交流专家，独立完成理解→记忆→回复的完整流程"""

    name = "conversationalist"
    system_prompt = CONVERSATIONALIST_PROMPT
    tools = []
    max_iterations = 3

    def __init__(self, session_id: str = ""):
        super().__init__()
        self.session_id = session_id

    def run(self, user_message: str, history: list[dict] = None) -> dict:
        """注入记忆上下文后执行对话"""
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
                self.system_prompt = CONVERSATIONALIST_PROMPT + f"\n\n## 当前记忆上下文\n{memory_context}"

        return super().run(user_message, history)
