"""MCP 服务端 - 通过 Model Context Protocol 暴露智能体工具

允许外部 MCP 客户端发现和使用我们的工具。
"""
import json
import asyncio

from src.tools.tool_registry import tool_registry
from src.config import settings


class MCPServer:
    """轻量级 MCP 兼容工具服务器

    实现 MCP 协议的工具发现和执行功能，
    无需完整的 mcp SDK 运行时依赖。
    """

    def __init__(self):
        self.tools = tool_registry

    def list_tools(self) -> list[dict]:
        """以 MCP 格式返回所有可用工具"""
        tools = []
        for name in self.tools.list_tool_names():
            tool_defs = self.tools.get_definitions()
            for td in tool_defs:
                if td["function"]["name"] == name:
                    tools.append({
                        "name": name,
                        "description": td["function"]["description"],
                        "inputSchema": td["function"]["parameters"],
                    })
        return tools

    def call_tool(self, name: str, arguments: dict) -> dict:
        """按名称和参数执行工具"""
        tool_func = self.tools.get_tool(name)
        if not tool_func:
            return {
                "content": [{"type": "text", "text": f"工具未找到：{name}"}],
                "isError": True,
            }

        try:
            if hasattr(tool_func, "invoke"):
                result = tool_func.invoke(arguments)
            else:
                result = tool_func(**arguments)

            return {
                "content": [{"type": "text", "text": str(result)}],
                "isError": False,
            }
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"工具错误：{e}"}],
                "isError": True,
            }

    async def handle_request(self, request: dict) -> dict:
        """处理 JSON-RPC 格式的 MCP 请求"""
        method = request.get("method", "")
        req_id = request.get("id", 0)

        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": self.list_tools()},
            }
        elif method == "tools/call":
            params = request.get("params", {})
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            result = self.call_tool(tool_name, arguments)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": result,
            }
        elif method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {
                        "name": "deepseek-multi-agent",
                        "version": "1.0.0",
                    },
                    "capabilities": {"tools": {}},
                },
            }
        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"未知方法：{method}"},
            }


mcp_server = MCPServer()
