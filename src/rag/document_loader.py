"""文档加载器：将 txt/md 文件导入 Chroma 向量数据库"""
import re
import uuid
from pathlib import Path

from src.config import settings
from src.database.chroma_client import chroma_client
from src.database.mysql_client import mysql_client
from src.rag.embedder import get_embedding_model

# 知识库目录
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
            if filepath.suffix in (".txt", ".md"):
                try:
                    result = self.load_document(filepath)
                    results.append(result)
                except Exception as e:
                    print(f"加载失败 {filepath.name}: {e}")
        return results

    def load_document(self, filepath: Path) -> dict:
        """加载单个文档：读取、分块、嵌入、存入 Chroma"""
        content = filepath.read_text(encoding="utf-8")
        file_type = filepath.suffix.lstrip(".")

        # 在 MySQL 中注册文档
        doc_id = mysql_client.register_document(filepath.name, file_type)

        # 从文件名/内容推断领域
        domain = self._infer_domain(filepath.name, content)

        # 文档分块
        chunks = self._chunk_text(content)

        if not chunks:
            mysql_client.update_document_status(doc_id, "ready", 0)
            return {"filename": filepath.name, "chunks": 0, "status": "ready"}

        # 批量生成嵌入
        chunk_ids = [] # 块 ID
        embeddings_list = [] # 嵌入列表
        metadatas = [] # 元数据

        batch_size = 32 # 批量大小
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

        # 批量存入 Chroma
        chroma_client.add_documents(
            ids=chunk_ids,
            documents=chunks,
            metadatas=metadatas,
            embeddings=embeddings_list,
        )

        mysql_client.update_document_status(doc_id, "ready", len(chunks))

        return {
            "filename": filepath.name,
            "chunks": len(chunks),
            "status": "ready",
            "domain": domain,
        }

    @staticmethod
    def _chunk_text(text: str) -> list[str]:
        """按段落和句子将文本分割为重叠的块"""
        paragraphs = re.split(r'\n\s*\n', text)

        chunks = [] # 块列表
        current_chunk = "" # 当前块
        chunk_size = settings.chunk_size # 块大小

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Markdown 标题 → 新块开始
            if para.startswith("#"):
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = para
                continue

            if len(current_chunk) + len(para) > chunk_size:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                # 段落过长则按句子拆分
                if len(para) > chunk_size:
                    sentences = re.split(r'(?<=[.!?。！？])\s*', para)
                    sub_chunk = ""
                    for sent in sentences:
                        if len(sub_chunk) + len(sent) > chunk_size:
                            if sub_chunk:
                                chunks.append(sub_chunk.strip())
                            sub_chunk = sent
                        else:
                            sub_chunk += sent if sub_chunk else sent
                    current_chunk = sub_chunk if sub_chunk else ""
                else:
                    current_chunk = para
            else:
                current_chunk += "\n\n" + para if current_chunk else para

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    @staticmethod
    def _infer_domain(filename: str, content: str) -> str:
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
