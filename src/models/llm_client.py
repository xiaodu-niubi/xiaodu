"""大模型客户端 - 兼容 OpenAI/DeepSeek API"""
import json
from typing import Optional, AsyncIterator

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_core.tools import BaseTool

from src.config import settings


class MissingModelCredentialsError(RuntimeError):
    """The backend process did not inherit a model API key."""


def build_llm(
    temperature: Optional[float] = None,
    streaming: bool = True,
    tools: Optional[list] = None,
) -> ChatOpenAI:
    """构建 LangChain 兼容的 LLM 实例，指向 DeepSeek API"""
    if not settings.llm_api_key:
        raise MissingModelCredentialsError("未配置模型密钥，请设置环境变量 LLM_API_KEY，然后重启后端。")
    kwargs = dict(
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        temperature=settings.llm_temperature if temperature is None else temperature,
        max_tokens=settings.llm_max_tokens,
        streaming=streaming,
        timeout=60,
        max_retries=1,
    )
    llm = ChatOpenAI(**kwargs)

    if tools:
        # 将工具转换为 OpenAI 格式并用 bind_tools 绑定
        converted = []
        for t in tools:
            if isinstance(t, dict):
                converted.append(t)
            elif isinstance(t, BaseTool):
                converted.append(_base_tool_to_openai_schema(t))
            elif callable(t):
                converted.append(_function_to_openai_schema(t))
        if converted:
            llm = llm.bind_tools(converted)

    return llm


def _function_to_openai_schema(func) -> dict:
    """将 Python 函数转换为 OpenAI 工具定义模式"""
    import inspect
    sig = inspect.signature(func)
    doc = (func.__doc__ or func.__name__).strip()

    # 常用参数名 → 中文描述映射
    PARAM_HINTS: dict[str, str] = {
        "expression": "要计算的数学表达式，如 '123*456'、'sqrt(16)'",
        "code": "要执行的 Python 代码",
        "text": "需要统计令牌数的文本内容",
        "value": "要转换的数值",
        "from_unit": "源单位，如 m/km/g/kg/C/F",
        "to_unit": "目标单位，如 m/km/g/kg/C/F",
        "timezone": "时区名称，如 Asia/Shanghai、UTC（可选）",
        "query": "检索查询关键词",
        "url": "网页 URL 地址",
        "filename": "文件名（含路径）",
    }

    props = {}
    required = []
    for name, param in sig.parameters.items():
        if name in ("self", "cls"):
            continue
        param_type = "string"
        if param.annotation is not inspect.Parameter.empty:
            anno = param.annotation
            type_map = {int: "integer", float: "number", bool: "boolean", str: "string"}
            param_type = type_map.get(anno, "string")
        props[name] = {"type": param_type, "description": PARAM_HINTS.get(name, name)}
        if param.default is inspect.Parameter.empty:
            required.append(name)

    return {
        "type": "function",
        "function": {
            "name": func.__name__,
            "description": doc,
            "parameters": {
                "type": "object",
                "properties": props,
                "required": required,
            },
        },
    }


def _base_tool_to_openai_schema(t: BaseTool) -> dict:
    """将 LangChain BaseTool 实例转换为 OpenAI 工具定义模式"""
    # 尝试从 args_schema（Pydantic 模型）提取 JSON Schema
    params = {"type": "object", "properties": {}}
    if hasattr(t, 'args_schema') and t.args_schema:
        try:
            params = t.args_schema.model_json_schema()
        except Exception:
            pass
    elif hasattr(t, 'args'):
        raw = t.args
        if isinstance(raw, dict) and 'type' in raw:
            params = raw

    return {
        "type": "function",
        "function": {
            "name": t.name,
            "description": t.description or "",
            "parameters": params,
        },
    }


def format_messages_for_llm(
    system_prompt: str,
    history: list[dict],
    user_message: str,
) -> list[BaseMessage]:
    """将系统提示、历史记录和当前消息组装为 LLM 消息列表"""
    messages: list[BaseMessage] = [SystemMessage(content=system_prompt)]

    for msg in history[-settings.max_context_messages:]:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
        elif role == "system":
            messages.append(SystemMessage(content=content))

    messages.append(HumanMessage(content=user_message))
    return messages


def parse_tool_calls(response) -> list[dict]:
    """从 LLM 响应中提取工具调用"""
    tool_calls = []
    if hasattr(response, "tool_calls") and response.tool_calls:
        for tc in response.tool_calls:
            tool_calls.append({
                "name": tc.get("name", ""),
                "args": tc.get("args", {}),
                "id": tc.get("id", ""),
            })
    return tool_calls
