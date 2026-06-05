import os

import uvicorn
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.api import auth, chat, conversations
from app.config.settings import settings
from app.database.postgresql import PostgresBase, postgres_engine
#必须要导入模型 才能生存 表
from app.models.conversation import Conversation
from app.models.medical_document import MedicalDocument

__all__ = [ "Conversation", "MedicalDocument"]


#初始化 LangSmith
os.environ["LANGCHAIN_TRACING_V2"] = str(settings.LANGCHAIN_TRACING_V2).lower()
os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT

try:
    # 根据 模型定义 创建表（没有则创建）
    PostgresBase.metadata.create_all(bind=postgres_engine)
    print("ok postgresql 数据库表创建成功")
except Exception as e:
    print(f"postgresql数据库表创建失败:{e}")



#创建 FastAPI应用
app = FastAPI(title="x健身教练", description="基于 langchain 1.x ", version="1.0.0", )


#配置 跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#注册路由
app.include_router(auth.router, prefix="/auth", tags=["登录注册"])
app.include_router(conversations.router, prefix="/conversations", tags=["会话管理"])
app.include_router(chat.router, prefix="/chat", tags=["AI对话"])



@app.get("/")
async def root():
    """根路径"""
    return {
        "messages":"renpho健身教练",
        "version":"1.0.0",
        "author":"thomas",
        "docs":"/docs"
    }

if __name__ == "__main__":
    print("x健身教练 API 启动中")

    print(f"访问地址: http://{settings.HOST}:{settings.PORT}")
    print(f"文档地址: http://{settings.HOST}:{settings.PORT}/docs")

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )