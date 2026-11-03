"""DeepSeek 知识与研究工作台的 FastAPI 入口。"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import pymysql

from src.config import settings
from src.api.chat_router import router as chat_router
from src.api.conversation_router import router as conversation_router
from src.api.knowledge_router import router as knowledge_router
from src.api.artifact_router import router as artifact_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动和关闭事件"""
    print("\n  DeepSeek · 知识与研究工作台\n  查阅资料 | 对比文档 | 制作报告\n")
    print(f"  API 服务：http://{settings.api_host}:{settings.api_port}")
    print(f"  MySQL：{settings.mysql_host}:{settings.mysql_port}")
    print(f"  Redis：{settings.redis_host}:{settings.redis_port}" if settings.redis_enabled else "  Redis：未启用（可选缓存）")
    chroma_info = f"本地嵌入模式（{settings.chroma_persist_dir}）" if settings.chroma_mode == "local" else f"HTTP 服务（{settings.chroma_host}:{settings.chroma_port}）"
    print(f"  Chroma：{chroma_info}")
    print(f"  大模型：{settings.llm_model}")

    # 预加载工具
    try:
        from src.tools.builtin_tools import calculator  # noqa
        from src.tools.web_search import web_search  # noqa
        from src.tools.file_tools import read_file  # noqa
        from src.agents import knowledge_search  # noqa
    except Exception as e:
        print(f"  警告：部分工具加载失败：{e}")

    yield

    print("\n  正在关闭...\n")


app = FastAPI(
    title="DeepSeek · 知识与研究工作台",
    description="资料检索、文档对比、工具调用与 Markdown 成果管理的个人工作空间",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 中间件 - 开发环境允许所有来源
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat_router)
app.include_router(conversation_router)
app.include_router(knowledge_router)
app.include_router(artifact_router)

FRONTEND_DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"
if (FRONTEND_DIST / 'assets').is_dir():
    app.mount('/assets', StaticFiles(directory=str(FRONTEND_DIST / 'assets')), name='assets')


@app.exception_handler(pymysql.MySQLError)
async def database_error(request, exc):
    return JSONResponse(status_code=503, content={'detail': '历史与资料存储服务暂时不可用，请检查 MySQL 连接。'})


@app.get("/")
async def root():
    """系统信息端点"""
    if (FRONTEND_DIST / 'index.html').is_file():
        return FileResponse(FRONTEND_DIST / 'index.html', headers={'Cache-Control': 'no-cache'})
    return {
        "name": "DeepSeek · 知识与研究工作台",
        "version": "1.0.0",
        "modes": ["查阅资料", "对比文档", "制作报告", "自由对话"],
        "capabilities": [
            "指定资料检索与引用核对",
            "多轮工具调用",
            "SSE 流式传输",
            "MySQL 历史与成果持久化",
            "Markdown 编辑与导出",
        ],
        "docs": "/docs",
    }


@app.get("/api/health")
@app.get("/health")
def health():
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
    if settings.redis_enabled:
        try:
            from src.database.redis_client import redis_client
            redis_client.client.ping()
            checks["redis"] = "正常"
        except Exception:
            checks["redis"] = "未连接（可选缓存）"
    else:
        checks["redis"] = "未启用（可选缓存）"

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
