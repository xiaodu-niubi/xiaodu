# 搭建与启动指南

从零搭建 DeepSeek 多智能体系统的完整流程。

---

## 1. 环境要求

| 软件 | 最低版本 | 检查命令 |
|------|---------|---------|
| Docker + Docker Compose | 20.10+ | `docker --version` |
| Python | 3.10+ | `python3 --version` |
| Node.js | 18+ | `node --version` |

### 安装依赖

**macOS**
```bash
brew install --cask docker
brew install python@3.12 node@20
```

**Linux (Ubuntu/Debian)**
```bash
curl -fsSL https://get.docker.com | sudo sh
sudo apt install python3 python3-pip python3-venv nodejs npm -y
```

**Windows** — 从 [docker.com](https://www.docker.com/products/docker-desktop/) 安装 Docker Desktop，从 [python.org](https://www.python.org/downloads/) 和 [nodejs.org](https://nodejs.org/) 安装 Python 和 Node.js。

---

## 2. 启动 MySQL 和 Redis

```bash
docker compose up -d
```

验证：
```bash
docker ps
# 应该看到 mysql:8.0 和 redis:7-alpine 两个容器，STATUS 显示 (healthy)
```

> 首次执行会拉取镜像约 500MB，需要几分钟。数据库 schema 由 `init.sql` 自动初始化。

---

## 3. 安装 Python 依赖

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

> 国内用户可加镜像加速：`pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`

---

## 4. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，至少填写 `LLM_API_KEY`。

获取 API Key：[platform.deepseek.com](https://platform.deepseek.com) → API Keys → 创建。

> `.env` 已在 `.gitignore` 中排除，不会被提交到 GitHub。

---

## 5. 加载知识库

```bash
python -m src.rag.document_loader
```

看到文档列表输出即加载成功。自定义知识库：将 `.md` / `.txt` 文件放入 `knowledge_base/`，重新执行即可。

---

## 6. 启动服务

```bash
# 终端 1：后端
python -m src.main

# 终端 2：前端
cd frontend
npm install
npm run dev
```

- 前端: http://localhost:5173
- API 文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

---

## 7. 常见问题排查

### MySQL 连接失败

```bash
docker ps | grep mysql          # 检查容器是否运行
docker compose down -v && docker compose up -d  # 重置数据卷
```

### Redis 连接失败

```bash
docker ps | grep redis
docker compose restart redis
```

### `ModuleNotFoundError` 缺少模块

确保虚拟环境已激活（终端前有 `(.venv)` 标识），执行：
```bash
pip install -r requirements.txt
```

### `pip install` SSL 错误

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
```

### 端口被占用

```bash
lsof -i :8000   # 查看占用 8000 端口的进程
lsof -i :5173
kill -9 <PID>   # 或修改 .env 中的 API_PORT、vite.config.js 中的 server.port
```

### 前端空白/跨域错误

1. 确认后端运行中：`curl http://localhost:8000/health`
2. 确认前端 Vite 代理指向 `http://localhost:8000`（见 `vite.config.js`）
3. 打开浏览器 DevTools → Network，检查 API 请求状态

### `sentence-transformers` 安装失败

Python 3.14 暂无 torch wheels，系统内置 N-gram 嵌入器自动降级，不影响使用。

### API 返回 401 错误

`.env` 中 `LLM_API_KEY` 未填或无效，确认密钥格式以 `sk-` 开头。

### 知识库检索不到内容

```bash
python -m src.rag.document_loader   # 重新加载
ls -la vector_data/vectors.pkl      # 确认向量数据存在
```

---

## 一键启动脚本

```bash
#!/bin/bash
set -e

echo "启动 DeepSeek 多智能体系统..."

docker compose up -d
sleep 3

source .venv/bin/activate 2>/dev/null || python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -q
python -m src.main &
BACKEND_PID=$!

cd frontend
npm install --silent
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "  前端: http://localhost:5173"
echo "  后端: http://localhost:8000"
echo "  API文档: http://localhost:8000/docs"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; docker compose down" EXIT
wait
```

保存为 `start.sh`，运行 `chmod +x start.sh && ./start.sh`。
