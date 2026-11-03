# 第10课：RAG知识检索（上）—— 嵌入模型 + 文档加载

> 🎯 **本课目标**：写嵌入模型和文档加载器，把知识库文档"喂"进向量数据库。

---

## 10.1 回顾RAG是什么

> RAG = Retrieval Augmented Generation（检索增强生成）

简单说：**让AI先"翻书"找到相关内容，再回答问题。**

比如你有一本产品手册，你问"产品的保修期是多久？"
1. 系统去向量数据库搜索"保修期"相关的文档段落
2. 把搜到的内容附在问题后面："[文档内容]：...保修期为2年..."
3. 发给大模型，大模型看着资料回答："根据产品手册，保修期为2年"

---

## 10.2 环节1：嵌入模型 —— 把文字变成向量

### 为什么要嵌入模型？

要搜索"语义相近"的内容，需要先把文字变成向量。
"嵌入"（Embedding）就是"把文字映射到数字空间"。

```
"苹果很好吃" → 嵌入模型 → [0.12, -0.45, 0.78, 0.33, ...]（384个数字）
```

### 两种嵌入模型

1. **sentence-transformers**（优先使用）：专业的嵌入模型，效果好
2. **简易n-gram嵌入器**（兜底方案）：纯Python实现，不依赖torch

为什么要有兜底？因为Python 3.14可能没有torch的预编译包，sentence-transformers装不上。

### 写代码：`src/rag/embedder.py`

```python
"""
简易本地嵌入模型 - Python 3.14 兼容，不依赖 torch/sentence-transformers

使用字符级 n-gram 哈希向量作为嵌入，配合关键词加权。
当 sentence-transformers 可用时会优先使用。
"""
import re
import hashlib
import struct


class SimpleEmbedder:
    """简易嵌入器：使用 n-gram 哈希生成向量，无需 ML 依赖
    
    原理：
    1. 把文本拆成1-gram、2-gram、3-gram（字符组合）
    2. 对每个gram做哈希，映射到384维空间
    3. 同时提取词级特征
    4. L2归一化得到最终向量
    
    例如 "你好":
    - 1-grams: "你", "好"
    - 2-grams: "你好"  
    - 词: "你好"
    
    每个gram都映射到向量中的某个位置并加权。
    """

    def __init__(self, dim: int = 384):
        self.dim = dim  # 向量维度（384维）

    def encode(self, text):
        """将文本编码为固定维度向量
        
        支持：
        - 单个字符串 → 返回list[float]
        - 字符串列表 → 返回list[list[float]]
        """
        if isinstance(text, list):
            return self.encode_batch(text)

        text = text.lower().strip()
        vector = [0.0] * self.dim

        # 1-gram（单个字符）
        for ch in text:
            idx = ord(ch) % self.dim
            vector[idx] += 0.1

        # 2-gram（两个字符的组合）
        for i in range(len(text) - 1):
            bigram = text[i:i+2]
            h = hashlib.md5(bigram.encode()).digest()
            idx = struct.unpack('<I', h[:4])[0] % self.dim
            vector[idx] += 0.15

        # 3-gram（三个字符的组合）
        for i in range(len(text) - 2):
            trigram = text[i:i+3]
            h = hashlib.md5(trigram.encode()).digest()
            idx = struct.unpack('<I', h[:4])[0] % self.dim
            vector[idx] += 0.1

        # 词级特征
        words = re.findall(r'\w+', text)
        for word in words:
            h = hashlib.md5(word.encode()).digest()
            idx = struct.unpack('<I', h[:4])[0] % self.dim
            vector[idx] += 0.2

        # L2 归一化（把向量长度缩放到1）
        norm = sum(v * v for v in vector) ** 0.5
        if norm > 0:
            vector = [v / norm for v in vector]

        return vector

    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        """批量编码"""
        return [self.encode(t) for t in texts]


# 全局实例
simple_embedder = SimpleEmbedder()


def get_embedding_model():
    """获取嵌入模型 - 优先使用 sentence-transformers，否则用简易嵌入器"""
    try:
        from sentence_transformers import SentenceTransformer
        from src.config import settings
        model = SentenceTransformer(settings.embedding_model)
        print(f"✅ 使用 sentence-transformers 嵌入模型: {settings.embedding_model}")
        return model
    except ImportError:
        print("⚠ sentence-transformers 不可用（可能Python 3.14无torch支持），使用简易嵌入器")
        return simple_embedder
```

---

## 10.3 环节2：文档加载器 —— 把文档切成小块

### 为什么要"切块"？

大模型一次能处理的文字有限（token限制）。一本产品手册可能几万字，不能全塞进去。

所以要**分块（Chunking）**：
```
原始文档（10000字）
    ↓ 切块
[块1：500字] [块2：500字] [块3：500字] ... [块20：500字]
    ↓ 嵌入
[向量1] [向量2] [向量3] ... [向量20]
    ↓ 存入向量数据库
```

搜索时，只取**最相关的几个块**发给大模型。

### 写代码：`src/rag/document_loader.py`

```python
"""文档加载器：将 txt/md 文件导入向量数据库"""
import re
import uuid
from pathlib import Path

from src.config import settings
from src.database.chroma_client import chroma_client
from src.database.mysql_client import mysql_client
from src.rag.embedder import get_embedding_model

# 知识库目录：项目根目录下的 knowledge_base 文件夹
KNOWLEDGE_BASE = Path(__file__).parent.parent.parent / "knowledge_base"


class DocumentLoader:
    """知识库文档加载器
    
    流程：
    1. 读取文件（.txt / .md）
    2. 把内容切成小块（chunk）
    3. 每个块生成嵌入向量
    4. 存入向量数据库 + MySQL注册
    """

    def __init__(self):
        self._embedding_model = None

    @property
    def embedding_model(self):
        if self._embedding_model is None:
            self._embedding_model = get_embedding_model()
        return self._embedding_model

    def load_all(self) -> list[dict]:
        """加载 knowledge_base 目录下所有文档"""
        if not KNOWLEDGE_BASE.exists():
            print(f"知识库目录不存在: {KNOWLEDGE_BASE}")
            return []

        results = []
        for filepath in KNOWLEDGE_BASE.iterdir():
            if filepath.suffix in (".txt", ".md"):
                try:
                    result = self.load_document(filepath)
                    results.append(result)
                    print(f"✅ 加载: {filepath.name} → {result['chunks']} 块")
                except Exception as e:
                    print(f"❌ 加载失败 {filepath.name}: {e}")
        return results

    def load_document(self, filepath: Path) -> dict:
        """加载单个文档：读取 → 分块 → 嵌入 → 存储"""
        content = filepath.read_text(encoding="utf-8")
        file_type = filepath.suffix.lstrip(".")

        # 在 MySQL 中注册文档
        doc_id = mysql_client.register_document(filepath.name, file_type)

        # 推断文档领域（公司、产品、技术、政策等）
        domain = self._infer_domain(filepath.name, content)

        # 切分文档
        chunks = self._chunk_text(content)

        if not chunks:
            mysql_client.update_document_status(doc_id, "ready", 0)
            return {"filename": filepath.name, "chunks": 0, "status": "ready"}

        # 批量生成嵌入向量并存储
        chunk_ids = []
        embeddings_list = []
        metadatas = []

        batch_size = 32  # 每批处理32个块

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            # 批量生成嵌入
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

        # 批量存入向量数据库
        chroma_client.add_documents(
            ids=chunk_ids,
            documents=chunks,
            metadatas=metadatas,
            embeddings=embeddings_list,
        )

        # 更新文档状态
        mysql_client.update_document_status(doc_id, "ready", len(chunks))

        return {
            "filename": filepath.name,
            "chunks": len(chunks),
            "status": "ready",
            "domain": domain,
        }

    def _chunk_text(self, text: str) -> list[str]:
        """按段落和句子将文本分割为重叠的块
        
        分块策略：
        1. 先按段落分割（空行）
        2. 段落过长 → 按句子分割
        3. 句子过长 → 硬截断
        4. 遇到Markdown标题（#开头）→ 新块开始
        """
        paragraphs = re.split(r'\n\s*\n', text)

        chunks = []
        current_chunk = ""
        chunk_size = settings.chunk_size  # 每块最大字数（默认1000）

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

            # 当前块 + 新段落会超过限制
            if len(current_chunk) + len(para) > chunk_size:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())

                # 段落本身过长，按句子拆分
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

    def _infer_domain(self, filename: str, content: str) -> str:
        """从文件名和内容推断知识领域"""
        combined = (filename + " " + content[:500]).lower()

        domain_keywords = {
            "company": ["公司", "关于", "我们", "企业", "组织", "介绍"],
            "product": ["产品", "功能", "服务", "解决方案", "平台", "手册"],
            "technical": ["api", "代码", "技术", "架构", "系统", "配置", "协议"],
            "policy": ["政策", "规则", "法规", "合规", "安全", "隐私", "条款"],
            "faq": ["常见问题", "问答", "帮助", "支持", "问题", "故障"],
        }

        for domain, keywords in domain_keywords.items():
            if any(kw in combined for kw in keywords):
                return domain
        return "general"


# 全局实例
document_loader = DocumentLoader()
```

---

## 10.4 写一些测试用的知识库文档

在 `knowledge_base/` 目录下创建几份文档（如果还没有的话）：

### `knowledge_base/company_intro.md`：
```markdown
# 深度求索公司简介

深度求索（DeepSeek）是一家专注于人工智能研究的科技公司。

## 核心产品
- DeepSeek 大语言模型：我们提供多个版本的AI模型，包括DeepSeek-V4等
- API 服务：开发者可以通过API接口调用我们的模型能力
- 企业定制方案：为企业提供AI解决方案

## 公司愿景
让AI技术普惠大众，降低AI使用门槛。

## 联系方式
- 官网：https://www.deepseek.com
- 邮箱：contact@deepseek.com
```

### `knowledge_base/faq.md`：
```markdown
# 常见问题（FAQ）

## 如何获取API密钥？
1. 访问 platform.deepseek.com
2. 注册账号
3. 进入API Keys页面创建密钥

## 支持哪些编程语言？
我们提供Python、JavaScript、Java、Go等语言的SDK。

## API调用限制是多少？
免费用户每分钟最多60次请求，付费用户无限制。

## 数据安全吗？
我们使用企业级加密，所有数据传输均通过HTTPS。
```

### `knowledge_base/policies.txt`：
```
隐私政策

1. 数据收集
我们仅收集提供服务所必需的信息。

2. 数据使用
用户数据仅用于改善服务质量，不会出售给第三方。

3. 数据保留
用户可在任何时候请求删除其数据。

4. 退款政策
购买后7天内可申请全额退款。超过7天按使用比例退款。
```

---

## 10.5 测试文档加载

创建 `test_loader.py`：

```python
"""测试文档加载器"""
from src.rag.document_loader import document_loader
from src.database.chroma_client import chroma_client

# 加载所有知识库文档
print("加载知识库文档...")
results = document_loader.load_all()

print(f"\n✅ 加载完成，共 {len(results)} 个文档：")
for r in results:
    print(f"   📄 {r['filename']}: {r['chunks']} 块 [{r.get('domain', '未知')}]")

# 查看向量库状态
stats = chroma_client.collection_stats()
print(f"\n✅ 向量库中共 {stats['total_chunks']} 个文档块")
```

运行：
```bash
python test_loader.py
```

预期输出：
```
✅ 使用简易嵌入器
✅ 加载: company_intro.md → 2 块 [company]
✅ 加载: faq.md → 3 块 [faq]
✅ 加载: policies.txt → 2 块 [policy]

✅ 加载完成，共 3 个文档
✅ 向量库中共 7 个文档块
```

---

> **下一课**：[第11课：RAG知识检索（下）](./11-RAG知识检索下.md) —— 写查询分析器 + 检索器。

> ✅ **检验清单**：
> - [ ] `src/rag/embedder.py` 已创建
> - [ ] `src/rag/document_loader.py` 已创建
> - [ ] `knowledge_base/` 下有文档
> - [ ] `python test_loader.py` 成功加载文档
