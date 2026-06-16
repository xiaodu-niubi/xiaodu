"""Agentic RAG 检索器 - 自适应多跳检索与相关性评分

与静态 RAG 不同，本检索器：
1. 根据查询复杂度自适应调整检索深度
2. 执行多跳检索：初始结果指导后续查询
3. 按相关性重新排序结果
4. 返回带置信度评分的结果
"""
import re

from src.config import settings
from src.database.chroma_client import chroma_client
from src.rag.query_analyzer import query_analyzer
from src.rag.embedder import get_embedding_model


class AgenticRetriever:
    """自适应检索器"""

    def __init__(self):
        self._embedding_model = None

    @property
    def embedding_model(self):
        if self._embedding_model is None:
            self._embedding_model = get_embedding_model()
        return self._embedding_model

    def retrieve(self, query: str) -> dict:
        """主入口：分析查询，执行自适应检索"""
        analysis = query_analyzer.analyze(query)

        if not analysis.need_retrieval:
            return {
                "results": [],
                "analysis": analysis,
                "summary": None,
            }

        all_results = []

        # 主查询检索
        main_results = self._single_retrieval(query, analysis.retrieval_depth)
        all_results.extend(main_results)

        # 多跳：使用子查询
        for sub_q in analysis.sub_queries:
            sub_results = self._single_retrieval(sub_q, max(analysis.retrieval_depth - 1, 2))
            all_results.extend(sub_results)

        # 去重并重排序
        ranked = self._deduplicate_and_rerank(all_results, query)

        # 构建上下文摘要
        summary = self._build_summary(ranked[:analysis.retrieval_depth], query)

        return {
            "results": ranked[:analysis.retrieval_depth],
            "analysis": analysis,
            "summary": summary,
        }

    def _single_retrieval(self, query: str, n_results: int = 5) -> list[dict]:
        """对 Chroma 执行单次检索"""
        try:
            embedding = self.embedding_model.encode(query)
            if hasattr(embedding, 'tolist'):
                embedding = embedding.tolist()

            # 不限制领域，搜索全部文档以获取最相关结果
            result = chroma_client.query(embedding, n_results=n_results)

            docs = []
            if result and result.get("ids") and result["ids"][0]:
                for i, doc_id in enumerate(result["ids"][0]):
                    docs.append({
                        "id": doc_id,
                        "content": result["documents"][0][i] if result.get("documents") else "",
                        "metadata": result["metadatas"][0][i] if result.get("metadatas") else {},
                        "distance": result["distances"][0][i] if result.get("distances") else 0,
                    })
            return docs
        except Exception as e:
            print(f"检索错误: {e}")
            return []

    def _deduplicate_and_rerank(self, results: list[dict], query: str) -> list[dict]:
        """去重并按关键词相关性重新排序"""
        if not results:
            return []

        # 去除内容完全相同的重复项
        seen = set()
        unique = []
        for r in results:
            content_hash = hash(r["content"][:200])
            if content_hash not in seen:
                seen.add(content_hash)
                unique.append(r)

        # 重排序：结合向量距离和关键词重叠
        query_words = set(re.findall(r'\w+', query.lower()))
        for r in unique:
            content_words = set(re.findall(r'\w+', r["content"].lower()))
            keyword_overlap = len(query_words & content_words) / max(len(query_words), 1)
            vector_score = 1.0 - min(r.get("distance", 0.5), 1.0)
            r["relevance"] = vector_score * 0.7 + keyword_overlap * 0.3

        return sorted(unique, key=lambda x: x.get("relevance", 0), reverse=True)

    def _build_summary(self, results: list[dict], query: str) -> str:
        """从检索到的文档块中构建简洁摘要"""
        if not results:
            return None

        summaries = []
        for i, r in enumerate(results[:3], 1):
            content = r["content"]
            snippet = content[:300].replace("\n", " ").strip()
            if len(content) > 300:
                snippet += "..."
            source = r.get("metadata", {}).get("filename", f"来源-{i}")
            summaries.append(f"[{source}] {snippet}")

        return "\n\n".join(summaries)


agentic_retriever = AgenticRetriever()
