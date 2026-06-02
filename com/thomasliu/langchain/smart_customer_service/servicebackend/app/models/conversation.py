from sqlalchemy import String, Integer, Column, TEXT, DateTime, func

from app.database.postgresql import PostgresBase


#会话列表模型 储存用户的会话列表信息
class Conversation(PostgresBase):
    __tablename__ = "conversations"

    id = Column(String(100), primary_key=True, index=True)

    user_id = Column(Integer, nullable=False,index=True)

    title = Column(String(255), nullable=False)

    last_message = Column(TEXT)

    last_active = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    created_at = Column(DateTime(timezone=True), server_default=func.now())

