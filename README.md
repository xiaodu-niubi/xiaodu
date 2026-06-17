<div align="center">
  <h1>DeepSeek 多智能体系统</h1>
  <p><strong>基于 LangGraph 的多智能体协作平台</strong></p>
  <p>
    <a href="#快速开始">快速开始</a> •
    <a href="#系统架构">系统架构</a> •
    <a href="#api-端点">API 端点</a> •
    <a href="#项目结构">项目结构</a> •
    <a href="#配置说明">配置说明</a>
  </p>
  <p>
    <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python" alt="Python">
    <img src="https://img.shields.io/badge/Vue-3.4+-green?logo=vue.js" alt="Vue">
    <img src="https://img.shields.io/badge/FastAPI-0.115+-teal?logo=fastapi" alt="FastAPI">
    <img src="https://img.shields.io/badge/LangGraph-0.2+-orange?logo=langchain" alt="LangGraph">
    <img src="https://img.shields.io/badge/MySQL-8.0-blue?logo=mysql" alt="MySQL">
    <img src="https://img.shields.io/badge/Redis-7-red?logo=redis" alt="Redis">
    <img src="https://img.shields.io/badge/License-MIT-yellow" alt="License">
  </p>
</div>

---

## 项目简介

一个基于 LangGraph 的多智能体协作系统，实现 Agentic RAG（动态知识检索）、ReAct 推理、函数调用和 MCP 协议。前端 Vue 3 暗色主题，后端 FastAPI + SSE 流式输出。

### 核心能力

- **多智能体协作** — 5 个专职智能体通过 LangGraph 编排协作
- **Agentic RAG** — 智能体自主决策何时检索、检索什么，多跳检索 + 去重 + 重排序
- **ReAct 推理** — Thought → Action → Observation 循环，LLM 自主推理调用工具
- **函数调用** — 计算器、代码执行、单位换算、文件读写、网络搜索、天气查询等工具
- **MCP 协议** — JSON-RPC 标准化工具接口，支持接入外部 MCP 工具服务器
- **SSE 流式输出** — 真正的 token 级实时流式传输，支持中途暂停生成
- **对话记忆** — Redis 多轮对话上下文 + MySQL 持久化历史 + 智能上下文窗口管理

### 前端体验

- 暗色主题，紫色渐变配色
- 流式打字效果，实时显示 AI 回复
- 停止生成按钮（保留已输出内容）
- 状态提示（分析中 → 路由中 → 检索中 → 生成中）
- 对话管理（新建/切换/删除）
- 工具调用可视化展示

---

## 快速开始

### 环境要求

| 软件 | 最低版本 | 用途 |
|------|---------|------|
| Docker + Compose | 20.10+ | 运行 MySQL + Redis |
| Python | 3.10+ | 后端服务 |
| Node.js | 18+ | 前端构建 |

### 1. 克隆项目

```bash
git clone https://github.com/xiaodu-niubi/xiaodu.git
cd xiaodu
```

### 2. 启动数据库

```bash
docker compose up -d
```

首次启动会自动拉取 MySQL 8.0 和 Redis 7 镜像并初始化数据库。

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入你的 DeepSeek API Key
```

**必须配置**：
- `LLM_API_KEY` — [DeepSeek API Key](https://platform.deepseek.com/api_keys)

### 4. 安装依赖

```bash
# 后端
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 前端
cd frontend
npm install
```

### 5. 启动服务

```bash
# 终端 1：启动后端
python -m src.main

# 终端 2：启动前端
cd frontend && npm run dev
```

### 6. 访问系统

- 前端界面: http://localhost:5173
- API 文档 (Swagger): http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

> 详细搭建说明和问题排查见 [SETUP.md](SETUP.md)

---

## 系统架构

```
用户浏览器 (Vue 3)
    │  SSE 流式连接
    ▼
FastAPI 后端 (:8000)
    │
    ├─ /api/chat          聊天（流式 + 非流式）
    ├─ /api/conversations 对话 CRUD
    ├─ /api/knowledge     知识库管理
    └─ /api/tools         工具列表
    │
    ▼
LangGraph 调度图
    │
    ├─ Orchestrator ── 意图分析 → 路由分发
    │
    ├─ RAG Agent ───── 从向量库检索知识
    │    └─ QueryAnalyzer → AgenticRetriever → 重排序
    │
    ├─ Tool Agent ──── 函数调用执行
    │    └─ 计算/代码/文件/搜索/天气...
    │
    ├─ Web Agent ───── 互联网搜索
    │    └─ DuckDuckGo + 网页抓取
    │
    └─ Memory Agent ── 对话记忆管理
         └─ Redis 上下文 + 偏好
    │
    ▼
存储层
    ├─ MySQL 8.0    对话历史 + 消息 + 文档注册
    ├─ Redis 7      会话记忆 + 智能体状态
    └─ 向量库       知识文档嵌入 + 相似度检索
```

### 智能体说明

| 智能体 | 触发场景 | 可用工具 |
|--------|---------|---------|
| **Orchestrator** | 所有请求首先经过 | 意图分类、路由决策 |
| **RAG Agent** | 公司信息、产品、FAQ | knowledge_search |
| **Tool Agent** | 计算、代码、换算、天气 | calculator, python_repl, unit_converter, get_weather |
| **Web Agent** | 实时信息、外部搜索 | web_search, web_fetch |
| **Memory Agent** | 多轮对话、偏好 | conversation_memory |

---

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/chat` | 聊天（`stream: true` 返回 SSE） |
| `GET` | `/api/conversations` | 对话列表 |
| `POST` | `/api/conversations` | 新建对话 |
| `GET` | `/api/conversations/{id}` | 对话详情 + 消息 |
| `DELETE` | `/api/conversations/{id}` | 删除对话 |
| `GET` | `/api/knowledge/list` | 知识库文档列表 |
| `POST` | `/api/knowledge/upload` | 上传文档 |
| `POST` | `/api/knowledge/reload` | 重新加载知识库 |
| `GET` | `/api/tools` | 可用工具列表 |
| `POST` | `/api/mcp` | MCP JSON-RPC 端点 |
| `GET` | `/health` | 健康检查 |

---

## 项目结构

```
.
├── .env.example                # 环境变量模板（可提交）
├── .env                        # 实际配置（gitignore，含密钥）
├── .gitignore
├── docker-compose.yml          # MySQL + Redis 容器编排
├── init.sql                    # 数据库建表脚本
├── requirements.txt            # Python 依赖清单
│
├── knowledge_base/             # 知识库文档
│   ├── company_intro.md        #   公司介绍
│   ├── product_manual.txt      #   产品手册
│   ├── faq.md                  #   常见问题
│   ├── technical_specs.md      #   技术规格
│   └── policies.txt            #   政策文件
│
├── src/                        # 后端源码
│   ├── main.py                 #   FastAPI 入口，路由注册
│   ├── config.py               #   配置读取（pydantic-settings）
│   ├── agents/                 #   智能体
│   │   ├── base_agent.py       #     ReAct 基类
│   │   ├── orchestrator.py     #     编排智能体
│   │   ├── rag_agent.py        #     知识检索智能体
│   │   ├── tool_agent.py       #     工具调用智能体
│   │   ├── web_agent.py        #     网络搜索智能体
│   │   └── memory_agent.py     #     记忆管理智能体
│   ├── graphs/                 #   LangGraph 调度图
│   │   └── supervisor_graph.py #     监督者-工作者图
│   ├── tools/                  #   工具系统
│   │   ├── tool_registry.py    #     工具注册中心
│   │   ├── builtin_tools.py    #     计算器/时间/换算/代码
│   │   ├── web_search.py       #     网络搜索/网页抓取
│   │   ├── file_tools.py       #     文件读写
│   │   └── weather_tools.py    #     天气查询
│   ├── rag/                    #   Agentic RAG
│   │   ├── query_analyzer.py   #     查询分析与意图判断
│   │   ├── retriever.py        #     多跳检索+去重+重排序
│   │   ├── document_loader.py  #     文档加载与分块
│   │   └── embedder.py         #     文本嵌入
│   ├── mcp/                    #   MCP 协议
│   │   ├── mcp_server.py       #     MCP 服务端
│   │   └── mcp_client.py       #     MCP 客户端
│   ├── memory/                 #   记忆管理
│   │   ├── conversation.py     #     Redis 会话记忆
│   │   └── context_builder.py  #     上下文窗口构建
│   ├── database/               #   数据层
│   │   ├── mysql_client.py     #     MySQL 操作
│   │   ├── redis_client.py     #     Redis 操作
│   │   └── chroma_client.py    #     向量库（numpy 本地实现）
│   ├── models/                 #   数据模型
│   │   ├── schemas.py          #     Pydantic 请求/响应模型
│   │   └── llm_client.py       #     LLM 客户端封装
│   └── api/                    #   API 路由
│       ├── chat_router.py      #     聊天端点（SSE 流式）
│       ├── conversation_router.py  # 对话 CRUD
│       └── knowledge_router.py #     知识库管理
│
└── frontend/                   # Vue 3 前端
    ├── package.json
    ├── vite.config.js
    └── src/
        ├── App.vue             #   根布局（侧边栏 + 主区域）
        ├── style.css           #   暗色主题 CSS 变量
        ├── views/
        │   └── ChatView.vue    #   聊天主页面
        ├── components/
        │   ├── ConversationList.vue  # 侧边栏对话列表
        │   ├── ChatMessage.vue      # 消息气泡
        │   └── ChatInput.vue        # 输入框 + 停止按钮
        ├── stores/
        │   └── chat.js         #   Pinia 状态管理
        └── api/
            └── index.js        #   API 客户端
```

---

## 配置说明

完整配置项见 `.env.example`，主要配置：

| 配置项 | 说明 | 必须 |
|--------|------|------|
| `LLM_API_KEY` | DeepSeek API Key | ✅ |
| `LLM_MODEL` | 模型名称（默认 deepseek-v4-pro） | - |
| `LLM_BASE_URL` | API 地址（默认 DeepSeek 官方） | - |
| `MYSQL_*` | MySQL 连接（默认 localhost:3307） | - |
| `REDIS_*` | Redis 连接（默认 localhost:6379） | - |
| `MAX_AGENT_ITERATIONS` | ReAct 最大循环次数（默认 10） | - |

---

## 技术栈

| 分类 | 技术 | 版本 |
|------|------|------|
| LLM API | DeepSeek（兼容 OpenAI） | deepseek-v4-pro |
| Agent 框架 | LangChain + LangGraph | 0.3.x / 0.2.x |
| 后端 | FastAPI + Uvicorn | 0.115 / 0.34 |
| 前端 | Vue 3 + Pinia + Vite | 3.4 / 2.1 / 5.0 |
| 数据库 | MySQL | 8.0 |
| 缓存 | Redis | 7 |
| 嵌入 | sentence-transformers | 3.4 |
| MCP | mcp（官方 SDK） | 1.4 |

---

## 贡献指南

欢迎提交 Issue 和 Pull Request。

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

---

## 许可证

本项目采用 [MIT License](LICENSE) 开源许可证。

---

<div align="center">
  <p>如果这个项目对你有帮助，请给一个 ⭐ Star 支持一下！</p>
</div>
