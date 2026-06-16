"""网络搜索智能体 - 外部信息搜索专家

单一职责：搜索网页和获取网页内容以获取最新信息。
"""
from src.agents.base_agent import BaseAgent

WEB_AGENT_PROMPT = """你是一个网络搜索智能体。你的职责是从互联网上查找最新信息。

## 可用工具：
- **web_search（网络搜索）**：通过 DuckDuckGo 搜索网页
- **web_fetch（获取网页）**：获取并阅读指定网页内容
- **get_weather（天气查询）**：查询指定城市的实时天气信息（温度、湿度、风速、预报等）

## 工作流程：
1. 思考需要搜索什么
2. 使用 web_search 获取搜索结果
3. 如需详细阅读，使用 web_fetch 阅读特定页面
4. 将发现综合成清晰答案

## 规则：
- 回答网络相关问题前必须先搜索
- 在答案中引用来源（URL）
- 如果搜索失败，请坦诚说明
- 时事/新闻 → 使用 web_search
- 阅读特定页面 → 先用 web_search 找到 URL，再用 web_fetch"""


class WebAgent(BaseAgent):
    """网络搜索智能体"""

    name = "web_agent"
    system_prompt = WEB_AGENT_PROMPT
    max_iterations = 4

    def __init__(self):
        super().__init__()
        from src.tools.tool_registry import tool_registry
        self.tools = [
            tool_registry.get_tool("web_search"),
            tool_registry.get_tool("web_fetch"),
            tool_registry.get_tool("get_weather"),
        ]
