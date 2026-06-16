"""工具注册中心 - 函数调用工具发现与注册"""
from typing import Callable
from langchain_core.tools import tool


class ToolRegistry:
    """所有可调用工具的中央注册表（单例模式）"""

    _instance = None # 单例实例
    _tools: dict[str, Callable] = {} # 工具函数
    _definitions: list[dict] = [] # 工具定义

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register(self, func: Callable) -> Callable:
        """注册一个工具函数"""
        tool_def = tool(func)
        self._tools[func.__name__] = tool_def
        self._definitions.append(self._to_openai_schema(func))
        return func

    def get_tool(self, name: str) -> Callable:
        """按名称获取工具"""
        return self._tools.get(name)

    def get_all_tools(self) -> list:
        """获取所有已注册工具"""
        return list(self._tools.values())

    def get_definitions(self) -> list[dict]:
        """获取所有工具的 OpenAI 函数调用模式定义"""
        return self._definitions

    def list_tool_names(self) -> list[str]:
        """列出所有工具名称"""
        return list(self._tools.keys())

    @staticmethod
    def _to_openai_schema(func: Callable) -> dict:
        """从工具函数提取 OpenAI 函数调用 JSON Schema"""
        import inspect
        sig = inspect.signature(func)
        doc = (func.__doc__ or "").strip()

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
            props[name] = {"type": param_type, "description": f"参数：{name}"}
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


tool_registry = ToolRegistry()
