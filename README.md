# DeepSeek · 知识与研究工作台

面向个人资料研究的完整工作台：导入资料、核对引用、比较文档、制作报告，并把回答编辑为可保存和导出的 Markdown 成果。

## 已实现的流程

- **查阅资料**：按指定文档或全部知识库检索；回答中的引用编号可点击，查看对应片段和原文件。
- **对比文档**：选择至少两份资料，检索会兼顾每份选定资料，便于比较差异与信息缺口。
- **制作报告**：生成 Markdown 报告，在右侧编辑、预览、保存；可从成果页再次打开，或下载 Markdown。
- **资料管理**：导入 TXT、Markdown、文字版 PDF、DOCX；限制文件大小为 20 MB，显示索引状态，支持原文预览与重新索引。
- **任务管理**：搜索、切换、重命名、删除历史任务；复制、重试、停止生成；已收到的部分回答、来源与工具结果会保存。
- **阅读体验**：桌面工作区、手机抽屉导航、深浅主题、代码高亮、表格横向滚动；向上阅读时不强制滚动到底部。
- **执行能力**：异步多轮工具调用，结果交回模型继续处理；联网默认关闭，用户可显式打开。代码执行默认关闭，需要 Docker 隔离环境。

## 执行与存储

前端使用 Vue 3、Pinia、Vite。FastAPI 使用 LangGraph 的“检索 → 执行与回答”工作流，流式和非流式 API 共享同一个执行循环。模型可组合检索、计算、单位转换与联网工具；工具参数按 LangChain 的流式消息聚合解析，工具结果作为 ToolMessage 交给模型。

任务事件包括 session、status、sources、tool、reset、token、done、error。session 在生成前返回对话和消息 ID，reset 清除工具执行前的过渡文本，done 在回答保存后发送。错误和停止有独立状态。

MySQL 保存对话、回答、来源、工具结果与编辑成果，沿用 init.sql 中已有的 JSON metadata 字段，不需要新增表。Redis 是可选缓存；默认关闭，不影响上下文读取。Chroma 保存文档分块与向量。重建索引复用文档 ID，避免重复添加资料。

## 本地运行

需要 Python 3.11+（本机已在 3.13 验证）、Node.js 22.12+ 或 24+、MySQL 8。首次运行先用 init.sql 创建表。

在项目根目录的 PowerShell 中：

~~~powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
~~~

首次配置可复制 .env.example 到 .env；已有 .env 时保留现有配置。LLM_BASE_URL、LLM_MODEL 和 MySQL 连接信息仍可在 .env 中设置。

**模型密钥只读取环境变量 LLM_API_KEY**，项目会忽略 .env 中的同名项。Windows 下打开“编辑账户的环境变量”，在“用户变量”中添加 LLM_API_KEY，将值设为自己的 API 密钥。仅供当前账户运行时，使用用户变量即可，无需管理员权限。密钥只在后端使用，不进入前端构建。

保存后重新打开启动终端（通过 Codex 启动时需退出并重新打开 Codex），再启动或重启后端。已运行的进程不会自动继承后来修改的 Windows 环境变量。确认环境变量已设置后，删除 .env 中的旧 LLM_API_KEY 行，避免项目文件保留密钥。未设置密钥时，资料管理仍可使用，模型任务会提示设置环境变量。

构建前端：

~~~powershell
cd frontend
npm ci
npm run build
cd ..
~~~

启动：

~~~powershell
.venv/Scripts/python.exe -m uvicorn src.main:app --host 127.0.0.1 --port 8000
~~~

打开 http://127.0.0.1:8000 即可使用。后端自动服务 frontend/dist，无需另开前端服务。API 文档在 /docs。

开发时可单独运行 frontend 的 npm run dev；/api 和 /health 默认代理到 127.0.0.1:8000。后端端口不同可设置 API_PROXY_TARGET，例如 http://127.0.0.1:8002。

如果页面能打开，但历史记录和发送消息同时失败，先确认后端进程仍在运行。前端 5173 端口负责页面，8000 端口负责接口；仅启动前端不能完成对话。访问 http://127.0.0.1:8000/api/health 检查 MySQL 和 Chroma，恢复后刷新页面；历史失败消息不会自动变为成功，需要重试。页面现在会显示 HTTP 状态或连接原因，便于区分代理、存储和模型错误。

## 检索模型与代码执行

EMBEDDING_BACKEND=auto 优先使用项目 model_cache 中已缓存的语义模型，未缓存时使用离线字符特征向量，结合中文词组相关性排序，不自动下载模型。离线特征检索适合起步，语义匹配质量取决于实际资料和查询。

需要语义模型时，安装 requirements-embeddings.txt，设置 EMBEDDING_BACKEND=sentence_transformers 和 EMBEDDING_MODEL。更换嵌入模型后必须重新索引；向量维度改变时使用新的 CHROMA_COLLECTION，再导入资料。客户端与独立 Chroma 服务应使用兼容版本，本机验证版本为 1.4.1。

扫描 PDF 需要先 OCR。本轮解析只提取文字、DOCX 段落与表格，原始页面格式不会保留在检索片段里。

若需要执行 Python，由部署者准备 CODE_CONTAINER_IMAGE，并设置 ENABLE_CODE_EXECUTION=true。容器使用无网络、只读根文件系统、无挂载项目文件、非 root 用户、CPU/内存/PID 限制和超时。默认不会下载镜像。

## 验证

后端单元测试和依赖检查：

~~~powershell
.venv/Scripts/python.exe -m unittest discover -s tests -v
.venv/Scripts/python.exe -m pip check
~~~

前端：

~~~powershell
cd frontend
npm test
npm run build
npm run test:browser
~~~

浏览器测试使用独立接口样例，不调用真实模型。首次使用 Playwright 可运行 npx playwright install chromium；已安装 Edge 的 Windows 可设置 BROWSER_CHANNEL=msedge。WORKBENCH_URL 默认 http://127.0.0.1:8000。截图输出到 outputs/workbench。

真实 MySQL 与 Chroma 的集成验收（模型使用样例替身，只创建并删除自己的测试对话）：

~~~powershell
$env:WORKBENCH_STORAGE_TESTS='1'
.venv/Scripts/python.exe -m unittest discover -s tests -v
~~~

## 当前边界

这是个人工作空间，按单个后端进程运行。运行中的 HTTP 流可以取消，已输出内容可恢复查看；进程重启或断线后通过重试重新执行，不会自动续接模型生成。尚未提供团队登录、租户隔离、后台任务队列和跨进程互斥，公开部署前需要增加访问控制。

编辑成果保存为 Markdown，导出也是 Markdown。工具执行记录、检索片段和实际引用用于核对结果，并不表示结论已通过人工审核。互联网工具使用公开搜索服务，其可用性取决于网络。

tutorial/ 中保留了原来的多智能体教学示例；当前工作台入口以 src/main.py 和 src/graphs/supervisor_graph.py 为准。
