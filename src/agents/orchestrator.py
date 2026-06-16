"""编排智能体 - 总调度器，负责分析用户意图并将任务路由到专用智能体

单一职责：分析用户意图，委派给正确的智能体。
不执行工具调用，不检索知识。

优化：先用关键词快速匹配，命中则跳过 LLM 调用。
"""
import re
from src.agents.base_agent import BaseAgent

# 快速路由规则 — 关键词匹配命中后直接跳过 LLM 调用
_QUICK_ROUTES = [
    # (关键词列表, 路由目标, 理由)
    (["天气", "气温", "温度", "下雨", "刮风", "下雪", "雾霾", "weather", "下雨吗", "热吗", "冷吗", "湿度"], "web_agent"),
    (["计算", "等于", "多少", "加", "减", "乘", "除", "平方", "开方", "log", "sqrt"], "tool_agent"),
    (["现在几点", "几点了", "当前时间", "日期", "星期几"], "tool_agent"),
    (["转换单位", "单位换算", "厘米", "英寸", "英里", "公里换算", "千克", "磅"], "tool_agent"),
    (["运行这段代码", "执行代码", "这段代码"], "tool_agent"),
    (["搜索", "查一下", "最新的", "新闻"], "web_agent"),
    (["你好", "嗨", "谢谢", "再见", "拜拜"], None),
    (["你是谁", "你叫什么", "介绍自己", "你能做什么"], None),
]

ORCHESTRATOR_PROMPT = """你是多智能体系统的编排智能体。你唯一的职责是分析用户请求并将其路由到合适的专用智能体。

## 可路由的智能体：
1. **rag_agent（知识检索智能体）** - 用于需要从文档、手册、政策、FAQ、公司信息中检索知识的问题
2. **tool_agent（工具执行智能体）** - 用于计算、代码执行、单位转换、文件操作、时间查询
3. **web_agent（网络搜索智能体）** - 用于搜索网页、获取URL、查找最新信息
4. **memory_agent（记忆智能体）** - 用于关于对话历史、用户偏好、历史上下文的问题

## 决策规则：
- 用户询问公司信息、产品详情、政策、技术规格或FAQ → **rag_agent**
- 用户需要纯数学计算、单位转换、时间查询、运行已有代码 → **tool_agent**
- 用户需要实时/网络信息（如天气查询） → **web_agent**
- 用户询问之前的对话或偏好 → **memory_agent**
- 用户要求生成/编写代码、写脚本、写程序、写游戏等创意性编程任务 → **next_agent 设为 null**（走通用LLM直接生成，不经过受限的tool_agent prompt）

## 重要区分：
- "帮我运行这段python代码" → tool_agent（执行已有代码）
- "帮我写一个贪吃蛇游戏" → null（代码生成，走通用模型）
- "计算 123*456" → tool_agent（纯计算）
- "用python写一个处理excel的脚本" → null（代码生成）

## 输出格式：
仅以 JSON 格式回复路由决策：
```json
{
  "next_agent": "<智能体名称 或 null>",
  "reasoning": "<简要原因>",
  "sub_message": "<发送给智能体的原始或优化后的查询>",
  "requires_multi_agent": false
}
```

如果需要多个智能体协作，将 requires_multi_agent 设置为 true 并按顺序列出智能体。
对于无需专家的简单问候、闲聊、代码生成，将 next_agent 设为 null。"""


class OrchestratorAgent(BaseAgent):
    """编排智能体 - 分析并路由请求"""

    name = "orchestrator"
    system_prompt = ORCHESTRATOR_PROMPT
    tools = []
    max_iterations = 3

    def _quick_route(self, user_message: str) -> dict | None:
        """关键词快速匹配，命中则直接返回路由决策，跳过 LLM 调用"""
        msg_lower = user_message.lower()
        for keywords, target in _QUICK_ROUTES:
            if any(kw in msg_lower for kw in keywords):
                return {
                    "next_agent": target,
                    "reasoning": f"关键词快速匹配",
                    "sub_message": user_message,
                }
        return None

    def route(self, user_message: str, history: list[dict] = None) -> dict:
        """分析并路由请求，优先使用关键词快速匹配"""
        import json

        # 尝试关键词快速匹配
        quick = self._quick_route(user_message)
        if quick:
            return quick

        result = self.run(user_message, history)

        # 从响应中解析 JSON
        content = result.get("content", "")
        try:
            decision = json.loads(content)
        except json.JSONDecodeError:
            # 尝试从 markdown 代码块中提取 JSON
            match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
            if match:
                try:
                    decision = json.loads(match.group(1))
                except json.JSONDecodeError:
                    decision = {"next_agent": None, "reasoning": "解析失败", "sub_message": user_message}
            else:
                decision = {"next_agent": None, "reasoning": "解析失败", "sub_message": user_message}

        return decision
