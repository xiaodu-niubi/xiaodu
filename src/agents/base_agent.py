"""ReAct 基类智能体 - 实现 Thought（思考）→ Action（行动）→ Observation（观察）循环

每个专用智能体继承此基类，自定义：
- system_prompt：智能体的角色和指令
- tools：智能体可用的工具集
"""
from typing import Optional
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.tools import BaseTool

from src.config import settings
from src.models.llm_client import build_llm, format_messages_for_llm


class BaseAgent:
    """ReAct 智能体基类，实现思考-行动-观察模式"""

    name: str = "base"
    system_prompt: str = "你是一个有用的助手。"
    tools: list = []
    max_iterations: int = 5

    def __init__(self):
        self._llm = None

    @property
    def llm(self):
        if self._llm is None:
            self._llm = build_llm(streaming=False, tools=self.tools)
        return self._llm

    def run(self, user_message: str, history: list[dict] = None) -> dict:
        """执行 ReAct 循环"""
        messages = format_messages_for_llm(
            system_prompt=self.system_prompt,
            history=history or [],
            user_message=user_message,
        )

        iteration = 0
        tool_calls_made = []
        observations = []

        while iteration < min(self.max_iterations, settings.max_agent_iterations):
            iteration += 1

            try:
                response = self.llm.invoke(messages)
            except Exception as e:
                return {"content": f"智能体错误：{e}", "tool_calls": tool_calls_made}

            # 检查是否有工具调用
            if hasattr(response, "tool_calls") and response.tool_calls:
                messages.append(response)

                for tc in response.tool_calls:
                    tool_name = tc.get("name", "")
                    tool_args = tc.get("args", {})
                    tool_id = tc.get("id", "")

                    result = self._execute_tool(tool_name, tool_args)
                    tool_calls_made.append({
                        "name": tool_name,
                        "args": tool_args,
                        "result": result,
                    })
                    observations.append(result)

                    messages.append(ToolMessage(content=str(result), tool_call_id=tool_id))
            else:
                # 最终答案 - 没有更多工具调用
                content = response.content if hasattr(response, "content") else str(response)

                return {
                    "content": content,
                    "tool_calls": tool_calls_made,
                    "iterations": iteration,
                }

        # 达到最大迭代次数，生成最终答案
        final_llm = build_llm(streaming=False)
        messages.append(HumanMessage(content=(
            "基于以上所有观察结果，提供你的最终综合答案。整合所有工具调用的信息。"
        )))
        final_response = final_llm.invoke(messages)
        content = final_response.content if hasattr(final_response, "content") else str(final_response)

        return {
            "content": content,
            "tool_calls": tool_calls_made,
            "iterations": iteration,
        }

    def _execute_tool(self, tool_name: str, tool_args: dict) -> str:
        """按名称执行工具，优先查注册中心，再查实例自身工具"""
        import inspect
        from src.tools.tool_registry import tool_registry

        def _get_param_hint(func) -> str:
            """获取工具函数的参数提示"""
            try:
                sig = inspect.signature(func)
                params = []
                for name, param in sig.parameters.items():
                    if name in ("self", "cls"):
                        continue
                    default = "" if param.default is inspect.Parameter.empty else f" = {param.default}"
                    params.append(f"{name}{default}")
                return "，".join(params) if params else "无参数"
            except Exception:
                return ""

        # 先查全局注册中心
        tool_func = tool_registry.get_tool(tool_name)
        if tool_func:
            # 如果参数为空，返回引导性错误帮助模型修正
            if not tool_args:
                hint = _get_param_hint(tool_func)
                return f"工具调用失败：'{tool_name}' 需要参数（{hint}），但收到了空参数。请用正确的参数重新调用，例如：如果用户问'123乘以456'，应调用 calculator(expression='123*456')。"
            try:
                result = tool_func.invoke(tool_args) if hasattr(tool_func, "invoke") else tool_func(**tool_args)
                return str(result)
            except Exception as e:
                hint = _get_param_hint(tool_func)
                return f"工具执行错误：{e}。该工具需要参数：{hint}。请用正确的参数重试。"

        # 再查实例自身的工具列表（如 RagAgent._knowledge_search_tool）
        for t in self.tools:
            name = getattr(t, 'name', None) or getattr(t, '__name__', '')
            if name == tool_name:
                if not tool_args:
                    hint = _get_param_hint(t)
                    return f"工具调用失败：'{tool_name}' 需要参数（{hint}），但收到了空参数。请用正确的参数重新调用。"
                try:
                    if hasattr(t, 'invoke'):
                        result = t.invoke(tool_args)
                    elif callable(t):
                        result = t(**tool_args)
                    else:
                        continue
                    return str(result)
                except Exception as e:
                    hint = _get_param_hint(t)
                    return f"工具执行错误：{e}。该工具需要参数：{hint}。请用正确的参数重试。"

        return f"未知工具：{tool_name}"
