# DeepSeek 知识与研究工作台

面向个人资料研究的完整工作台：导入资料、核对引用、比较文档、制作报告，并把回答编辑为可保存和导出的 Markdown 成果。

## 目录

- [功能特性](#功能特性)
- [技术架构](#技术架构)
- [快速开始](#快速开始)
- [检索模型与代码执行](#检索模型与代码执行)
- [测试与验证](#测试与验证)
- [当前边界](#当前边界)

---

## 功能特性

| 功能 | 说明 |
|------|------|
| 查阅资料 | 按指定文档或全部知识库检索，引用编号可点击查看原文片段 |
| 对比文档 | 选择多份资料同时检索，便于比较差异与信息缺口 |
| 制作报告 | 生成 Markdown 报告，支持右侧编辑、预览、保存与下载 |
| 资料管理 | 导入 TXT / Markdown / PDF（文字版）/ DOCX，最大 20 MB |
| 任务管理 | 搜索、切换、重命名、删除历史任务；支持复制、重试、停止生成 |
| 执行能力 | 异步多轮工具调用；联网与代码执行默认关闭，可按需开启 |

---

## 技术架构

- **前端**：Vue 3 + Pinia + Vite
- **后端**：FastAPI + LangGraph（检索 → 执行 → 回答工作流）
- **存储**：MySQL（对话/成果）、Redis（可选缓存）、Chroma（向量）
- **流式**：SSE 事件流（session / status / sources / tool / token / done / error）

---

## 快速开始

### 环境要求

- Python 3.11+（已在 3.13 验证）
- Node.js 22.12+ 或 24+
- MySQL 8

### 1. 克隆并配置环境变量

```powershell
# 复制配置模板
cp .env.example .env
```

编辑 `.env`，填入数据库连接信息和模型配置。

> **模型密钥安全提示**：`LLM_API_KEY` 建议设置为系统环境变量而非写入 `.env`。
> Windows 中打开「编辑账户的环境变量」→「用户变量」→ 添加 `LLM_API_KEY`。
> 设置后重新打开终端，删除 `.env` 中的旧密钥行。

### 2. 初始化数据库

```sql
-- 在 MySQL 中执行
source init.sql
```

### 3. 安装后端依赖

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 4. 构建前端

```powershell
cd frontend
npm ci
npm run build
cd ..
```

### 5. 启动

```powershell
.venv\Scripts\python.exe -m uvicorn src.main:app --host 127.0.0.1 --port 8000
```

打开 http://127.0.0.1:8000 即可使用。API 文档在 `/docs`。

### 开发模式

前端单独运行（代理到后端 8000 端口）：

```powershell
cd frontend
npm run dev
```

如后端端口不同，设置 `API_PROXY_TARGET`，例如 `http://127.0.0.1:8002`。

### 常见问题

- **页面能打开但消息发送失败**：确认后端进程仍在运行，访问 http://127.0.0.1:8000/api/health 检查 MySQL 和 Chroma 状态。
- **环境变量未生效**：保存后需重新打开终端，已运行进程不会自动继承新变量。

---

## 检索模型与代码执行

### 嵌入模型

`EMBEDDING_BACKEND=auto`（默认）优先使用 `model_cache/` 中已缓存的语义模型，未缓存时使用离线字符特征向量，不自动下载模型。

需要语义检索时：

```powershell
pip install -r requirements-embeddings.txt
```

并在 `.env` 中设置：

```
EMBEDDING_BACKEND=sentence_transformers
EMBEDDING_MODEL=你的模型名
```

> 更换嵌入模型后必须重新索引；向量维度改变时需使用新的 `CHROMA_COLLECTION`。

### 代码执行

需要部署者准备隔离容器镜像，并在 `.env` 中设置：

```
CODE_CONTAINER_IMAGE=你的镜像名
ENABLE_CODE_EXECUTION=true
```

容器限制：无网络、只读根文件系统、非 root 用户、CPU/内存/PID 限制与超时。

---

## 测试与验证

### 后端

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe -m pip check
```

### 前端

```powershell
cd frontend
npm test
npm run build
npm run test:browser
```

> 首次使用 Playwright 运行 `npx playwright install chromium`；Windows 已安装 Edge 可设置 `BROWSER_CHANNEL=msedge`。截图输出到 `outputs/workbench/`。

### 集成测试（需真实 MySQL 与 Chroma）

```powershell
$env:WORKBENCH_STORAGE_TESTS='1'
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

模型使用样例替身，只创建并删除自己的测试对话。

---

## 当前边界

- 单进程运行，不支持团队登录、租户隔离、后台任务队列和跨进程互斥，**公开部署前需增加访问控制**。
- 进程重启或断线后需手动重试，不会自动续接模型生成。
- 成果仅导出为 Markdown，不保留原始页面格式。
- 互联网工具依赖公开搜索服务，可用性取决于网络。
- PDF 扫描件需先 OCR，当前只提取文字层内容。

---

`tutorial/` 中保留了多智能体教学示例，当前工作台入口以 `src/main.py` 和 `src/graphs/supervisor_graph.py` 为准。
