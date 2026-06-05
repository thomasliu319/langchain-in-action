from langchain_openai import ChatOpenAI

from app.config.settings import settings



#模型初始化
def get_model():
    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
        temperature=0.3,
        extra_body={"thinking": {"type": "disabled"}},
    )