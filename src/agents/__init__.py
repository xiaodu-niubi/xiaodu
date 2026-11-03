"""多智能体模块 — 3 Agent + 1 Orchestrator

每个智能体都有完整的业务闭环：
- Orchestrator: 意图分析 → 路由分发
- Researcher:   知识获取 → RAG检索 + Web搜索 + 整合回复
- Executor:     执行任务 → 工具调用 + 结果解释
- Conversationalist: 对话交流 → 记忆感知 + 自然回复
"""
from src.agents.orchestrator import OrchestratorAgent
from src.agents.researcher_agent import ResearcherAgent
from src.agents.executor_agent import ExecutorAgent
from src.agents.conversationalist_agent import ConversationalistAgent

# 保留 knowledge_search 工具注册（从旧 rag_agent 迁移而来）
from src.agents.rag_agent import knowledge_search  # noqa

__all__ = [
    "OrchestratorAgent",
    "ResearcherAgent",
    "ExecutorAgent",
    "ConversationalistAgent",
]
