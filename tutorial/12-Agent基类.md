# 第12课：Agent基类 —— 实现ReAct思考-行动-观察循环

> 🎯 **本课目标**：写智能体基类BaseAgent，实现ReAct循环（思考→行动→观察→再思考）。

---

## 12.1 什么是ReAct模式？

ReAct = **Re**asoning（推理）+ **Act**ing（行动）

这是智能体的核心工作模式。你能想象一个不给工具的助手——只能空想。ReAct让智能体循环地"思考→调用工具→观察结果→再思考"，直到能给出最终答案。

### 一个具体例子：用户问"公司有哪些产品？"

```
┌─ 第1轮 ─────────────────────────────┐
│ 思考（Thought）：用户想知道公司产品，  │
│   我需要查知识库                       │
│ 行动（Action）：调用 knowledge_search  │
│   参数 query="公司产品列表"           │
│ 观察（Observation）：返回了3个文档块   │
│   [company_intro.md] 核心产品包括...  │
└──────────────────────────────────────┘
         ↓ 信息还不够？再来一轮
┌─ 第2轮 ─────────────────────────────┐
│ 思考：需要更详细的产品功能信息         │
│ 行动：调用 knowledge_search           │
│   参数 query="产品功能特性"           │
│ 观察：返回了2个文档块                  │
│   [product_manual.txt] ...           │
└──────────────────────────────────────┘
         ↓ 信息够了
┌─ 最终回答 ──────────────────────────┐
│ "根据公司介绍，我们的核心产品包括：    │
│  1. DeepSeek大语言模型...             │
│  2. API服务...                       │
│  3. 企业定制方案..."                  │
└──────────────────────────────────────┘
```

---

## 12.2 BaseAgent的设计思路

所有智能体（RAG智能体、工具智能体、网络智能体等）都继承这个基类。基类负责：
1. 管理消息历史
2. 调用LLM
3. 执行工具调用
4. 控制循环次数

子类只需要提供：
- `system_prompt`：智能体的"角色设定"
- `tools`：智能体能用的工具列表

---

## 12.3 写代码：`src/agents/base_agent.py`

```python
"""ReAct 基类智能体 - 实现 Thought（思考）→ Action（行动）→ Observation（观察）循环

每个专用智能体继承此基类，自定义：
- system_prompt：智能体的角色和指令
- tools：智能体可用的工具集
- max_iterations：最大循环次数（防止死循环）
"""
from typing import Optional
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage

from src.config import settings
from src.models.llm_client import build_llm, format_messages_for_llm


class BaseAgent:
    """ReAct 智能体基类
    
    子类需要设置以下属性：
    - name: 智能体名称（如 "rag_agent"）
    - system_prompt: 系统提示（定义角色和行为）
    - tools: 可用工具列表
    - max_iterations: 最大循环次数
    """

    name: str = "base"
    system_prompt: str = "你是一个有用的助手。"
    tools: list = []
    max_iterations: int = 5

    def __init__(self):
        self._llm = None  # 懒加载，第一次使用时才创建

    @property
    def llm(self):
        """获取LLM实例（绑定了工具）"""
        if self._llm is None:
            self._llm = build_llm(streaming=False, tools=self.tools)
        return self._llm

    def run(self, user_message: str, history: list[dict] = None) -> dict:
        """执行 ReAct 循环
        
        参数：
        - user_message: 用户的问题
        - history: 之前的对话历史
        
        返回：
        {
            "content": "最终回答",
            "tool_calls": [{"name": "工具名", "args": {...}, "result": "结果"}, ...],
            "iterations": 3
        }
        """
        # 第1步：组装消息（系统提示 + 历史 + 当前问题）
        messages = format_messages_for_llm(
            system_prompt=self.system_prompt,
            history=history or [],
            user_message=user_message,
        )

        iteration = 0
        tool_calls_made = []   # 记录所有工具调用
        observations = []      # 记录所有观察结果

        # 第2步：ReAct循环
        while iteration < min(self.max_iterations, settings.max_agent_iterations):
            iteration += 1

            # 2a. 调用LLM
            try:
                response = self.llm.invoke(messages)
            except Exception as e:
                return {"content": f"智能体错误：{e}", "tool_calls": tool_calls_made}

            # 2b. 检查LLM是否想调用工具
            if hasattr(response, "tool_calls") and response.tool_calls:
                # LLM想调用工具，把它的回复加入消息历史
                messages.append(response)

                for tc in response.tool_calls:
                    tool_name = tc.get("name", "")
                    tool_args = tc.get("args", {})
                    tool_id = tc.get("id", "")

                    print(f"  [{self.name}] 🔧 调用工具: {tool_name}({tool_args})")

                    # 执行工具
                    result = self._execute_tool(tool_name, tool_args)
                    tool_calls_made.append({
                        "name": tool_name,
                        "args": tool_args,
                        "result": result,
                    })
                    observations.append(result)

                    # 把工具执行结果加入消息历史
                    messages.append(ToolMessage(content=str(result), tool_call_id=tool_id))

                # 继续循环，让LLM看到工具结果后再思考
                continue

            else:
                # 2c. LLM没有调用工具 → 这是最终答案
                content = response.content if hasattr(response, "content") else str(response)

                return {
                    "content": content,
                    "tool_calls": tool_calls_made,
                    "iterations": iteration,
                }

        # 第3步：达到最大循环次数，强制生成最终答案
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
        """按名称执行工具
        
        查找顺序：
        1. 全局工具注册中心（tool_registry）
        2. 本智能体自带的工具列表
        """
        from src.tools.tool_registry import tool_registry

        # 先查全局注册中心
        tool_func = tool_registry.get_tool(tool_name)
        if tool_func:
            try:
                result = tool_func.invoke(tool_args) if hasattr(tool_func, "invoke") else tool_func(**tool_args)
                return str(result)
            except Exception as e:
                return f"工具执行错误：{e}"

        # 再查本实例的工具列表
        for t in self.tools:
            name = getattr(t, 'name', None) or getattr(t, '__name__', '')
            if name == tool_name:
                try:
                    if hasattr(t, 'invoke'):
                        result = t.invoke(tool_args)
                    elif callable(t):
                        result = t(**tool_args)
                    else:
                        continue
                    return str(result)
                except Exception as e:
                    return f"工具执行错误：{e}"

        return f"未知工具：{tool_name}"
```

---

## 12.4 ReAct循环图解

```
         ┌──────────────────┐
         │   用户提问        │
         └──────┬───────────┘
                │
                ▼
    ┌───────────────────────┐
    │  组装消息             │
    │  SystemMessage +      │
    │  History +            │
    │  HumanMessage         │
    └───────┬───────────────┘
            │
            ▼
    ╔═══════════════════════╗
    ║     ReAct 循环        ║
    ║                       ║
    ║  ┌─ LLM.invoke() ──┐  ║
    ║  │ 思考 + 决策     │  ║
    ║  └──┬──────────┬───┘  ║
    ║     │          │      ║
    ║  有工具调用  无工具调用 ║
    ║     │          │      ║
    ║     ▼          ▼      ║
    ║  执行工具    返回最终  ║
    ║     │        答案     ║
    ║     ▼                ║
    ║  观察结果            ║
    ║     │                ║
    ║  重新循环 ──→        ║
    ╚═══════════════════════╝
```

---

## 12.5 测试BaseAgent

创建 `test_agent.py`：

```python
"""测试BaseAgent基类"""
from src.agents.base_agent import BaseAgent
from src.tools.tool_registry import tool_registry
# 导入工具，触发注册
from src.tools.builtin_tools import calculator, get_current_time

# 创建一个简单的测试智能体
class TestAgent(BaseAgent):
    name = "test_agent"
    system_prompt = """你是一个数学助手。用户问数学题时，必须使用calculator工具计算，不要自己算。
    如果不是数学题，就用你的知识直接回答。"""
    tools = [tool_registry.get_tool("calculator"), tool_registry.get_tool("get_current_time")]
    max_iterations = 3


print("=" * 60)
print("测试BaseAgent ReAct循环")
print("=" * 60)

agent = TestAgent()

# 测试1：数学问题（需要调用工具）
print("\n--- 测试1：数学计算 ---")
result = agent.run("计算 12345 * 67890")
print(f"最终答案：{result['content'][:200]}")
print(f"迭代次数：{result['iterations']}")
print(f"工具调用：{len(result['tool_calls'])} 次")
for tc in result['tool_calls']:
    print(f"  - {tc['name']}({tc['args']}) = {tc['result'][:80]}")

# 测试2：常识问题（不需要工具）
print("\n--- 测试2：常识问题 ---")
result = agent.run("Python是什么？用一句话回答")
print(f"最终答案：{result['content'][:200]}")
print(f"迭代次数：{result['iterations']}")
print(f"工具调用：{len(result['tool_calls'])} 次")

# 测试3：时间查询（调用另一个工具）
print("\n--- 测试3：时间查询 ---")
result = agent.run("现在是几点？")
print(f"最终答案：{result['content'][:200]}")
print(f"工具调用：{len(result['tool_calls'])} 次")

print("\n✅ BaseAgent ReAct测试完成！")
```

运行：
```bash
python test_agent.py
```

观察输出中的 `[test_agent] 🔧 调用工具: calculator(...)`，这就是ReAct循环在工作。

---

> **下一课**：[第13课：编排智能体](./13-编排智能体.md) —— 实现Orchestrator，分析用户意图并路由到合适的专家。

> ✅ **检验清单**：
> - [ ] `src/agents/base_agent.py` 已创建
> - [ ] `python test_agent.py` 能看到ReAct循环日志
> - [ ] 理解了"思考→行动→观察→再思考"的循环逻辑
