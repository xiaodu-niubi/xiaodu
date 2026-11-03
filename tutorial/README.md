# 🎓 DeepSeek 多智能体系统 —— 从零搭建教程

> 本目录保留早期教学示例。当前工作台的启动和配置以根目录 README.md 为准：LLM_API_KEY 只从系统或启动进程的环境变量读取，.env 中的密钥不会生效。

> 🎯 **目标读者**：后端开发小白
> 📝 **教学方式**：每一步都详细讲解，不跳步骤
> 🛠️ **最终成果**：一个完整可运行的多智能体AI对话系统后端

---

## 📖 课程目录

| 课号 | 标题 | 核心内容 |
|------|------|---------|
| 1 | [项目概述](./01-项目概述.md) | 理解Agent、RAG、ReAct的概念 |
| 2 | [环境准备](./02-环境准备.md) | 安装Python、Docker，启动MySQL+Redis |
| 3 | [项目结构](./03-项目结构.md) | 创建目录骨架，安装Python依赖 |
| 4 | [配置管理](./04-配置管理.md) | 写.env文件和config.py |
| 5 | [MySQL数据库](./05-数据库层-MySQL.md) | 写MySQL客户端，增删改查对话和消息 |
| 6 | [Redis缓存](./06-数据库层-Redis.md) | 写Redis客户端，管理对话记忆 |
| 7 | [向量数据库](./07-数据库层-向量数据库.md) | 写本地向量存储，实现语义搜索 |
| 8 | [大模型客户端](./08-大模型客户端.md) | 封装DeepSeek API调用 |
| 9 | [工具系统](./09-工具系统.md) | 工具注册中心 + 计算器/时间/代码等工具 |
| 10 | [RAG上](./10-RAG知识检索上.md) | 嵌入模型 + 文档加载器 |
| 11 | [RAG下](./11-RAG知识检索下.md) | 查询分析器 + 检索器 |
| 12 | [Agent基类](./12-Agent基类.md) | ReAct循环：思考-行动-观察 |
| 13 | [编排智能体](./13-编排智能体.md) | Orchestrator：意图分析 + 路由 |
| 14 | [专用智能体](./14-专用智能体.md) | RAG/Tool/Web/Memory四大专家 |
| 15 | [LangGraph编排图](./15-LangGraph编排图.md) | 状态图把智能体串起来 |
| 16 | [API层](./16-API层.md) | FastAPI路由 + SSE流式输出 |
| 17 | [启动与测试](./17-启动与测试.md) | 启动系统，全面测试 |

---

## 🚀 快速导航

### 如果你是纯小白：
- 从第1课开始，按顺序学
- 每课都动手敲代码
- 每课学完运行测试，确认通过再继续

### 如果你有一定基础：
- 第1课了解项目概况
- 第2-4课可快速过
- 重点看第8-16课（核心逻辑）

### 如果你想快速跑起来：
```bash
# 1. 启动数据库
docker compose up -d

# 2. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置API密钥
cp .env.example .env
# 编辑.env，填你的LLM_API_KEY

# 5. 加载知识库
python -m src.rag.document_loader

# 6. 启动
python -m src.main

# 7. 打开 http://localhost:8000/docs 测试
```

---

## 📁 配套代码

所有代码在 `D:\code\deepseek\src\` 目录下。按照教程顺序，每课的代码对应以下文件：

```
src/
├── config.py                    ← 第4课
├── main.py                      ← 第16课
├── database/
│   ├── mysql_client.py          ← 第5课
│   ├── redis_client.py          ← 第6课
│   └── chroma_client.py         ← 第7课
├── models/
│   ├── schemas.py               ← 第8课
│   └── llm_client.py            ← 第8课
├── tools/
│   ├── tool_registry.py         ← 第9课
│   ├── builtin_tools.py         ← 第9课
│   ├── web_search.py            ← 第9课
│   └── file_tools.py            ← 第9课
├── rag/
│   ├── embedder.py              ← 第10课
│   ├── document_loader.py       ← 第10课
│   ├── query_analyzer.py        ← 第11课
│   └── retriever.py             ← 第11课
├── agents/
│   ├── base_agent.py            ← 第12课
│   ├── orchestrator.py          ← 第13课
│   ├── rag_agent.py             ← 第14课
│   ├── tool_agent.py            ← 第14课
│   ├── web_agent.py             ← 第14课
│   └── memory_agent.py          ← 第14课
├── graphs/
│   └── supervisor_graph.py      ← 第15课
├── memory/
│   ├── conversation.py          ← 第14课
│   └── context_builder.py       ← 第14课
└── api/
    ├── chat_router.py           ← 第16课
    ├── conversation_router.py   ← 第16课
    └── knowledge_router.py      ← 第16课
```

---

## 💡 学习建议

1. **不要跳课**：后面的课依赖前面的代码
2. **动手敲代码**：不要复制粘贴，手打一遍加深记忆
3. **理解核心概念**：Agent > RAG > ReAct > LangGraph 这个顺序理解
4. **遇到错误先自己排查**：看终端报错信息，检查文件路径和导入
5. **每课结束后运行测试**：确保代码正确再继续

---

## ❓ 遇到问题？

- 检查Docker容器是否在运行：`docker ps`
- 检查虚拟环境是否激活：终端前应有 `(.venv)`
- 检查 `.env` 中的API密钥是否正确
- 看终端报错信息的最后几行，通常能找到原因
