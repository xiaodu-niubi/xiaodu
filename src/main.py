"""DeepSeek 多智能体系统 - FastAPI 入口"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
    print(f"  Chroma：{settings.chroma_host}:{settings.chroma_port}")
    print(f"  大模型：{settings.llm_model}")

    # 自动发现并加载所有工具模块
    import importlib
    import pkgutil
    import src.tools as tools_pkg

    for _, name, _ in pkgutil.iter_modules(tools_pkg.__path__):
        try:
            importlib.import_module(f"src.tools.{name}")
        except Exception as e:
            print(f"  警告：工具 {name} 加载失败：{e}")

    yield

    print("\n  正在关闭...\n")


app = FastAPI(
    title="DeepSeek 多智能体系统",
    description="具备 Agentic RAG、ReAct、函数调用和 MCP 的智能多智能体系统",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 中间件 - 开发环境允许所有来源
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat_router)
app.include_router(conversation_router)
app.include_router(knowledge_router)

# 简易 IP 限流中间件
from collections import defaultdict
import time
_rate_records: dict[str, list] = defaultdict(list)
_RATE_LIMIT = 60
_RATE_WINDOW = 60


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    _rate_records[ip] = [t for t in _rate_records[ip] if now - t < _RATE_WINDOW]
    if len(_rate_records[ip]) >= _RATE_LIMIT:
        return JSONResponse(status_code=429, content={"detail": "请求过于频繁，请稍后再试"})
    _rate_records[ip].append(now)
    return await call_next(request)


@app.get("/")
async def root():
    """系统信息端点"""
    return {
        "name": "DeepSeek 多智能体系统",
        "version": "1.0.0",
        "agents": ["orchestrator（编排）", "rag（知识检索）", "tool（工具执行）", "web（网络搜索）", "memory（记忆管理）"],
        "capabilities": [
            "多智能体协作",
            "Agentic RAG（动态知识检索）",
            "ReAct 推理模式",
            "函数调用",
            "MCP 协议",
            "SSE 流式传输",
            "Redis 记忆存储",
            "MySQL 持久化",
        ],
        "docs": "/docs",
    }


@app.get("/health")
@app.get("/api/health")
async def health():
    """健康检查端点"""
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

    # 检查 Chroma
    try:
        from src.database.chroma_client import chroma_client
        chroma_client.collection_stats()
        checks["chroma"] = "正常"
    except Exception as e:
        checks["chroma"] = f"异常：{e}"

    return checks


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
