"""Agentic RAG 查询分析器 - 动态决定检索策略

与静态 RAG 不同，本分析器在检索前分析查询以决定：
1. 是否需要检索
2. 检索什么（哪些知识领域）
3. 检索多少结果（自适应深度）
4. 是否分解为子查询
"""
from dataclasses import dataclass, field


@dataclass
class QueryAnalysis:
    """查询分析结果"""
    need_retrieval: bool # 是否需要检索
    retrieval_domains: list[str] = field(default_factory=list) # 检索的领域
    sub_queries: list[str] = field(default_factory=list) # 分解的子查询
    retrieval_depth: int = 3 # 检索深度
    reasoning: str = "" # 分析结果


class QueryAnalyzer:
    """分析用户查询，做出动态检索决策"""

    # 表示需要检索的关键词（中英文）
    RETRIEVAL_INDICATORS = [
        "什么", "怎么", "如何", "解释", "描述", "告诉", "定义",
        "谁", "何时", "哪里", "为什么", "关于", "信息", "哪些",
        "文档", "知识", "政策", "手册", "指南", "产品", "提供",
        "规格", "详情", "历史", "背景", "特性", "功能", "申请",
        "公司", "服务", "流程", "规则", "规定", "标准", "退款",
        "what", "how", "explain", "describe", "tell", "define",
        "who", "when", "where", "why", "about", "information",
        "document", "knowledge", "policy", "manual", "guide",
        "specification", "detail", "history", "background",
        "company", "product", "feature", "process",
    ]

    # 闲聊标识（无需检索）
    CHAT_INDICATORS = [
        "你好", "嗨", "谢谢", "感谢", "再见", "拜拜",
        "hello", "hi", "hey", "thanks", "bye", "goodbye",
    ]

    # 领域关键词映射
    DOMAIN_KEYWORDS = {
        "company": ["公司", "关于", "我们", "组织", "企业", "深度求索", "deepseek",
                     "about", "who are you", "organization"],
        "product": ["产品", "功能", "特性", "解决方案", "平台", "服务", "api",
                     "product", "feature", "offering", "solution", "platform"],
        "technical": ["技术", "代码", "架构", "系统", "基础设施", "配置", "协议",
                       "模型", "参数", "训练", "推理", "api", "code", "technical",
                       "architecture", "infrastructure", "deployment", "config"],
        "policy": ["政策", "规则", "法规", "合规", "安全", "隐私", "条款", "协议",
                    "退款", "policy", "rule", "regulation", "compliance", "privacy",
                    "term", "condition", "agreement", "license"],
        "faq": ["常见问题", "问答", "帮助", "支持", "问题", "错误", "故障",
                "怎么办", "如何解决", "faq", "question", "help", "support",
                "issue", "problem", "bug", "error", "fix", "troubleshoot"],
    }

    def analyze(self, query: str) -> QueryAnalysis:
        """分析查询并决定检索策略"""
        query_lower = query.lower().strip()

        # 检查是否只是闲聊
        if self._is_small_talk(query_lower):
            return QueryAnalysis(
                need_retrieval=False,
                reasoning="这是闲聊/打招呼，无需检索知识库。",
            )

        # 检查检索信号
        has_retrieval_signal = any(
            indicator in query_lower for indicator in self.RETRIEVAL_INDICATORS
        )

        if not has_retrieval_signal:
            return QueryAnalysis(
                need_retrieval=False,
                reasoning="查询中未检测到知识检索信号。",
            )

        # 确定需要搜索的领域
        domains = self._match_domains(query_lower)

        # 分解复杂查询为子查询
        sub_queries = self._decompose_query(query)

        # 自适应深度：领域越多 → 检索越深
        depth = min(len(domains) + 2, 7)

        return QueryAnalysis(
            need_retrieval=True,
            retrieval_domains=domains,
            sub_queries=sub_queries,
            retrieval_depth=depth,
            reasoning=f"查询包含检索信号。匹配领域：{domains}。深度：{depth}。子查询：{len(sub_queries)}个。",
        )

    def _is_small_talk(self, query: str) -> bool:
        """判断是否为闲聊（针对中文优化）"""
        for indicator in self.CHAT_INDICATORS:
            if indicator in query:
                return True
        # 中文疑问词检查
        question_words = ["什么", "怎么", "如何", "为什么", "哪些", "哪个", "何时",
                          "哪里", "谁", "多少", "how", "why", "what", "when", "where", "who"]
        if any(ind in query for ind in question_words):
            return False
        # 按字符数判断中文，按单词数判断英文
        if any('一' <= c <= '鿿' for c in query):
            return len(query) <= 5  # 中文：5个字符以下为闲聊
        return len(query.split()) <= 2  # 英文：2个词以下为闲聊

    def _match_domains(self, query: str) -> list[str]:
        """匹配查询涉及的领域"""
        domains = []
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            if any(kw in query for kw in keywords):
                domains.append(domain)
        return domains or ["general"]

    def _decompose_query(self, query: str) -> list[str]:
        """将复杂查询分解为更简单的子查询"""
        sub_queries = []

        # 按 "和" "与" "以及" 等连词分割
        if "和" in query or "与" in query or "以及" in query:
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


query_analyzer = QueryAnalyzer()
