import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # LLM (DeepSeek API via OpenAI compatible)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "deepseek-v4-pro")

    # LangSmith
    LANGCHAIN_TRACING_V2: str = os.getenv("LANGCHAIN_TRACING_V2", "true")
    LANGCHAIN_API_KEY: str = os.getenv("LANGCHAIN_API_KEY", "")
    LANGCHAIN_PROJECT: str = os.getenv("LANGCHAIN_PROJECT", "customer_service_api")

    # Milvus
    MILVUS_URI: str = os.getenv("MILVUS_URI", "http://192.168.3.22:19530")

    # Model paths
    VL_MODEL_PATH: str = os.getenv("VL_MODEL_PATH", "/home/thomas/Downloads/models/Qwen2.5-Omni-7B")
    EMB_MODEL_PATH: str = os.getenv("EMB_MODEL_PATH", "/home/thomas/Downloads/models/Qwen3-Embedding-0.6B")
    RERANKER_MODEL_PATH: str = os.getenv("RERANKER_MODEL_PATH", "/home/thomas/Downloads/models/bge-reranker-v2-m3")

    # Collections
    RAG_COLLECTION: str = "multimodal_kb"
    KB_COLLECTION: str = "customer_service_kb"
    EMBED_DIM: int = 1024

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000


settings = Settings()
