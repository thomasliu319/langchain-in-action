"""
配置模块
"""
import  os
from dotenv import load_dotenv

# 加载 .env 文件（从 backend 根目录）
from pathlib import Path


env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path, override=True) # 强制覆盖已存在的环境变量


class Settings:
    """应用配置 - 直接从环境变量读取"""

    # AI 模型配置
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")

    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

    # LangSmith 配置（用于追踪和评估）
    LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "true").lower() == "true"
    LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY", "")
    LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "medical_assistant")

    # 数据库配置
    DATABASE_URL = os.getenv("DATABASE_URL", "")
    POSTGRES_SHORT_TERM_URL = os.getenv("POSTGRES_SHORT_TERM_URL", "")
    POSTGRES_LONG_TERM_URL = os.getenv("POSTGRES_LONG_TERM_URL", "")
    POSTGRES_SESSION_URL = os.getenv("POSTGRES_SESSION_URL", "")

    # 长期记忆后端类型：postgres | milvus
    LONG_TERM_MEMORY_TYPE = os.getenv("LONG_TERM_MEMORY_TYPE", "postgres").lower()

    # Redis 短期记忆配置
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_CHECKPOINT_TTL = int(os.getenv("REDIS_CHECKPOINT_TTL", "86400"))  # 默认 24h

    # Milvus 长期记忆配置
    MILVUS_URI = os.getenv("MILVUS_URI", "http://192.168.3.22:19530")

    # ChromaDB 长期记忆配置（保留兼容，当前未使用）
    CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
    EMBED_MODEL_NAME = os.getenv("EMBED_MODEL_NAME", "all-MiniLM-L6-v2")
    VECTOR_MEMORY_TOP_K = int(os.getenv("VECTOR_MEMORY_TOP_K", "10"))


    # 应用配置
    SECRET_KEY = os.getenv("SECRET_KEY", "default-secret-key")
    ALGORITHM = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

    # 本地 VL 模型配置（文档提取用）
    VL_MODEL_PATH = os.getenv("VL_MODEL_PATH", "/home/thomas/Downloads/models/Qwen2.5-VL-7B-Instruct")
    VL_MODEL_SERVER_URL = os.getenv("VL_MODEL_SERVER_URL", "http://localhost:8006/v1")

    # 服务器配置
    HOST = os.getenv("HOST")
    PORT = int(os.getenv("PORT"))


# 创建全局配置实例
settings = Settings()