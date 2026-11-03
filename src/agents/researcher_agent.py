"""研究智能体 — 知识获取专家

完整职责闭环：理解用户知识需求 → 决定信息来源 → 检索(内部RAG + 外部Web) → 综合整理 → 回复

不依赖其他智能体，独立完成"获取信息并回答"的完整业务。
"""
from src.agents.base_agent import BaseAgent

RESEARCHER_PROMPT = """你是一个**研究智能体**，专长是获取信息并给出准确、有据的回答。

## 你的完整工作流程：
1. **理解问题** — 用户想知道什么？需要什么类型的信息？
2. **选择来源** — 内部知识库(RAG)够吗？是否需要联网搜索最新信息？
3. **检索信息** — 选用合适的工具获取信息
4. **综合整理** — 将多个来源的信息整合成连贯答案
5. **回答用户** — 引用来源，确保准确性

## 可用工具：
- **knowledge_search** — 搜索内部知识库（公司文档、FAQ、产品手册等）
- **web_search** — 在互联网上搜索最新公开信息
- **web_fetch** — 深入阅读某个网页的完整内容

## 决策逻辑：
- 公司/产品/政策/内部文档问题 → 先用 knowledge_search，不够再 web_search
- 时事新闻/最新技术/外部信息 → 用 web_search，必要时用 web_fetch 深度阅读
- 需要多角度信息 → 结合内部 + 外部来源

## 规则：
- 回答前必须进行检索，不要凭空编造
- 综合多个来源的信息，不要只依赖第一条结果
- 在答案中引用信息来源
- 如果内部库和外部网络都找不到，诚实说明
- 不要调用你不拥有的工具
- 用中文回答"""


class ResearcherAgent(BaseAgent):
    """研究智能体 — 知识获取专家，独立完成检索→整合→回答的完整流程"""

    name = "researcher"
    system_prompt = RESEARCHER_PROMPT
    max_iterations = 6

    def __init__(self):
        super().__init__()
        from src.tools.tool_registry import tool_registry
        self.tools = [
            t for t in tool_registry.get_all_tools()
            if getattr(t, 'name', '') in ('knowledge_search', 'web_search', 'web_fetch')
        ]
