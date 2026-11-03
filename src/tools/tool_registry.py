"""工具注册中心 - 函数调用工具发现与注册"""
from typing import Callable
from langchain_core.tools import tool


class ToolRegistry:
    """所有可调用工具的中央注册表（单例模式）"""

    _instance = None
    _tools: dict[str, Callable] = {}
    _definitions: list[dict] = []

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
            desc = PARAM_HINTS.get(name, f"参数：{name}")
            props[name] = {"type": param_type, "description": desc}
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
