# 第16课：API层 —— 用FastAPI暴露HTTP接口

> 🎯 **本课目标**：写FastAPI路由，让外部能通过HTTP请求访问我们的智能体系统。

---

## 16.1 FastAPI快速入门

FastAPI是一个Python Web框架，它的特点：
- 快（和Node.js/Go一个级别）
- 自动生成API文档（Swagger）
- 用Python类型注解自动校验请求参数

### 最简单的FastAPI例子：

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/hello")
def hello():
    return {"message": "Hello World"}
```

访问 `http://localhost:8000/hello` → 返回 `{"message": "Hello World"}`

---

## 16.2 我们的API有哪些接口？

| 方法 | 路径 | 功能 |
|------|------|------|
| `GET` | `/` | 系统信息 |
| `GET` | `/health` | 健康检查 |
| `POST` | `/api/chat` | 核心聊天接口（支持流式SSE） |
| `GET` | `/api/conversations` | 对话列表 |
| `POST` | `/api/conversations` | 新建对话 |
| `GET` | `/api/conversations/{id}` | 对话详情+消息 |
| `DELETE` | `/api/conversations/{id}` | 删除对话 |
| `PUT` | `/api/conversations/{id}` | 更新对话标题 |
| `GET` | `/api/knowledge/list` | 知识库文档列表 |
| `POST` | `/api/knowledge/upload` | 上传文档 |
| `POST` | `/api/knowledge/reload` | 重新加载知识库 |
| `GET` | `/api/tools` | 可用工具列表 |

---

## 16.3 写代码：`src/api/chat_router.py`（核心聊天接口）

```python
"""聊天 API 路由 - 核心对话端点，支持 SSE 流式传输"""
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from src.models.schemas import ChatRequest, ChatResponse
from src.graphs.supervisor_graph import supervisor_graph
from src.database.mysql_client import mysql_client
from src.memory.conversation import conversation_memory

router = APIRouter(prefix="/api", tags=["聊天"])


@router.post("/chat")
async def chat(request: ChatRequest):
    """主聊天端点，支持流式和非流式响应
    
    请求体：
    {
        "message": "公司有哪些产品？",
        "conversation_id": null,   // null表示新建对话
        "stream": true             // true=流式SSE, false=等全部生成完再返回
    }
    """
    # ── 第1步：获取或创建对话 ──
    conv_id = request.conversation_id
    if not conv_id:
        # 新对话：MySQL中创建记录
        conv = mysql_client.create_conversation()
        conv_id = conv["id"]
        session_id = conv["session_id"]
    else:
        # 已有对话：从MySQL读取
        conv = mysql_client.get_conversation(conv_id)
        if not conv:
            raise HTTPException(status_code=404, detail="对话未找到")
        session_id = conv["session_id"]

    # ── 第2步：保存用户消息 ──
    mysql_client.save_message(conv_id, "user", request.message)     # 持久化到MySQL
    conversation_memory.add_turn(session_id, "user", request.message)  # 缓存到Redis

    # ── 第3步：获取对话历史（从Redis）──
    history = conversation_memory.get_history(session_id, 20)

    # ── 第4步：处理请求 ──
    if request.stream:
        # ═══ 流式响应（SSE） ═══
        async def event_generator():
            """异步生成器，逐块产出SSE事件"""
            response_text = ""

            # 调用编排图的流式处理方法
            async for chunk in supervisor_graph.stream_process(
                user_message=request.message,
                session_id=session_id,
                conversation_id=conv_id,
                history=history,
            ):
                # 收集完整回复
                if chunk['type'] == 'token':
                    response_text += chunk['content']

                # SSE格式：event: 类型\ndata: JSON数据\n\n
                yield f"event: {chunk['type']}\ndata: {json.dumps(chunk, ensure_ascii=False)}\n\n"

            # ── 第5步：保存助手回复 ──
            if response_text.strip():
                mysql_client.save_message(conv_id, "assistant", response_text)
                conversation_memory.add_turn(session_id, "assistant", response_text)

                # 自动生成标题（取用户消息的前100字）
                if conv.get("title") == "新对话":
                    title = request.message[:100]
                    if len(request.message) > 100:
                        title += "..."
                    mysql_client.update_conversation_title(conv_id, title)

            # 发送完成事件
            yield f"event: done\ndata: {json.dumps({'conversation_id': conv_id})}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # 禁用Nginx缓冲
            },
        )
    else:
        # ═══ 非流式响应 ═══
        result = supervisor_graph.process(
            user_message=request.message,
            session_id=session_id,
            conversation_id=conv_id,
            history=history,
        )

        response_text = result.get("response", "")
        tool_calls_data = result.get("tool_calls", [])

        # 保存回复
        mysql_client.save_message(
            conv_id, "assistant", response_text,
            tool_calls=tool_calls_data if tool_calls_data else None,
        )
        conversation_memory.add_turn(session_id, "assistant", response_text)

        # 自动生成标题
        if conv.get("title") == "新对话":
            title = request.message[:100]
            if len(request.message) > 100:
                title += "..."
            mysql_client.update_conversation_title(conv_id, title)

        return ChatResponse(
            conversation_id=conv_id,
            session_id=session_id,
            message=response_text,
            tool_calls=tool_calls_data,
        )
```

---

## 16.4 写代码：`src/api/conversation_router.py`

```python
"""对话管理 API 路由"""
from fastapi import APIRouter, HTTPException

from src.models.schemas import ConversationCreate, ConversationUpdate
from src.database.mysql_client import mysql_client

router = APIRouter(prefix="/api/conversations", tags=["对话"])


@router.get("")
async def list_conversations(limit: int = 50, offset: int = 0):
    """获取对话列表"""
    conversations = mysql_client.list_conversations(limit, offset)
    return {"conversations": conversations, "total": len(conversations)}


@router.post("")
async def create_conversation(body: ConversationCreate):
    """创建新对话"""
    conv = mysql_client.create_conversation(title=body.title)
    return conv


@router.get("/{conv_id}")
async def get_conversation(conv_id: str):
    """获取对话详情（含消息列表）"""
    conv = mysql_client.get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="对话未找到")
    messages = mysql_client.get_messages(conv_id)
    conv["messages"] = messages
    return conv


@router.delete("/{conv_id}")
async def delete_conversation(conv_id: str):
    """删除对话"""
    conv = mysql_client.get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="对话未找到")
    mysql_client.delete_conversation(conv_id)
    from src.memory.conversation import conversation_memory
    conversation_memory.clear(conv["session_id"])
    return {"status": "已删除"}


@router.put("/{conv_id}")
async def update_conversation(conv_id: str, body: ConversationUpdate):
    """更新对话标题"""
    conv = mysql_client.get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="对话未找到")
    mysql_client.update_conversation_title(conv_id, body.title)
    return {"status": "已更新"}
```

---

## 16.5 写代码：`src/api/knowledge_router.py`

```python
"""知识库管理 API 路由"""
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException

from src.database.mysql_client import mysql_client
from src.rag.document_loader import document_loader
from src.tools.tool_registry import tool_registry
from src.mcp.mcp_server import mcp_server

router = APIRouter(prefix="/api", tags=["知识库"])


@router.get("/knowledge/list")
async def list_knowledge():
    """列出所有知识库文档"""
    docs = mysql_client.list_documents()
    return {"documents": docs}


@router.post("/knowledge/upload")
async def upload_knowledge(file: UploadFile = File(...)):
    """上传文档到知识库"""
    if not file.filename.endswith((".txt", ".md")):
        raise HTTPException(status_code=400, detail="仅支持 .txt 和 .md 文件")

    # 保存到knowledge_base目录
    kb_path = Path(__file__).parent.parent.parent / "knowledge_base"
    kb_path.mkdir(exist_ok=True)

    file_path = kb_path / file.filename
    content = await file.read()
    file_path.write_bytes(content)

    # 加载到向量数据库
    result = document_loader.load_document(file_path)

    return {
        "filename": file.filename,
        "chunks": result["chunks"],
        "status": result["status"],
    }


@router.post("/knowledge/reload")
async def reload_knowledge():
    """重新加载所有知识库文档"""
    results = document_loader.load_all()
    return {"loaded": len(results), "documents": results}


@router.get("/tools")
async def list_tools():
    """列出所有可用工具及其定义"""
    definitions = tool_registry.get_definitions()
    names = tool_registry.list_tool_names()
    return {"tools": [{"name": n, "description": d["function"]["description"]}
                      for n, d in zip(names, definitions)]}
```

---

## 16.6 写代码：`src/main.py`（程序入口）

```python
"""DeepSeek 多智能体系统 - FastAPI 入口"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.api.chat_router import router as chat_router
from src.api.conversation_router import router as conversation_router
from src.api.knowledge_router import router as knowledge_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动和关闭事件"""
    print("""
    ╔══════════════════════════════════════════════════════╗
    ║       DeepSeek 多智能体系统 v1.0                    ║
    ║  多智能体协作 | Agentic RAG | ReAct | MCP          ║
    ╚══════════════════════════════════════════════════════╝
    """)
    print(f"  API 服务：http://{settings.api_host}:{settings.api_port}")
    print(f"  MCP 服务：http://{settings.api_host}:{settings.mcp_server_port}")
    print(f"  MySQL：{settings.mysql_host}:{settings.mysql_port}")
    print(f"  Redis：{settings.redis_host}:{settings.redis_port}")
    print(f"  大模型：{settings.llm_model}")

    # 预加载工具（触发注册）
    try:
        from src.tools.builtin_tools import calculator  # noqa
        from src.tools.web_search import web_search  # noqa
        from src.tools.file_tools import read_file  # noqa
        from src.agents.rag_agent import knowledge_search  # noqa
    except Exception as e:
        print(f"  警告：部分工具加载失败：{e}")

    yield  # 这里是应用运行期间

    print("\n  正在关闭...\n")


# 创建FastAPI应用
app = FastAPI(
    title="DeepSeek 多智能体系统",
    description="具备 Agentic RAG、ReAct、函数调用和 MCP 的智能多智能体系统",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 中间件 - 允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat_router)
app.include_router(conversation_router)
app.include_router(knowledge_router)


@app.get("/")
async def root():
    """系统信息"""
    return {
        "name": "DeepSeek 多智能体系统",
        "version": "1.0.0",
        "agents": ["orchestrator", "rag", "tool", "web", "memory"],
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    """健康检查"""
    checks = {}

    # 检查 MySQL
    try:
        from src.database.mysql_client import mysql_client
        mysql_client.list_conversations(limit=1)
        checks["mysql"] = "正常"
    except Exception as e:
        checks["mysql"] = f"异常：{e}"

    # 检查 Redis
    try:
        from src.database.redis_client import redis_client
        redis_client.client.ping()
        checks["redis"] = "正常"
    except Exception as e:
        checks["redis"] = f"异常：{e}"

    # 检查向量库
    try:
        from src.database.chroma_client import chroma_client
        chroma_client.collection_stats()
        checks["chroma"] = "正常"
    except Exception as e:
        checks["chroma"] = f"异常：{e}"

    return checks


# 直接运行 python -m src.main 时启动服务
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,  # 开发模式：代码改了就自动重启
    )
```

---

## 16.7 SSE（Server-Sent Events）协议解释

SSE是一种服务器向浏览器**单向推送**数据的技术。我们用它来实现AI的打字机效果。

```
客户端发送：POST /api/chat {"message": "你好", "stream": true}
    ↓
服务器返回（持续不断，直到结束）：
event: status
data: {"type": "status", "content": "analyzing"}

event: node
data: {"type": "node", "content": "supervisor"}

event: token
data: {"type": "token", "content": "你"}

event: token
data: {"type": "token", "content": "好"}

event: token
data: {"type": "token", "content": "！"}

...

event: done
data: {"conversation_id": "abc-123"}
```

前端收到 `event: token` 就追加文字，实现打字机效果。

---

> **下一课**：[第17课：启动与测试](./17-启动与测试.md) —— 启动整套系统，用curl测试所有功能。

> ✅ **检验清单**：
> - [ ] `src/api/chat_router.py` 已创建
> - [ ] `src/api/conversation_router.py` 已创建
> - [ ] `src/api/knowledge_router.py` 已创建
> - [ ] `src/main.py` 已创建
> - [ ] 理解了SSE流式输出的原理
