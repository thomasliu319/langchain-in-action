"""
智能客服系统 API
融合多模态 RAG + ReAct Agent + 知识库管理
LangSmith 可观测 + SSE 流式 + StreamUI 风格页面

启动:
  python com/thomasliu/langchain/intelligent_customer_service_api/main.py
  # 或
  uvicorn com.thomasliu.langchain.intelligent_customer_service_api.main:app
"""
import os
import sys
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# ─── 确保包可导入（支持 python main.py 直接运行） ───
_ROOT = os.path.abspath(__file__)
for _ in range(5):
    _ROOT = os.path.dirname(_ROOT)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from com.thomasliu.langchain.intelligent_customer_service_api.config import settings

# ─── LangSmith 可观测（必须在 langchain 导入前设置） ───
os.environ["LANGCHAIN_TRACING_V2"] = settings.LANGCHAIN_TRACING_V2
os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT

from com.thomasliu.langchain.intelligent_customer_service_api.routes import rag, agent, kb

app = FastAPI(
    title="智能客服系统 API",
    description="多模态 RAG + ReAct Agent + 知识库管理",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(rag.router)
app.include_router(agent.router)
app.include_router(kb.router)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
