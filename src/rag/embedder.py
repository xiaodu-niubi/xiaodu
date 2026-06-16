"""
简易本地嵌入模型 - Python 3.14 兼容，不依赖 torch/sentence-transformers

使用字符级 n-gram 哈希向量作为嵌入，配合关键词加权。
当 sentence-transformers 可用时会优先使用。
"""
import re
import hashlib
import struct


class SimpleEmbedder:
    """简易嵌入器：使用 n-gram 哈希生成向量，无需 ML 依赖"""

    def __init__(self, dim: int = 384):
        self.dim = dim

    def encode(self, text):
        """将文本编码为固定维度向量 - 支持单个字符串或字符串列表"""
        if isinstance(text, list):
            return self.encode_batch(text)
        text = text.lower().strip()
        vector = [0.0] * self.dim

        # 1-gram（单字/词）
        for ch in text:
            idx = ord(ch) % self.dim
            vector[idx] += 0.1

        # 2-gram
        for i in range(len(text) - 1):
            bigram = text[i:i+2]
            h = hashlib.md5(bigram.encode()).digest()
            idx = struct.unpack('<I', h[:4])[0] % self.dim
            vector[idx] += 0.15

        # 3-gram
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

        # L2 归一化
        norm = sum(v * v for v in vector) ** 0.5
        if norm > 0:
            vector = [v / norm for v in vector]

        return vector

    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.encode(t) for t in texts]


# 全局实例
simple_embedder = SimpleEmbedder()


def get_embedding_model():
    """获取嵌入模型 - 优先使用 sentence-transformers，否则用简易嵌入器"""
    try:
        from sentence_transformers import SentenceTransformer
        from src.config import settings
        return SentenceTransformer(settings.embedding_model)
    except ImportError:
        print("⚠ sentence-transformers 不可用（Python 3.14 暂无 torch 支持），使用简易嵌入器")
        return simple_embedder
