"""Chroma 向量数据库客户端 — 支持嵌入式（PersistentClient）和 HTTP 两种模式"""

import os

import chromadb

from src.config import settings


class ChromaClient:
    """Chroma 向量数据库客户端

    CHROMA_MODE=local:  使用 PersistentClient（嵌入式运行，无需独立服务）
    CHROMA_MODE=http:   使用 HttpClient（连接独立 Chroma 服务，如 Docker）
    """

    def __init__(self):
        self._client = None
        self._collection = None

    @property
    def client(self):
        if self._client is None:
            if settings.chroma_mode == "http":
                self._client = chromadb.HttpClient(
                    host=settings.chroma_host,
                    port=settings.chroma_port,
                )
            else:
                # 默认 local 模式：数据持久化到本地目录
                persist_dir = os.path.abspath(settings.chroma_persist_dir)
                self._client = chromadb.PersistentClient(path=persist_dir)
        return self._client

    @property
    def collection(self):
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=settings.chroma_collection,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def add_documents(self, ids: list[str], documents: list[str],
                      metadatas: list[dict], embeddings: list[list[float]]):
        """批量添加文档块到向量库"""
        if not ids:
            return
        self.collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

    def query(self, query_embedding: list[float], n_results: int = 5,
              where: dict = None) -> dict:
        """余弦相似度查询，返回格式兼容旧版 numpy 实现"""
        if self.collection.count() == 0:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, self.collection.count()),
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        return result

    def delete_by_document_id(self, doc_id: str):
        """删除指定文档的所有分块"""
        self.collection.delete(
            where={"document_id": doc_id}
        )

    def collection_stats(self) -> dict:
        """返回集合统计信息（供健康检查使用）"""
        return {"total_chunks": self.collection.count()}


# 全局单例
chroma_client = ChromaClient()
