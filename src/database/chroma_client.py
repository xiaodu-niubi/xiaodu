"""简易向量数据库 - 基于 numpy 的本地向量存储（无需外部服务）

替代 Chroma，适用于 Python 3.14 环境。
支持添加文档、余弦相似度检索和元数据过滤。
"""
import os
import json
import pickle
import numpy as np

from src.config import settings

VECTOR_STORE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'vector_data')


class ChromaClient:
    """本地向量存储（接口兼容 Chroma）"""

    def __init__(self):
        self._data = None
        os.makedirs(VECTOR_STORE_DIR, exist_ok=True)

    @property
    def data(self) -> dict:
        if self._data is None:
            self._data = self._load()
        return self._data

    def _load(self) -> dict:
        path = os.path.join(VECTOR_STORE_DIR, 'vectors.pkl')
        if os.path.exists(path):
            try:
                with open(path, 'rb') as f:
                    return pickle.load(f)
            except Exception:
                pass
        return {"ids": [], "documents": [], "metadatas": [], "embeddings": []}

    def _save(self):
        path = os.path.join(VECTOR_STORE_DIR, 'vectors.pkl')
        with open(path, 'wb') as f:
            pickle.dump(self._data, f)

    @property
    def collection(self):
        return self  # 自兼容接口

    def add_documents(self, ids: list[str], documents: list[str],
                      metadatas: list[dict], embeddings: list[list[float]]):
        """批量添加文档块到向量库"""
        self.data["ids"].extend(ids)
        self.data["documents"].extend(documents)
        self.data["metadatas"].extend(metadatas)
        self.data["embeddings"].extend(embeddings)
        self._save()

    def query(self, query_embedding: list[float], n_results: int = 5,
              where: dict = None) -> dict:
        """余弦相似度查询"""
        if not self.data["embeddings"]:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

        query_vec = np.array(query_embedding)
        stored_vecs = np.array(self.data["embeddings"])

        # 余弦相似度
        query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-10)
        stored_norms = stored_vecs / (np.linalg.norm(stored_vecs, axis=1, keepdims=True) + 1e-10)
        similarities = np.dot(stored_norms, query_norm)
        distances = 1.0 - similarities  # 距离

        # 按相似度排序取 top-k
        indices = np.argsort(distances)[:n_results]

        result_ids = []
        result_docs = []
        result_metas = []
        result_distances = []

        for i in indices:
            # 元数据过滤
            if where:
                meta = self.data["metadatas"][int(i)]
                match = True
                for k, v in where.items():
                    if meta.get(k) != v:
                        match = False
                        break
                if not match:
                    continue

            result_ids.append(self.data["ids"][int(i)])
            result_docs.append(self.data["documents"][int(i)])
            result_metas.append(self.data["metadatas"][int(i)])
            result_distances.append(float(distances[int(i)]))

        return {
            "ids": [result_ids],
            "documents": [result_docs],
            "metadatas": [result_metas],
            "distances": [result_distances],
        }

    def delete_by_document_id(self, doc_prefix: str):
        """删除指定文档的所有分块"""
        to_keep = []
        for i, meta in enumerate(self.data["metadatas"]):
            if meta.get("document_id") != doc_prefix:
                to_keep.append(i)

        self.data["ids"] = [self.data["ids"][i] for i in to_keep]
        self.data["documents"] = [self.data["documents"][i] for i in to_keep]
        self.data["metadatas"] = [self.data["metadatas"][i] for i in to_keep]
        self.data["embeddings"] = [self.data["embeddings"][i] for i in to_keep]
        self._save()

    def collection_stats(self) -> dict:
        return {"total_chunks": len(self.data["ids"])}


chroma_client = ChromaClient()
