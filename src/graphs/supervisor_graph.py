"""LangGraph 调度图 - 多智能体协作编排

实现监督者-工作者模式：
- 监督者节点分析意图并路由到专用智能体
- 每个工作者智能体有单一职责
- 条件边根据智能体输出进行路由
- 状态通过图流转，支持记忆检查点
"""
from typing import TypedDict, Literal

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import AIMessage, ToolMessage

from src.agents.orchestrator import OrchestratorAgent
from src.agents.rag_agent import RagAgent
from src.agents.tool_agent import ToolAgent
from src.agents.web_agent import WebAgent
from src.agents.memory_agent import MemoryAgent
from src.memory.conversation import conversation_memory


# ─── 状态定义 ───

class SupervisorState(TypedDict):
    """调度图状态"""
    session_id: str
    conversation_id: str
    messages: list[dict]
    user_message: str
    next_agent: str
    agent_output: dict
    final_response: str
    tool_calls: list[dict]
    error: str
    route_complete: bool


# ─── 节点函数 ───

def supervisor_node(state: SupervisorState) -> SupervisorState:
    """编排节点：分析意图，决定路由到哪个智能体"""
    orchestrator = OrchestratorAgent()
    history = state.get("messages", [])[-10:]
    user_msg = state.get("user_message", "")
    decision = orchestrator.route(user_msg, history)
    state["next_agent"] = decision.get("next_agent", "") or ""
    state["error"] = ""
    print(f"[调度器] 路由到：{state['next_agent']}")
    print(f"[调度器] 原因：{decision.get('reasoning', 'N/A')}")
    return state


def rag_node(state: SupervisorState) -> SupervisorState:
    """RAG 智能体节点：从知识库检索"""
    agent = RagAgent()
    result = agent.run(state["user_message"], state.get("messages", [])[-10:])
    state["agent_output"] = result
    state["route_complete"] = True
    return state


def tool_node(state: SupervisorState) -> SupervisorState:
    """工具智能体节点：执行函数调用"""
    agent = ToolAgent()
    result = agent.run(state["user_message"], state.get("messages", [])[-10:])
    state["agent_output"] = result
    state["tool_calls"] = result.get("tool_calls", [])
    state["route_complete"] = True
    return state


def web_node(state: SupervisorState) -> SupervisorState:
    """网络智能体节点：搜索互联网"""
    agent = WebAgent()
    result = agent.run(state["user_message"], state.get("messages", [])[-10:])
    state["agent_output"] = result
    state["tool_calls"] = result.get("tool_calls", [])
    state["route_complete"] = True
    return state


def memory_node(state: SupervisorState) -> SupervisorState:
    """记忆智能体节点：检索对话上下文"""
    agent = MemoryAgent(session_id=state.get("session_id", ""))
    result = agent.run(state["user_message"], state.get("messages", [])[-10:])
    state["agent_output"] = result
    state["route_complete"] = True
    return state


def fallback_node(state: SupervisorState) -> SupervisorState:
    """回退节点：无需专家时处理简单查询"""
    from src.models.llm_client import build_llm
    llm = build_llm(streaming=False)
    response = llm.invoke(state["user_message"])
    state["agent_output"] = {
        "content": response.content if hasattr(response, "content") else str(response),
        "tool_calls": [],
    }
    state["route_complete"] = True
    return state


def format_output_node(state: SupervisorState) -> SupervisorState:
    """格式化最终输出"""
    output = state.get("agent_output", {})
    state["final_response"] = output.get("content", "无法处理您的请求。")
    return state


# ─── 路由函数 ───

def router(state: SupervisorState) -> Literal["rag", "tool", "web", "memory", "fallback"]:
    """根据监督者决策确定下一个节点"""
    next_agent = state.get("next_agent", "").lower()

    routing_map = {
        "rag_agent": "rag",
        "tool_agent": "tool",
        "web_agent": "web",
        "memory_agent": "memory",
    }

    target = routing_map.get(next_agent, "fallback")
    print(f"[路由] → {target}")
    return target


# ─── 构建图 ───

def build_supervisor_graph() -> StateGraph:
    """构建并编译 LangGraph 调度图"""
    workflow = StateGraph(SupervisorState)

    # 添加节点
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("rag", rag_node)
    workflow.add_node("tool", tool_node)
    workflow.add_node("web", web_node)
    workflow.add_node("memory", memory_node)
    workflow.add_node("fallback", fallback_node)
    workflow.add_node("format_output", format_output_node)

    # 入口：监督者节点
    workflow.set_entry_point("supervisor")

    # 监督者根据分析结果路由到专用智能体
    workflow.add_conditional_edges(
        "supervisor",
        router,
        {
            "rag": "rag",
            "tool": "tool",
            "web": "web",
            "memory": "memory",
            "fallback": "fallback",
        },
    )

    # 所有智能体 → 格式化输出 → 结束
    workflow.add_edge("rag", "format_output")
    workflow.add_edge("tool", "format_output")
    workflow.add_edge("web", "format_output")
    workflow.add_edge("memory", "format_output")
    workflow.add_edge("fallback", "format_output")
    workflow.add_edge("format_output", END)

    # 编译，带检查点以支持记忆
    memory_saver = MemorySaver()
    graph = workflow.compile(checkpointer=memory_saver)
    return graph


# ─── 图执行封装 ───

class SupervisorGraph:
    """调度图的高层 API"""

    def __init__(self):
        self.graph = build_supervisor_graph()

    def process(
        self,
        user_message: str,
        session_id: str,
        conversation_id: str,
        history: list[dict] = None,
    ) -> dict:
        """通过图处理用户消息"""
        config = {"configurable": {"thread_id": session_id}}

        initial_state: SupervisorState = {
            "session_id": session_id,
            "conversation_id": conversation_id,
            "messages": history or [],
            "user_message": user_message,
            "next_agent": "",
            "agent_output": {},
            "final_response": "",
            "tool_calls": [],
            "error": "",
            "route_complete": False,
        }

        try:
            result = self.graph.invoke(initial_state, config)
            return {
                "response": result.get("final_response", ""),
                "agent_used": result.get("next_agent", "fallback"),
                "tool_calls": result.get("tool_calls", []),
                "session_id": session_id,
            }
        except Exception as e:
            return {
                "response": f"处理出错：{e}",
                "agent_used": "error",
                "tool_calls": [],
                "session_id": session_id,
            }

    async def stream_process(
        self,
        user_message: str,
        session_id: str,
        conversation_id: str,
        history: list[dict] = None,
    ):
        """流式处理，使用真正的 LLM 流式输出"""
        import asyncio
        from src.models.llm_client import build_llm, format_messages_for_llm

        try:
            # Phase 1: 分析意图、决定路由
            yield {"type": "status", "content": "analyzing"}

            orchestrator = OrchestratorAgent() #路由到指定智能体
            decision = orchestrator.route(user_message, (history or [])[-10:])
            next_agent = (decision.get("next_agent", "") or "").lower()
            print(f"[调度器] 路由到：{next_agent}")

            yield {"type": "status", "content": "routing"}
            yield {"type": "node", "content": "supervisor"}

            # Phase 2: 根据路由准备上下文，然后流式调用 LLM
            system_prompt = "你是一个有用的AI助手，请用中文回答用户的问题。"
            tools_for_llm = []
            extra_context = ""

            if next_agent == "rag_agent":
                yield {"type": "status", "content": "executing_rag"}
                yield {"type": "node", "content": "rag"}
                # 先从知识库检索
                extra_context = self._fetch_knowledge(user_message)
                system_prompt = (
                    "你是知识检索智能体。请仅根据以下知识库内容回答用户问题。"
                    "如果知识库中没有相关信息，请诚实告知。\n\n"
                    f"## 知识库内容\n{extra_context}"
                )

            elif next_agent == "tool_agent":
                yield {"type": "status", "content": "executing_tool"}
                yield {"type": "node", "content": "tool"}
                from src.tools.tool_registry import tool_registry
                tools_for_llm = list(tool_registry.get_all_tools())
                system_prompt = (
                    "你是一个工具调用智能体。可以使用计算器、时间查询、代码执行等工具。"
                    "用中文回答，必要时调用工具获取准确信息。"
                )

            elif next_agent == "web_agent":
                yield {"type": "status", "content": "executing_web"}
                yield {"type": "node", "content": "web"}
                from src.tools.tool_registry import tool_registry
                tools_for_llm = [
                    t for t in tool_registry.get_all_tools()
                    if getattr(t, 'name', '') in ('web_search', 'web_fetch', 'get_weather')
                ]
                system_prompt = (
                    "你是一个网络搜索智能体。用中文回答，可以搜索互联网获取最新信息，"
                    "也可以使用 get_weather 工具查询城市天气（支持中文城市名如'北京'、'贵阳'）。"
                    "当用户询问天气时，请直接用 get_weather 工具获取实时数据。"
                )

            elif next_agent == "memory_agent":
                yield {"type": "status", "content": "executing_memory"}
                yield {"type": "node", "content": "memory"}
                extra_context = self._fetch_memory(session_id, user_message)
                system_prompt = (
                    "你是一个记忆管理智能体。根据对话历史提供个性化回复。\n\n"
                    f"## 历史上下文\n{extra_context}"
                )

            else:
                yield {"type": "status", "content": "executing_fallback"}
                yield {"type": "node", "content": "fallback"}

            yield {"type": "node", "content": "format_output"}

            # Phase 3: 多轮工具调用循环
            # 有工具时用非流式检测并执行（保证 args 完整），最后统一流式输出最终回答
            messages = format_messages_for_llm(
                system_prompt=system_prompt,
                history=history or [],
                user_message=user_message,
            )

            from src.config import settings as app_settings
            max_iterations = app_settings.max_agent_iterations
            full_response = ""

            if tools_for_llm:
                # ── 非流式循环：可靠检测工具调用 ──
                llm_ns = build_llm(streaming=False, tools=tools_for_llm)
                iteration = 0

                while iteration < max_iterations:
                    iteration += 1
                    try:
                        response = llm_ns.invoke(messages)
                    except Exception as e:
                        yield {"type": "error", "content": f"LLM 调用失败: {e}"}
                        return

                    if hasattr(response, 'tool_calls') and response.tool_calls:
                        messages.append(response)
                        yield {"type": "status", "content": "executing_tools"}

                        from src.tools.tool_registry import tool_registry

                        for tc in response.tool_calls:
                            tool_name = tc.get('name', '')
                            tool_args = tc.get('args', {})
                            tool_id = tc.get('id', '')
                            tool_func = tool_registry.get_tool(tool_name)
                            if tool_func:
                                try:
                                    result = tool_func.invoke(tool_args) if hasattr(tool_func, 'invoke') else tool_func(**tool_args)
                                    result_str = str(result)
                                    yield {"type": "token", "content": f"\n\n🔧 调用 {tool_name}:\n{result_str[:500]}\n\n"}
                                    full_response += f"\n\n[工具 {tool_name}: {result_str}]"
                                    messages.append(ToolMessage(content=result_str, tool_call_id=tool_id))
                                except Exception as e:
                                    error_msg = f"工具 {tool_name} 执行失败: {e}"
                                    yield {"type": "token", "content": f"\n{error_msg}\n"}
                                    messages.append(ToolMessage(content=error_msg, tool_call_id=tool_id))
                            else:
                                error_msg = f"未找到工具: {tool_name}"
                                yield {"type": "token", "content": f"\n{error_msg}\n"}
                                messages.append(ToolMessage(content=error_msg, tool_call_id=tool_id))
                    else:
                        break  # 最终回答已包含在 messages 中

            # Phase 4: 流式输出最终回答
            final_llm = build_llm(streaming=True, tools=[])
            try:
                for chunk in final_llm.stream(messages):
                    if chunk.content:
                        full_response += chunk.content
                        yield {"type": "token", "content": chunk.content}
            except Exception as e:
                if not full_response:
                    yield {"type": "token", "content": str(e)}

            # 保存结果到图状态，供 chat_router 读取
            config = {"configurable": {"thread_id": session_id}}
            self.graph.update_state(config, {
                "final_response": full_response,
                "next_agent": next_agent,
                "tool_calls": [],
            })

            yield {"type": "done", "content": ""}

        except Exception as e:
            yield {"type": "error", "content": str(e)}

    def _fetch_knowledge(self, query: str) -> str:
        """从知识库检索内容"""
        try:
            from src.rag.retriever import agentic_retriever
            result = agentic_retriever.retrieve(query)
            if result and result.get("results"):
                return result.get("summary", "无相关内容")
        except Exception as e:
            print(f"知识检索失败: {e}")
        return "知识库暂无相关内容"

    def _fetch_memory(self, session_id: str, query: str) -> str:
        """获取对话记忆"""
        try:
            from src.memory.conversation import conversation_memory
            history = conversation_memory.get_history(session_id, 10)
            if history:
                lines = []
                for h in history:
                    role = "用户" if h.get("role") == "user" else "AI"
                    lines.append(f"[{role}]: {h.get('content', '')[:200]}")
                return "\n".join(lines)
        except Exception as e:
            print(f"记忆获取失败: {e}")
        return "无历史记录"


supervisor_graph = SupervisorGraph()
