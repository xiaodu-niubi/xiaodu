"""环境变量优先；模型密钥只读取启动进程继承的环境变量。"""
import os
from pathlib import Path
from dotenv import dotenv_values

# 绕过系统代理：httpx/chromadb 等库会走系统代理，导致本地请求返回 502
os.environ.setdefault("NO_PROXY", "localhost,127.0.0.1,::1")
os.environ.setdefault("no_proxy", "localhost,127.0.0.1,::1")

env_path = Path(__file__).parent.parent / ".env"
# .env 只补充普通配置，禁止将文件中的模型密钥注入进程环境。
for name, value in dotenv_values(env_path).items():
    if name != "LLM_API_KEY" and value is not None:
        os.environ.setdefault(name, value)


class Settings:
    """全局配置单例"""

    # 大模型配置
    llm_api_key: str = os.getenv("LLM_API_KEY", "").strip()
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
    llm_model: str = os.getenv("LLM_MODEL", "deepseek-chat")
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    llm_max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "4096"))

    # MySQL 配置
    mysql_host: str = os.getenv("MYSQL_HOST", "localhost")
    mysql_port: int = int(os.getenv("MYSQL_PORT", "3306"))
    mysql_user: str = os.getenv("MYSQL_USER", "root")
    mysql_password: str = os.getenv("MYSQL_PASSWORD", "xiaodu20030328")
    mysql_database: str = os.getenv("MYSQL_DATABASE", "deepseek")

    # Redis 配置
    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_db: int = int(os.getenv("REDIS_DB", "0"))
    redis_password: str = os.getenv("REDIS_PASSWORD", "")
    redis_enabled: bool = os.getenv("REDIS_ENABLED", "false").lower() == "true"

    # Chroma 向量数据库配置
    chroma_mode: str = os.getenv("CHROMA_MODE", "local")  # local=嵌入式PersistentClient, http=独立服务
    chroma_host: str = os.getenv("CHROMA_HOST", "localhost")
    chroma_port: int = int(os.getenv("CHROMA_PORT", "8001"))
    chroma_collection: str = os.getenv("CHROMA_COLLECTION", "deepseek_knowledge")
    chroma_persist_dir: str = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")

    # 嵌入模型配置
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    embedding_backend: str = os.getenv("EMBEDDING_BACKEND", "auto")
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "1000"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "200"))

    # 智能体配置
    max_agent_iterations: int = int(os.getenv("MAX_AGENT_ITERATIONS", "10"))
    memory_ttl_seconds: int = int(os.getenv("MEMORY_TTL_SECONDS", "86400"))
    max_context_messages: int = int(os.getenv("MAX_CONTEXT_MESSAGES", "20"))
    task_timeout_seconds: int = int(os.getenv("TASK_TIMEOUT_SECONDS", "180"))
    enable_code_execution: bool = os.getenv("ENABLE_CODE_EXECUTION", "false").lower() == "true"
    code_container_image: str = os.getenv("CODE_CONTAINER_IMAGE", "python:3.12-slim")

    # MCP 协议配置
    mcp_server_port: int = int(os.getenv("MCP_SERVER_PORT", "9000"))

    # API 服务配置
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))

    @property
    def mysql_url(self) -> str:
        return f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}?charset=utf8mb4"

    @property
    def chroma_url(self) -> str:
        return f"http://{self.chroma_host}:{self.chroma_port}"


settings = Settings()
