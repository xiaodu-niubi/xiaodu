"""Document-filtered vector retrieval with Chinese lexical reranking."""
import hashlib
import re
from src.database.chroma_client import chroma_client
from src.rag.embedder import get_embedding_model


def terms(text):
    lower = text.lower()
    words = set(re.findall(r"[a-z0-9_]+", lower))
    for run in re.findall(r"[\u4e00-\u9fff]+", lower):
        words.update(run[i:i+2] for i in range(max(1, len(run)-1)))
    return words


class AgenticRetriever:
    def __init__(self):
        self._embedding_model = None

    @property
    def embedding_model(self):
        if self._embedding_model is None:
            self._embedding_model = get_embedding_model()
        return self._embedding_model

    def retrieve(self, query: str, document_ids=None):
        where = None
        if document_ids:
            where = {"document_id": {"$in": list(document_ids)}}
        # Retrieve each selected document too, so a comparison isn't dominated by one source.
        results = self._single_retrieval(query, 12, where)
        if document_ids:
            for doc_id in document_ids:
                results.extend(self._single_retrieval(query, 2, {"document_id": doc_id}))
        ranked = self._deduplicate_and_rerank(results, query)
        selected = []
        if document_ids:
            for doc_id in document_ids:
                match = next((r for r in ranked if r["metadata"].get("document_id") == doc_id), None)
                if match:
                    selected.append(match)
        seen = {r["id"] for r in selected}
        selected.extend(r for r in ranked if r["id"] not in seen)
        selected = selected[:max(6, len(document_ids or []))]
        return {"results": selected, "summary": self._build_summary(selected, query), "analysis": None}

    def _single_retrieval(self, query, n_results=6, where=None):
        embedding = self.embedding_model.encode(query)
        if hasattr(embedding, "tolist"):
            embedding = embedding.tolist()
        result = chroma_client.query(embedding, n_results=n_results, where=where)
        return [
            {"id": doc_id, "content": result["documents"][0][i],
             "metadata": result["metadatas"][0][i] or {}, "distance": result["distances"][0][i]}
            for i, doc_id in enumerate((result.get("ids") or [[]])[0])
        ]

    def _deduplicate_and_rerank(self, results, query):
        seen, unique = set(), []
        query_terms = terms(query)
        for item in results:
            digest = hashlib.sha256(item["content"].encode()).hexdigest()
            # Retain identical passages from different documents for comparison/citation.
            key = (item["metadata"].get("document_id"), digest)
            if key in seen:
                continue
            seen.add(key)
            overlap = len(query_terms & terms(item["content"])) / max(1, len(query_terms))
            item["relevance"] = (1 - min(max(item.get("distance", 1), 0), 1)) * .65 + overlap * .35
            unique.append(item)
        return sorted(unique, key=lambda r: r["relevance"], reverse=True)

    def _build_summary(self, results, query):
        return "\n\n".join(
            f"[{i}] {r['metadata'].get('filename', '知识库文档')}\n{r['content']}"
            for i, r in enumerate(results, 1)
        ) or None


agentic_retriever = AgenticRetriever()
