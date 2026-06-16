"""MCP 客户端 - 连接外部 MCP 服务器，发现和使用远程工具"""
import json
from typing import Optional

import httpx


class MCPClient:
    """连接外部 MCP 服务器的客户端"""

    def __init__(self, server_url: str = None):
        self.server_url = server_url or f"http://localhost:9000"
        self._tools_cache: Optional[list[dict]] = None

    async def initialize(self) -> dict:
        """初始化与 MCP 服务器的连接"""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.server_url}/mcp",
                json={"jsonrpc": "2.0", "id": 0, "method": "initialize"},
                timeout=10,
            )
            return resp.json()

    async def list_tools(self) -> list[dict]:
        """从远程 MCP 服务器获取可用工具列表"""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.server_url}/mcp",
                json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                timeout=10,
            )
            result = resp.json()
            tools = result.get("result", {}).get("tools", [])
            self._tools_cache = tools
            return tools

    async def call_tool(self, name: str, arguments: dict) -> dict:
        """调用远程 MCP 服务器上的工具"""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.server_url}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": name, "arguments": arguments},
                },
                timeout=30,
            )
            return resp.json()

    def get_tools_as_openai_schema(self) -> list[dict]:
        """将缓存的 MCP 工具转换为 OpenAI 函数调用模式"""
        if not self._tools_cache:
            return []

        schemas = []
        for tool in self._tools_cache:
            schemas.append({
                "type": "function",
                "function": {
                    "name": f"mcp_{tool['name']}",
                    "description": tool.get("description", ""),
                    "parameters": tool.get("inputSchema", {"type": "object", "properties": {}}),
                },
            })
        return schemas


mcp_client = MCPClient()
