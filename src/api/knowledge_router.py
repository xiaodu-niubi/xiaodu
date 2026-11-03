"""Knowledge library endpoints with bounded uploads and source preview."""
import asyncio
import logging
import re
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException
from src.database.mysql_client import mysql_client
from src.database.chroma_client import chroma_client
from src.rag.document_loader import document_loader, KNOWLEDGE_BASE
from src.tools.tool_registry import tool_registry
from src.mcp.mcp_server import mcp_server

router = APIRouter(prefix="/api", tags=["知识库"])
logger = logging.getLogger(__name__)
MAX_BYTES = 20 * 1024 * 1024
_index_lock = asyncio.Lock()


def safe_path(filename):
    if not filename or len(filename) > 200 or re.search(r'[\\/:*?"<>|\x00-\x1f]', filename) or filename in (".", ".."):
        raise HTTPException(400, "文件名不合法，请使用普通文件名。")
    path = (KNOWLEDGE_BASE / filename).resolve()
    if not path.is_relative_to(KNOWLEDGE_BASE.resolve()):
        raise HTTPException(400, "文件路径不合法。")
    return path


@router.get("/knowledge/list")
async def list_knowledge():
    return {"documents": await asyncio.to_thread(mysql_client.list_documents)}


@router.post("/knowledge/upload")
async def upload_knowledge(file: UploadFile = File(...)):
    path = safe_path(file.filename)
    if path.suffix.lower() not in (".txt", ".md", ".pdf", ".docx"):
        raise HTTPException(400, "支持 TXT、Markdown、PDF 和 Word 文档。")
    if _index_lock.locked():
        raise HTTPException(409, "资料正在索引，请稍后再试。")
    async with _index_lock:
        if path.exists():
            raise HTTPException(409, "同名资料已存在。请修改文件名，或在资料列表中重新索引。")
        KNOWLEDGE_BASE.mkdir(exist_ok=True)
        size = 0
        try:
            with path.open("xb") as output:
                while chunk := await file.read(65536):
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise HTTPException(413, "文件不能超过 20 MB。")
                    output.write(chunk)
            if size == 0:
                raise HTTPException(400, "文件为空。")
        except BaseException:
            path.unlink(missing_ok=True)
            raise
        finally:
            await file.close()
        try:
            return await asyncio.to_thread(document_loader.load_document, path)
        except ImportError:
            raise HTTPException(503, "文档解析依赖未安装，请更新 requirements.txt 后重试。")
        except Exception:
            logger.exception("Document indexing failed")
            raise HTTPException(422, "资料索引失败。请检查文件内容与知识库连接，再从列表重试；扫描版 PDF 需要先进行 OCR。")


@router.get("/knowledge/{doc_id}/content")
async def read_document(doc_id: str):
    doc = await asyncio.to_thread(mysql_client.get_document, doc_id)
    if not doc:
        raise HTTPException(404, "资料不存在。")
    path = safe_path(doc["filename"])
    if not path.is_file():
        raise HTTPException(404, "资料原文件不存在。")
    try:
        content = await asyncio.to_thread(document_loader.read_content, path)
    except Exception:
        raise HTTPException(422, "无法读取此资料。")
    return {"id": doc_id, "filename": doc["filename"], "content": content[:200000], "truncated": len(content) > 200000}


@router.post("/knowledge/{doc_id}/reindex")
async def reindex_document(doc_id: str):
    doc = await asyncio.to_thread(mysql_client.get_document, doc_id)
    if not doc:
        raise HTTPException(404, "资料不存在。")
    if _index_lock.locked():
        raise HTTPException(409, "其他资料正在索引，请稍后再试。")
    async with _index_lock:
        try:
            return await asyncio.to_thread(document_loader.load_document, safe_path(doc["filename"]))
        except Exception:
            logger.exception("Reindex failed")
            raise HTTPException(422, "重新索引失败，请检查资料与服务连接。")


@router.post("/knowledge/reload")
async def reload_knowledge():
    if _index_lock.locked():
        raise HTTPException(409, "资料正在索引，请稍后再试。")
    async with _index_lock:
        results = await asyncio.to_thread(document_loader.load_all)
    return {"loaded": len(results), "documents": results}


@router.get("/tools")
async def list_tools():
    return {"tools": [{"name": d["function"]["name"], **d["function"]} for d in tool_registry.get_definitions()]}


@router.post("/mcp")
async def mcp_endpoint(request: dict):
    return await mcp_server.handle_request(request)
