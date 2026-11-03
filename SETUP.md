# 搭建与启动指南

从零搭建 DeepSeek 多智能体系统的完整流程。

---

## 目录

1. [环境要求](#1-环境要求)
2. [安装 Docker 并启动数据库](#2-安装-docker-并启动数据库)
3. [安装 Python 依赖](#3-安装-python-依赖)
4. [配置环境变量](#4-配置环境变量)
5. [加载知识库](#5-加载知识库)
6. [启动后端服务](#6-启动后端服务)
7. [启动前端服务](#7-启动前端服务)
8. [验证系统](#8-验证系统)
9. [常见问题排查](#9-常见问题排查)

---

## 1. 环境要求

| 软件 | 最低版本 | 检查命令 | 用途 |
|------|---------|---------|------|
| **Docker** + Docker Compose | 20.10+ | `docker --version` | 运行 MySQL + Redis |
| **Python** | 3.10 ~ 3.14 | `python3 --version` | 后端服务 |
| **Node.js** | 18+ | `node --version` | 前端构建 |
| **npm** | 9+ | `npm --version` | 前端包管理 |

### macOS 快速安装缺失依赖

```bash
# 安装 Homebrew（如果没有）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装 Docker
brew install --cask docker

# 安装 Python
brew install python@3.12

# 安装 Node.js
brew install node@20
```

### Linux (Ubuntu/Debian) 快速安装

```bash
# Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker

# Python + Node
sudo apt update
sudo apt install python3 python3-pip python3-venv nodejs npm -y
```

### Windows

从 [docker.com](https://www.docker.com/products/docker-desktop/) 下载安装 Docker Desktop，从 [python.org](https://www.python.org/downloads/) 和 [nodejs.org](https://nodejs.org/) 分别安装 Python 和 Node.js。

---

## 2. 安装 Docker 并启动数据库

### 2.1 启动 Docker

- **macOS/Windows**：启动 Docker Desktop 应用，等待状态栏图标显示「运行中」
- **Linux**：`sudo systemctl start docker`

### 2.2 启动 MySQL 和 Redis

在项目根目录执行：

```bash
cd deepseek
docker compose up -d
```

> 首次执行会自动拉取 `mysql:8.0` 和 `redis:7-alpine` 镜像（约 500MB），需要几分钟。

### 2.3 验证数据库

```bash
docker ps
```

应该看到两个容器在运行：

```
CONTAINER ID   IMAGE            STATUS         PORTS
xxxxxxxxxxx    mysql:8.0        Up (healthy)   0.0.0.0:3306->3306/tcp
xxxxxxxxxxx    redis:7-alpine   Up (healthy)   0.0.0.0:6379->6379/tcp
```

`STATUS` 列显示 `(healthy)` 表示启动成功。

### 2.4 docker-compose.yml 说明

项目根目录的 `docker-compose.yml` 定义了三个容器，**全部需要启动**：

```yaml
# 简化说明：
mysql  → 端口 3307，用户 root，密码 123456，数据库 deepseek
redis  → 端口 6379，密码 123456，持久化开启 (AOF)
chroma → 端口 8001，向量数据库（chromadb/chroma），数据持久化到 chroma_data 卷
```

**如果不想用 Docker**，也可以自行安装 MySQL 8.0 和 Redis 7，然后修改 `.env` 中的连接地址。

---

## 3. 安装 Python 依赖

### 3.1 创建虚拟环境

```bash
cd deepseek
python3 -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate    # Windows PowerShell
```

终端提示符前出现 `(.venv)` 表示激活成功。

### 3.2 安装依赖

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

> 使用清华镜像加速下载。如果不在国内可以去掉 `-i https://pypi.tuna.tsinghua.edu.cn/simple`。

### 3.3 依赖说明

| 包 | 用途 |
|----|------|
| `fastapi` + `uvicorn` | Web 框架 + ASGI 服务器 |
| `langchain` + `langgraph` | 智能体框架 + 状态图编排 |
| `langchain-openai` | DeepSeek API 客户端（OpenAI 兼容） |
| `pymysql` + `redis` | MySQL + Redis 驱动 |
| `numpy` | 向量计算 |
| `httpx` + `aiohttp` | HTTP 客户端 |
| `duckduckgo-search` | 免费网络搜索 |
| `python-dotenv` | 环境变量加载 |
| `sentence-transformers` | 文本嵌入向量（可选，Python 3.14 自动降级） |

---

## 4. 配置环境变量

### 4.1 创建配置文件

```bash
cp .env.example .env
```

### 4.2 编辑 .env

打开 `.env`，至少修改以下两项：

```env
# 必填：你的 DeepSeek API 密钥
LLM_API_KEY=sk-xxxxxxxxxxxxxxxx

# 必填：模型名称（推荐 deepseek-v4-pro，也支持 deepseek-chat）
LLM_MODEL=deepseek-v4-pro
```

### 4.3 获取 API 密钥

1. 访问 [platform.deepseek.com](https://platform.deepseek.com)
2. 注册/登录账号
3. 进入「API Keys」页面，点击「创建 API Key」
4. 复制密钥填入 `.env`

> `.env` 已在 `.gitignore` 中排除，不会被提交到 GitHub。

### 4.4 完整配置项

```env
# ── LLM ──
LLM_API_KEY=sk-xxxxxxxx          # API 密钥（必填）
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-v4-pro        # 模型名
LLM_TEMPERATURE=0.7              # 创造性 (0~1)
LLM_MAX_TOKENS=4096              # 最大输出长度

# ── MySQL ──
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=deepseek
MYSQL_PASSWORD=deepseek123       # 与 docker-compose.yml 一致
MYSQL_DATABASE=deepseek

# ── Redis ──
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=deepseek-redis-2024
REDIS_DB=0

# ── 向量库 ──
CHROMA_HOST=localhost
CHROMA_PORT=8001

# ── 智能体 ──
MAX_AGENT_ITERATIONS=10          # ReAct 最大循环次数
MEMORY_TTL_SECONDS=86400         # 记忆过期 (24小时)
MAX_CONTEXT_MESSAGES=20          # 最大上下文消息数
```

---

## 5. 加载知识库

项目附带了 5 篇中文知识库文档（`knowledge_base/` 目录），需要加载到向量库才能被 RAG 检索。

```bash
# 确保仍在项目根目录，虚拟环境已激活
python -m src.rag.document_loader
```

等待输出：
```
加载: company_intro.md → 10 块 [company]
加载: product_manual.txt → 2 块 [product]
加载: faq.md → 5 块 [company]
加载: policies.txt → 2 块 [company]
加载: technical_specs.md → 14 块 [technical]
总计加载 5 个文档
```

### 自定义知识库

- 将你的 `.txt` 或 `.md` 文件放入 `knowledge_base/` 目录
- 重新执行 `python -m src.rag.document_loader` 即可

---

## 6. 启动后端服务

```bash
# 确保在项目根目录，虚拟环境已激活
python -m src.main
```

看到以下输出表示启动成功：

```
╔══════════════════════════════════════════════════════╗
║       DeepSeek 多智能体系统 v1.0                    ║
║  多智能体协作 | Agentic RAG | ReAct | MCP          ║
╚══════════════════════════════════════════════════════╝

  API 服务：http://0.0.0.0:8000
  MCP 服务：http://0.0.0.0:9000
  MySQL：localhost:3306
  Redis：localhost:6379
  大模型：deepseek-v4-pro
```

- API 文档（Swagger）：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

### 后台运行

```bash
nohup python -m src.main > /tmp/backend.log 2>&1 &
```

查看日志：`tail -f /tmp/backend.log`

---

## 7. 启动前端服务

### 7.1 安装依赖并启动

```bash
cd frontend
npm install
npm run dev
```

输出示例：
```
  VITE v5.x  ready in 500ms
  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

浏览器打开 http://localhost:5173

> Vite 自动将 `/api` 请求代理到后端 `http://localhost:8000`，无需额外配置。

### 7.2 构建生产版本（可选）

```bash
npm run build
# 产物在 frontend/dist/，可部署到 Nginx、Vercel 等
```

---

## 8. 验证系统

### 8.1 后端健康检查

```bash
curl http://localhost:8000/health
```

预期输出：
```json
{"mysql": "正常", "redis": "正常", "chroma": "正常"}
```

### 8.2 测试聊天

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "公司提供哪些产品？", "stream": false}'
```

预期返回包含 `"message"` 和 `"conversation_id"` 的 JSON。

### 8.3 前端测试

浏览器打开 http://localhost:5173，在输入框输入问题并发送，应该看到：
1. 状态提示「正在分析...」→「正在检索知识库...」
2. AI 回复逐字流式出现
3. 侧边栏显示对话列表

---

## 9. 常见问题排查

### Q1: `pip install` 报 SSL 错误

**现象**：`SSLError: [SSL: UNEXPECTED_EOF_WHILE_READING]`

**解决**：使用国内镜像
```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
```

### Q2: `ModuleNotFoundError: No module named 'xxx'`

**解决**：确保虚拟环境已激活，依赖安装完整
```bash
source .venv/bin/activate
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### Q3: MySQL 连接失败

**检查容器**：
```bash
docker ps | grep mysql
```

如果没有 running 状态，重新启动：
```bash
docker compose down
docker compose up -d
```

**检查端口占用**：
```bash
lsof -i :3306
```

### Q4: `Access denied for user 'deepseek'@'localhost'`

Docker 容器可能未正确初始化。修复：
```bash
docker compose down -v     # 删除旧数据卷
docker compose up -d       # 重新创建（init.sql 自动执行）
```

### Q5: Redis 连接失败

检查 Redis 容器：
```bash
docker ps | grep redis
redis-cli -a deepseek-redis-2024 ping   # 预期 PONG
```

### Q6: 后端启动后前端显示空白

1. 确保后端正在运行：`curl http://localhost:8000/health`
2. 确保前端 Vite 代理配置正确（`vite.config.js` 中的 proxy 指向 8000）
3. 打开浏览器开发者工具 → Network 标签，检查 API 请求状态

### Q7: `sentence-transformers` 安装失败

Python 3.14 暂无 torch wheels。系统已内置 N-gram 嵌入器作为自动降级方案，不影响使用。终端会提示 `使用简易嵌入器`。

### Q8: 知识库检索不到内容

先确认文档已加载：
```bash
python -m src.rag.document_loader
```

检查向量数据文件存在：
```bash
ls -la vector_data/vectors.pkl
```

### Q9: API 返回 401 错误

`.env` 中 `LLM_API_KEY` 未填或无效。确认密钥格式为 `sk-` 开头。

### Q10: 端口已被占用

```bash
# 查看占用端口的进程
lsof -i :8000
lsof -i :5173

# 杀掉进程
kill -9 <PID>

# 或者修改端口（编辑 .env 的 API_PORT 和 vite.config.js 的 server.port）
```

### Q11: 前后端都启动成功，但聊天没反应

打开浏览器开发者工具 (F12) → Console 和 Network 标签：
- 检查是否有红色报错
- 查找 `/api/chat` 请求，检查状态码
- 如果是 CORS 错误，确认后端已配置 `allow_origins=["*"]`

---

## 一键启动脚本

创建 `start.sh`：

```bash
#!/bin/bash
set -e

echo "🚀 启动 DeepSeek 多智能体系统..."

# 1. 数据库
echo "📦 启动 MySQL + Redis..."
docker compose up -d
sleep 3

# 2. 后端
echo "🐍 启动后端..."
source .venv/bin/activate 2>/dev/null || python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -q -i https://pypi.tuna.tsinghua.edu.cn/simple
python -m src.main &
BACKEND_PID=$!
sleep 3

# 3. 前端
echo "🎨 启动前端..."
cd frontend
npm install --silent
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ 系统启动完成！"
echo "   前端: http://localhost:5173"
echo "   后端: http://localhost:8000"
echo "   API文档: http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止所有服务"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; docker compose down" EXIT
wait
```

```bash
chmod +x start.sh
./start.sh
```
