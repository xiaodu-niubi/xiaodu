"""RAG 智能体 - 知识检索专家

单一职责：搜索知识库（Chroma）回答基于知识的问题。
使用 Agentic RAG（非静态 RAG）- 动态决定检索什么和如何检索。
"""
from src.agents.base_agent import BaseAgent

RAG_AGENT_PROMPT = """你是一个知识检索智能体。你的职责是仅使用知识库中的信息来回答问题。

## 工作流程（ReAct）：
1. **思考**：判断是否需要从知识库检索信息
2. **行动**：使用 knowledge_search 工具查询知识库
3. **观察**：审查检索到的信息
4. **再思考**：是否需要更具体的信息？再次搜索
5. **最终答案**：从检索到的知识中综合出清晰、准确的答案

## 规则：
- 在回答之前始终先搜索知识库
- 如果知识库中没有相关答案，请诚实说明
- 引用信息来源于哪个文档
- 对于多部分问题，进行多次搜索
- 将多个文档块的信息综合成一个连贯的答案
- 不要编造知识库中不存在的信息"""


class RagAgent(BaseAgent):
    """知识检索智能体"""

    name = "rag_agent"
    system_prompt = RAG_AGENT_PROMPT
    max_iterations = 5

    def __init__(self):
        super().__init__()
        from src.tools.tool_registry import tool_registry
        # 使用全局注册的 knowledge_search 工具
        knowledge_tool = tool_registry.get_tool("knowledge_search")
        if knowledge_tool:
            self.tools = [knowledge_tool]
        else:
            self.tools = [self._knowledge_search_tool]

    @staticmethod
    def _knowledge_search_tool(query: str) -> str:
        """搜索知识库获取相关信息"""
        from src.rag.retriever import agentic_retriever
        try:
            result = agentic_retriever.retrieve(query)
            if not result or not result.get("results"):
                return "知识库中未找到相关信息。"

            analysis = result.get("analysis")
            summary = result.get("summary", "")

            output = f"检索到 {len(result['results'])} 个相关文档块。\n\n"
            if hasattr(analysis, 'reasoning'):
                output += f"分析：{analysis.reasoning}\n\n"
            output += summary

            return output
        except Exception as e:
            return f"知识检索错误：{e}。知识库可能尚未初始化。"


# 注册为全局可调用工具
from src.tools.tool_registry import tool_registry

def knowledge_search(query: str) -> str:
    """搜索知识库，获取关于公司、产品、政策、FAQ 和技术文档的信息。用于任何可能在存储文档中有答案的问题。"""
    from src.rag.retriever import agentic_retriever
    try:
        result = agentic_retriever.retrieve(query)
        if not result or not result.get("results"):
            return "知识库中未找到相关信息。"
        return result.get("summary", "无可用摘要。")
    except Exception as e:
        return f"知识检索不可用：{e}"

tool_registry.register(knowledge_search)
