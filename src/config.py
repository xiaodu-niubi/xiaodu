"""配置管理 - 从环境变量加载所有配置项"""
import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


class Settings:
    """全局配置单例"""

    # 大模型配置
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
    llm_model: str = os.getenv("LLM_MODEL", "deepseek-chat")
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    llm_max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "4096"))

    # MySQL 配置
    mysql_host: str = os.getenv("MYSQL_HOST", "localhost")
    mysql_port: int = int(os.getenv("MYSQL_PORT", "3306"))
    mysql_user: str = os.getenv("MYSQL_USER", "root")
    mysql_password: str = os.getenv("MYSQL_PASSWORD", "")
    mysql_database: str = os.getenv("MYSQL_DATABASE", "deepseek")

    # Redis 配置
    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_db: int = int(os.getenv("REDIS_DB", "0"))
    redis_password: str = os.getenv("REDIS_PASSWORD", "")

    # Chroma 向量数据库配置
    chroma_host: str = os.getenv("CHROMA_HOST", "localhost")
    chroma_port: int = int(os.getenv("CHROMA_PORT", "8001"))
    chroma_collection: str = os.getenv("CHROMA_COLLECTION", "deepseek_knowledge")

    # 嵌入模型配置
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "1000"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "200"))

    # 智能体配置
    max_agent_iterations: int = int(os.getenv("MAX_AGENT_ITERATIONS", "10"))
    memory_ttl_seconds: int = int(os.getenv("MEMORY_TTL_SECONDS", "86400"))
    max_context_messages: int = int(os.getenv("MAX_CONTEXT_MESSAGES", "20"))

    # MCP 协议配置
    mcp_server_port: int = int(os.getenv("MCP_SERVER_PORT", "9000"))

    # API 服务配置
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))

    # 天气检测关键词（逗号分隔）
    weather_keywords: str = os.getenv("WEATHER_KEYWORDS", "天气,气温,温度,下雨,刮风,下雪,雾霾,weather,下雨吗,热吗,冷吗,湿度,风大")

    # 支持的城市名（逗号分隔）
    weather_cities: str = os.getenv("WEATHER_CITIES", "北京,上海,广州,深圳,杭州,成都,重庆,武汉,南京,天津,西安,长沙,郑州,济南,青岛,大连,厦门,福州,苏州,昆明,贵阳,沈阳,哈尔滨,长春,石家庄,太原,合肥,南昌,南宁,海口,拉萨,银川,乌鲁木齐,兰州,西宁,呼和浩特,三亚,Tokyo,London,New York,Paris,Berlin,Sydney")

    @property
    def mysql_url(self) -> str:
        return f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}?charset=utf8mb4"

    @property
    def chroma_url(self) -> str:
        return f"http://{self.chroma_host}:{self.chroma_port}"


settings = Settings()
