# 第15课：LangGraph编排图 —— 把智能体串起来

> 🎯 **本课目标**：用LangGraph的StateGraph把5个智能体编排成一个协作流程。

---

## 15.1 LangGraph是什么？

LangGraph是LangChain团队开发的一个**状态图编排框架**。

用大白话说：LangGraph帮你画一张"流程图"，定义数据怎么在多个智能体之间流转。

### 核心概念

| 概念 | 大白话解释 |
|------|-----------|
| **State（状态）** | 一个"数据包"，在节点之间传递。包含用户消息、中间结果等 |
| **Node（节点）** | 一个处理步骤，比如"分析意图"、"搜索知识库" |
| **Edge（边）** | 节点之间的连线，定义"从这个节点跳到哪个节点" |
| **Conditional Edge（条件边）** | 根据条件决定下一个节点（相当于if-else） |

---

## 15.2 我们的编排图长什么样

```
开始
  │
  ▼
┌──────────────┐
│  supervisor   │  ← 编排智能体分析意图
│  (分析意图)    │
└──────┬───────┘
       │  根据分析结果路由
       ├──→ rag    (知识检索)
       ├──→ tool   (工具执行)
       ├──→ web    (网络搜索)
       ├──→ memory (记忆管理)
       └──→ fallback (通用大模型)
              │
              ▼
       ┌──────────────┐
       │ format_output │  ← 格式化最终输出
       └──────┬───────┘
              │
              ▼
            结束
```

---

## 15.3 写代码：`src/graphs/supervisor_graph.py`

这是**整个项目最核心的文件**，它定义了多智能体的协作流程。

```python
"""LangGraph 调度图 - 多智能体协作编排

实现监督者-工作者模式：
- 监督者节点分析意图并路由到专用智能体
- 每个工作者智能体有单一职责
- 条件边根据智能体输出进行路由
- 状态通过图流转
"""
from typing import TypedDict, Literal

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from src.agents.orchestrator import OrchestratorAgent
from src.agents.rag_agent import RagAgent
from src.agents.tool_agent import ToolAgent
from src.agents.web_agent import WebAgent
from src.agents.memory_agent import MemoryAgent
from src.memory.conversation import conversation_memory


# ═══════════════════════════════════════════
# 第1部分：定义状态（数据包）
# ═══════════════════════════════════════════

class SupervisorState(TypedDict):
    """调度图状态 - 在节点之间传递的数据包"""
    session_id: str          # 会话ID
    conversation_id: str     # 对话ID
    messages: list[dict]     # 历史消息
    user_message: str        # 当前用户消息
    next_agent: str          # 下一个智能体（由supervisor决定）
    agent_output: dict       # 智能体的输出
    final_response: str      # 最终回复
    tool_calls: list[dict]   # 工具调用记录
    error: str               # 错误信息
    route_complete: bool     # 路由是否完成


# ═══════════════════════════════════════════
# 第2部分：定义节点函数
# ═══════════════════════════════════════════

def supervisor_node(state: SupervisorState) -> SupervisorState:
    """编排节点：分析意图，决定路由到哪个智能体"""
    orchestrator = OrchestratorAgent()
    history = state.get("messages", [])[-10:]  # 取最近10条历史
    user_msg = state.get("user_message", "")

    # 调用编排智能体的route方法
    decision = orchestrator.route(user_msg, history)

    # 把决策写入状态
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
    """回退节点：无需专家时用通用LLM直接回答"""
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


# ═══════════════════════════════════════════
# 第3部分：定义路由函数
# ═══════════════════════════════════════════

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


# ═══════════════════════════════════════════
# 第4部分：构建图
# ═══════════════════════════════════════════

def build_supervisor_graph() -> StateGraph:
    """构建并编译 LangGraph 调度图"""
    workflow = StateGraph(SupervisorState)

    # 添加节点（Add nodes）
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("rag", rag_node)
    workflow.add_node("tool", tool_node)
    workflow.add_node("web", web_node)
    workflow.add_node("memory", memory_node)
    workflow.add_node("fallback", fallback_node)
    workflow.add_node("format_output", format_output_node)

    # 设置入口（Entry point）
    workflow.set_entry_point("supervisor")

    # 条件边：supervisor根据分析结果路由到不同的专家
    workflow.add_conditional_edges(
        "supervisor",
        router,  # 路由函数
        {
            "rag": "rag",
            "tool": "tool",
            "web": "web",
            "memory": "memory",
            "fallback": "fallback",
        },
    )

    # 直接边：所有专家 → 格式化输出 → 结束
    workflow.add_edge("rag", "format_output")
    workflow.add_edge("tool", "format_output")
    workflow.add_edge("web", "format_output")
    workflow.add_edge("memory", "format_output")
    workflow.add_edge("fallback", "format_output")
    workflow.add_edge("format_output", END)

    # 编译图（带检查点，支持保存状态）
    memory_saver = MemorySaver()
    graph = workflow.compile(checkpointer=memory_saver)
    return graph


# ═══════════════════════════════════════════
# 第5部分：图执行封装（给API层用的高层接口）
# ═══════════════════════════════════════════

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
        """非流式处理：通过图处理用户消息，返回完整结果"""
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
            # ⭐ 核心：把初始状态输入图，图自动按边流转
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
        """流式处理：逐步输出结果（SSE打字机效果）
        
        这是一个异步生成器，用 yield 逐步返回数据块。
        """
        from src.models.llm_client import build_llm, format_messages_for_llm

        try:
            # Phase 1: 分析意图、决定路由
            yield {"type": "status", "content": "analyzing"}

            orchestrator = OrchestratorAgent()
            decision = orchestrator.route(user_message, (history or [])[-10:])
            next_agent = (decision.get("next_agent", "") or "").lower()
            print(f"[调度器] 路由到：{next_agent}")

            yield {"type": "status", "content": "routing"}
            yield {"type": "node", "content": "supervisor"}

            # Phase 2: 根据路由准备上下文
            system_prompt = "你是一个有用的AI助手，请用中文回答用户的问题。"
            tools_for_llm = []
            extra_context = ""

            if next_agent == "rag_agent":
                yield {"type": "status", "content": "executing_rag"}
                yield {"type": "node", "content": "rag"}
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
                    if getattr(t, 'name', '') in ('web_search', 'web_fetch')
                ]
                system_prompt = "你是一个网络搜索智能体。用中文回答，可以搜索互联网获取最新信息。"

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

            # Phase 3: 流式调用LLM
            messages = format_messages_for_llm(
                system_prompt=system_prompt,
                history=history or [],
                user_message=user_message,
            )

            llm = build_llm(streaming=True, tools=tools_for_llm)
            full_response = ""

            for chunk in llm.stream(messages):
                if chunk.content:
                    full_response += chunk.content
                    yield {"type": "token", "content": chunk.content}

                # 处理流中的工具调用
                if hasattr(chunk, 'tool_calls') and chunk.tool_calls:
                    for tc in chunk.tool_calls:
                        if tc.get('name'):
                            tool_name = tc['name']
                            tool_args = tc.get('args', {})
                            from src.tools.tool_registry import tool_registry
                            tool_func = tool_registry.get_tool(tool_name)
                            if tool_func:
                                try:
                                    result = tool_func.invoke(tool_args) if hasattr(tool_func, 'invoke') else tool_func(**tool_args)
                                    full_response += f"\n\n[工具 {tool_name}: {result}]"
                                    yield {"type": "token", "content": f"\n\n🔧 {tool_name}: {result}\n\n"}
                                except Exception as e:
                                    yield {"type": "token", "content": f"\n工具错误: {e}\n"}

            # 保存结果到图状态
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


# 全局实例
supervisor_graph = SupervisorGraph()
```

---

## 15.4 流式处理的SSE事件类型

在 `stream_process` 方法中，我们通过 `yield` 返回不同类型的事件：

| 事件类型 | 含义 | 前端怎么用 |
|---------|------|-----------|
| `status: analyzing` | 正在分析意图 | 显示"分析中..." |
| `status: routing` | 正在路由 | 显示"路由中..." |
| `status: executing_rag` | 正在检索知识 | 显示"检索中..." |
| `status: executing_tool` | 正在执行工具 | 显示"执行中..." |
| `node: supervisor` | 经过supervisor节点 | 用于调试/可视化 |
| `node: rag` | 经过rag节点 | 用于调试/可视化 |
| `token: "你好"` | 实际的回复文字 | 逐字显示 |
| `done` | 处理完成 | 关闭连接 |

---

## 15.5 图的工作原理（重点理解）

```python
# 1. 初始状态
state = {"user_message": "公司有哪些产品？", "next_agent": "", ...}

# 2. 图从入口节点"supervisor"开始
#    supervisor节点运行 → state["next_agent"] = "rag_agent"

# 3. 条件边：router函数检查 state["next_agent"]
#    "rag_agent" → 路由到"rag"节点

# 4. rag节点运行 → state["agent_output"] = {...}, state["route_complete"] = True

# 5. 边：rag → format_output → END

# 6. 最终结果：state["final_response"] = "根据公司介绍，我们的产品包括..."
```

---

> **下一课**：[第16课：API层](./16-API层.md) —— 写FastAPI路由，暴露HTTP接口。

> ✅ **检验清单**：
> - [ ] `src/graphs/supervisor_graph.py` 已创建
> - [ ] 理解了State → Node → Edge → Conditional Edge的概念
> - [ ] 理解了监督者-工作者模式
