# 第11课：RAG知识检索（下）—— 查询分析 + 检索器

> 🎯 **本课目标**：写查询分析器（判断要不要检索、怎么检索）和检索器（执行搜索并排序）。

---

## 11.1 回顾：完整的检索流程

```
用户问题："公司有哪些产品？"
    │
    ▼
查询分析器 (query_analyzer.py)
    │ 分析：包含"公司"和"产品"关键词 → 需要检索
    │ 领域：company, product
    │ 深度：4
    │
    ▼
检索器 (retriever.py)
    │ 1. 生成查询向量
    │ 2. 去向量数据库搜索
    │ 3. 去重 + 重排序
    │ 4. 构建摘要
    │
    ▼
返回结果："[company_intro.md] 深度求索是一家AI公司...核心产品包括..."
```

---

## 11.2 写代码：`src/rag/query_analyzer.py`

这个模块负责**分析用户的问题，决定检索策略**。

```python
"""Agentic RAG 查询分析器 - 动态决定检索策略

与静态RAG不同，本分析器在检索前分析查询以决定：
1. 是否需要检索（闲聊就不用检索）
2. 检索什么（哪些领域）
3. 检索多少（深度）
4. 是否拆成子查询
"""
from dataclasses import dataclass, field


@dataclass
class QueryAnalysis:
    """查询分析结果"""
    need_retrieval: bool                     # 是否需要检索
    retrieval_domains: list[str] = field(default_factory=list)  # 涉及的领域
    sub_queries: list[str] = field(default_factory=list)        # 拆解后的子查询
    retrieval_depth: int = 3                 # 检索深度（取多少个结果）
    reasoning: str = ""                      # 分析理由


class QueryAnalyzer:
    """分析用户查询，做出动态检索决策"""

    # ── 检索信号词（包含这些词 → 需要检索知识库）──
    RETRIEVAL_INDICATORS = [
        # 中文
        "什么", "怎么", "如何", "解释", "描述", "告诉", "定义",
        "谁", "何时", "哪里", "为什么", "关于", "信息", "哪些",
        "文档", "知识", "政策", "手册", "指南", "产品", "提供",
        "规格", "详情", "历史", "背景", "特性", "功能", "申请",
        "公司", "服务", "流程", "规则", "规定", "标准", "退款",
        # 英文
        "what", "how", "explain", "describe", "tell", "define",
        "who", "when", "where", "why", "about", "information",
    ]

    # ── 闲聊标识（包含这些词但很短 → 只是打招呼）──
    CHAT_INDICATORS = [
        "你好", "嗨", "谢谢", "感谢", "再见", "拜拜",
        "hello", "hi", "hey", "thanks", "bye", "goodbye",
    ]

    # ── 领域关键词映射 ──
    DOMAIN_KEYWORDS = {
        "company": ["公司", "关于", "我们", "组织", "企业",
                     "about", "who are you", "organization"],
        "product": ["产品", "功能", "特性", "解决方案", "平台", "服务", "api",
                     "product", "feature", "offering", "solution"],
        "technical": ["技术", "代码", "架构", "系统", "配置", "协议",
                       "模型", "参数", "api", "code", "technical", "deployment"],
        "policy": ["政策", "规则", "法规", "合规", "安全", "隐私", "退款",
                    "policy", "rule", "regulation", "privacy", "term"],
        "faq": ["常见问题", "问答", "帮助", "支持", "问题", "错误", "故障",
                "怎么办", "如何解决", "faq", "help", "support", "issue", "fix"],
    }

    def analyze(self, query: str) -> QueryAnalysis:
        """分析查询并决定检索策略
        
        返回 QueryAnalysis 对象，包含是否需要检索、检索哪些领域、检索深度等。
        """
        query_lower = query.lower().strip()

        # 第1步：检查是否只是闲聊
        if self._is_small_talk(query_lower):
            return QueryAnalysis(
                need_retrieval=False,
                reasoning="这是闲聊/打招呼，无需检索知识库。",
            )

        # 第2步：检查是否有检索信号
        has_retrieval_signal = any(
            indicator in query_lower for indicator in self.RETRIEVAL_INDICATORS
        )

        if not has_retrieval_signal:
            return QueryAnalysis(
                need_retrieval=False,
                reasoning="查询中未检测到知识检索信号。",
            )

        # 第3步：确定涉及的领域
        domains = self._match_domains(query_lower)

        # 第4步：拆解复杂查询
        sub_queries = self._decompose_query(query)

        # 第5步：自适应深度（领域越多 → 检索越多）
        depth = min(len(domains) + 2, 7)

        return QueryAnalysis(
            need_retrieval=True,
            retrieval_domains=domains,
            sub_queries=sub_queries,
            retrieval_depth=depth,
            reasoning=f"查询包含检索信号。匹配领域：{domains}。深度：{depth}。",
        )

    def _is_small_talk(self, query: str) -> bool:
        """判断是否为闲聊"""
        # 明确的闲聊词
        for indicator in self.CHAT_INDICATORS:
            if indicator in query:
                return True
        # 中文疑问词检查（包含疑问词的不是闲聊）
        question_words = ["什么", "怎么", "如何", "为什么", "哪些", "哪个",
                          "何时", "哪里", "谁", "多少",
                          "how", "why", "what", "when", "where", "who"]
        if any(ind in query for ind in question_words):
            return False
        # 很短的文本 → 闲聊
        if any('一' <= c <= '鿿' for c in query):
            return len(query) <= 5  # 中文5字以下
        return len(query.split()) <= 2  # 英文2词以下

    def _match_domains(self, query: str) -> list[str]:
        """匹配查询涉及的领域"""
        domains = []
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            if any(kw in query for kw in keywords):
                domains.append(domain)
        return domains or ["general"]

    def _decompose_query(self, query: str) -> list[str]:
        """将复杂查询拆解为子查询
        
        例如："公司有什么产品和退款政策？"
        → ["公司有什么产品？", "退款政策是什么？"]
        """
        sub_queries = []

        # 按连接词拆分
        for sep in ["和", "与", "以及", " and "]:
            if sep in query:
                parts = query.split(sep)
                if len(parts) >= 2:
                    sub_queries = [p.strip() for p in parts[:3]]
                    break

        # 多问句检测
        if "？" in query or "?" in query:
            questions = []
            for q in query.replace("?", "？").split("？"):
                if q.strip():
                    questions.append(q.strip() + "？")
            if len(questions) > 1:
                sub_queries = questions[:3]

        return sub_queries


# 全局实例
query_analyzer = QueryAnalyzer()
```

---

## 11.3 写代码：`src/rag/retriever.py`

这个模块是检索的**核心执行者**。

```python
"""Agentic RAG 检索器 - 自适应多跳检索与相关性评分

与静态 RAG 不同，本检索器：
1. 根据查询复杂度自适应调整检索深度
2. 执行多跳检索：用初始结果指导后续查询
3. 按相关性重新排序
4. 返回带置信度评分的结果
"""
import re

from src.config import settings
from src.database.chroma_client import chroma_client
from src.rag.query_analyzer import query_analyzer
from src.rag.embedder import get_embedding_model


class AgenticRetriever:
    """自适应检索器 - RAG的核心引擎"""

    def __init__(self):
        self._embedding_model = None

    @property
    def embedding_model(self):
        if self._embedding_model is None:
            self._embedding_model = get_embedding_model()
        return self._embedding_model

    def retrieve(self, query: str) -> dict:
        """主入口：分析查询 → 执行自适应检索 → 返回结果

        返回格式：
        {
            "results": [...],       # 检索到的文档块列表
            "analysis": QueryAnalysis,  # 查询分析结果
            "summary": "..."        # 内容摘要
        }
        """
        # 第1步：分析查询
        analysis = query_analyzer.analyze(query)

        # 不需要检索（闲聊等）
        if not analysis.need_retrieval:
            return {
                "results": [],
                "analysis": analysis,
                "summary": None,
            }

        all_results = []

        # 第2步：主查询检索
        main_results = self._single_retrieval(query, analysis.retrieval_depth)
        all_results.extend(main_results)

        # 第3步：多跳检索（用子查询再搜）
        for sub_q in analysis.sub_queries:
            sub_results = self._single_retrieval(sub_q, max(analysis.retrieval_depth - 1, 2))
            all_results.extend(sub_results)

        # 第4步：去重 + 重排序
        ranked = self._deduplicate_and_rerank(all_results, query)

        # 第5步：构建摘要
        summary = self._build_summary(ranked[:analysis.retrieval_depth], query)

        return {
            "results": ranked[:analysis.retrieval_depth],
            "analysis": analysis,
            "summary": summary,
        }

    def _single_retrieval(self, query: str, n_results: int = 5) -> list[dict]:
        """执行单次检索
        
        1. 把查询文本转成向量
        2. 去向量数据库找相似文档
        3. 返回结果列表
        """
        try:
            # 生成查询向量
            embedding = self.embedding_model.encode(query)
            if hasattr(embedding, 'tolist'):
                embedding = embedding.tolist()

            # 查询向量数据库
            result = chroma_client.query(embedding, n_results=n_results)

            # 格式化结果
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
        """去重并按关键词相关性重新排序
        
        排序策略：向量距离(70%) + 关键词重叠(30%)
        """
        if not results:
            return []

        # 去重：内容前200字相同 → 视为重复
        seen = set()
        unique = []
        for r in results:
            content_hash = hash(r["content"][:200])
            if content_hash not in seen:
                seen.add(content_hash)
                unique.append(r)

        # 重排序
        query_words = set(re.findall(r'\w+', query.lower()))
        for r in unique:
            content_words = set(re.findall(r'\w+', r["content"].lower()))
            # 关键词重叠率
            keyword_overlap = len(query_words & content_words) / max(len(query_words), 1)
            # 向量得分（距离越小→得分越高）
            vector_score = 1.0 - min(r.get("distance", 0.5), 1.0)
            # 综合得分
            r["relevance"] = vector_score * 0.7 + keyword_overlap * 0.3

        # 按综合得分降序排列
        return sorted(unique, key=lambda x: x.get("relevance", 0), reverse=True)

    def _build_summary(self, results: list[dict], query: str) -> str:
        """从检索结果构建简洁摘要"""
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


# 全局实例
agentic_retriever = AgenticRetriever()
```

---

## 11.4 测试完整RAG流程

创建 `test_rag.py`：

```python
"""测试完整RAG流程"""
from src.rag.query_analyzer import query_analyzer
from src.rag.retriever import agentic_retriever

# ⚠️ 运行此测试前，确保已加载知识库：python -m src.rag.document_loader

print("=" * 60)
print("RAG 知识检索测试")
print("=" * 60)

# 测试1：查询分析
test_queries = [
    "你好",
    "公司提供哪些产品？",
    "如何申请API密钥？退款政策是什么？",
    "今天天气怎么样？",
]

for q in test_queries:
    print(f"\n📝 用户提问：'{q}'")
    analysis = query_analyzer.analyze(q)
    print(f"   需要检索: {analysis.need_retrieval}")
    if analysis.need_retrieval:
        print(f"   领域: {analysis.retrieval_domains}")
        print(f"   子查询: {analysis.sub_queries}")
        print(f"   深度: {analysis.retrieval_depth}")
    print(f"   理由: {analysis.reasoning}")

# 测试2：完整检索
print("\n" + "=" * 60)
print("检索测试")
print("=" * 60)

test_retrieval = [
    "公司有哪些产品？",
    "如何获取API密钥？",
    "退款政策是什么？",
]

for q in test_retrieval:
    print(f"\n🔍 检索：'{q}'")
    result = agentic_retriever.retrieve(q)
    print(f"   找到 {len(result['results'])} 个结果")
    if result.get("summary"):
        print(f"   摘要：")
        # 分行显示
        for line in result["summary"].split("\n")[:5]:
            print(f"     {line[:100]}...")

print("\n✅ RAG测试完成！")
```

运行：
```bash
# 先加载知识库
python -m src.rag.document_loader

# 再测试
python test_rag.py
```

---

## 11.5 检索流程总结

```
查询进入
    │
    ▼
QueryAnalyzer.analyze(query)
    │
    ├─ 闲聊？→ 不检索，直接回答
    ├─ 无检索信号？→ 不检索
    └─ 需要检索 → 确定领域、深度、子查询
              │
              ▼
AgenticRetriever.retrieve(query)
    │
    ├─ 主查询检索
    ├─ 子查询检索（多跳）
    ├─ 去重（相同内容只留1个）
    ├─ 重排序（向量+关键词）
    └─ 构建摘要
              │
              ▼
返回结果给调用方（将要被RAG智能体使用）
```

---

> **下一课**：[第12课：Agent基类](./12-Agent基类.md) —— 写BaseAgent，实现ReAct思考-行动-观察循环。

> ✅ **检验清单**：
> - [ ] `src/rag/query_analyzer.py` 已创建
> - [ ] `src/rag/retriever.py` 已创建
> - [ ] `python test_rag.py` 能正确分析查询意图
> - [ ] 理解了"查询分析→检索→去重→重排序→摘要"的完整流程
