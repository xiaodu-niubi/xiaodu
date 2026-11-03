"""文档加载器：将 txt/md 文件导入 Chroma 向量数据库"""
import re
import uuid
from pathlib import Path

from src.config import settings
from src.database.chroma_client import chroma_client
from src.database.mysql_client import mysql_client
from src.rag.embedder import get_embedding_model

KNOWLEDGE_BASE = Path(__file__).parent.parent.parent / "knowledge_base"


class DocumentLoader:
    """知识库文档加载器"""

    def __init__(self):
        self._embedding_model = None

    @property
    def embedding_model(self):
        if self._embedding_model is None:
            self._embedding_model = get_embedding_model()
        return self._embedding_model

    def load_all(self) -> list[dict]:
        """加载 knowledge_base 目录下所有文档到 Chroma"""
        if not KNOWLEDGE_BASE.exists():
            return []

        results = []
        for filepath in KNOWLEDGE_BASE.iterdir():
            if filepath.suffix.lower() in (".txt", ".md", ".pdf", ".docx"):
                try:
                    result = self.load_document(filepath)
                    results.append(result)
                except Exception as e:
                    print(f"加载失败 {filepath.name}: {e}")
                    results.append({'filename': filepath.name, 'status': 'error', 'chunks': 0})
        return results

    def load_document(self, filepath: Path) -> dict:
        """加载单个文档：读取、分块、嵌入、存入 Chroma"""
        file_type = filepath.suffix.lstrip(".")

        # 在 MySQL 中注册文档
        doc_id = mysql_client.register_document(filepath.name, file_type)
        mysql_client.update_document_status(doc_id, "processing", 0)
        try:
            content = self.read_content(filepath)
            return self._index_document(filepath, content, file_type, doc_id)
        except Exception:
            mysql_client.update_document_status(doc_id, "error", 0)
            raise

    def read_content(self, filepath: Path) -> str:
        if filepath.suffix.lower() == ".pdf":
            from pypdf import PdfReader
            parts = []
            for i, page in enumerate(PdfReader(str(filepath)).pages):
                text = page.extract_text() or ''
                if text.strip():
                    parts.append(f"第 {i + 1} 页\n{text}")
            return "\n\n".join(parts)
        if filepath.suffix.lower() == ".docx":
            from docx import Document
            doc = Document(str(filepath))
            paragraphs = [p.text for p in doc.paragraphs]
            for table in doc.tables:
                paragraphs.extend(" | ".join(c.text for c in row.cells) for row in table.rows)
            return "\n\n".join(paragraphs)
        return filepath.read_text(encoding="utf-8-sig")

    def _index_document(self, filepath, content, file_type, doc_id):
        if not content.strip():
            raise ValueError("没有可提取的文字。扫描版 PDF 请先进行 OCR。")

        # 从文件名/内容推断领域
        domain = self._infer_domain(filepath.name, content)

        # 文档分块
        chunks = self._chunk_text(content)

        if not chunks:
            mysql_client.update_document_status(doc_id, "ready", 0)
            return {"filename": filepath.name, "chunks": 0, "status": "ready"}

        # 批量生成嵌入
        chunk_ids = []
        embeddings_list = []
        metadatas = []

        batch_size = 32
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            embeddings = self.embedding_model.encode(batch)
            if hasattr(embeddings, 'tolist'):
                embeddings = embeddings.tolist()

            for j, (chunk_text, emb) in enumerate(zip(batch, embeddings)):
                chunk_id = f"{doc_id}_chunk_{i + j}"
                chunk_ids.append(chunk_id)
                embeddings_list.append(emb)
                metadatas.append({
                    "document_id": doc_id,
                    "filename": filepath.name,
                    "file_type": file_type,
                    "domain": domain,
                    "chunk_index": i + j,
                    "total_chunks": len(chunks),
                })

        # Replace an existing document's chunks so reloads don't multiply old versions.
        chroma_client.delete_by_document_id(doc_id)
        # 批量存入 Chroma
        chroma_client.add_documents(
            ids=chunk_ids,
            documents=chunks,
            metadatas=metadatas,
            embeddings=embeddings_list,
        )

        mysql_client.update_document_status(doc_id, "ready", len(chunks))

        return {
            "id": doc_id,
            "filename": filepath.name,
            "chunks": len(chunks),
            "status": "ready",
            "domain": domain,
        }

    def _chunk_text(self, text: str) -> list[str]:
        """按段落和句子将文本分割为重叠的块"""
        size = max(100, settings.chunk_size)
        overlap = min(max(0, settings.chunk_overlap), size // 2)
        text = text.strip()
        if not text:
            return []
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + size, len(text))
            if end < len(text):
                boundary = max(text.rfind('\n', start + size // 2, end), text.rfind('。', start + size // 2, end))
                if boundary > start:
                    end = boundary + 1
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end == len(text):
                break
            start = max(start + 1, end - overlap)
        return chunks

    def _infer_domain(self, filename: str, content: str) -> str:
        """从文件名和内容推断知识领域"""
        combined = (filename + " " + content[:500]).lower()

        domain_keywords = {
            "company": ["公司", "关于", "我们", "企业", "组织", "介绍"],
            "product": ["产品", "功能", "服务", "解决方案", "平台", "手册"],
            "technical": ["api", "代码", "技术", "架构", "系统", "配置", "协议"],
            "policy": ["政策", "规则", "法规", "合规", "安全", "隐私", "条款", "协议"],
            "faq": ["常见问题", "问答", "帮助", "支持", "问题", "故障"],
        }

        for domain, keywords in domain_keywords.items():
            if any(kw in combined for kw in keywords):
                return domain
        return "general"


document_loader = DocumentLoader()
