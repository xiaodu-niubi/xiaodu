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

    # 保存上传文件到 knowledge_base 目录
    kb_path = Path(__file__).parent.parent.parent / "knowledge_base"
    kb_path.mkdir(exist_ok=True)

    file_path = kb_path / file.filename
    content = await file.read()
    file_path.write_bytes(content)

    # 加载到 Chroma 向量数据库
    result = document_loader.load_document(file_path)

    return {
        "filename": file.filename,
        "chunks": result["chunks"],
        "status": result["status"],
    }


@router.post("/knowledge/reload")
async def reload_knowledge():
    """重新加载所有知识库文档到 Chroma"""
    results = document_loader.load_all()
    return {"loaded": len(results), "documents": results}


@router.get("/tools")
async def list_tools():
    """列出所有可用工具及其模式定义"""
    definitions = tool_registry.get_definitions()
    names = tool_registry.list_tool_names()

    tools = []
    for name, defn in zip(names, definitions):
        tools.append({
            "name": name,
            "description": defn["function"]["description"],
            "parameters": defn["function"]["parameters"],
        })

    return {"tools": tools}


@router.post("/mcp")
async def mcp_endpoint(request: dict):
    """MCP JSON-RPC 端点，用于工具发现和执行"""
    result = await mcp_server.handle_request(request)
    return result
