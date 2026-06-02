from sqlalchemy import Column, Integer, String, func, DateTime

from app.database.mysql import Base


#用户模型

class User(Base):
    # 表名  ORM框架需要指定
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    username = Column(String(100), unique=True,index=True,nullable=False)

    email = Column(String(100), unique=True, index=True, nullable=False)

    password_hash = Column(String(100), nullable=False)

    created_at = Column(DateTime(timezone=True),server_default=func.now())

    updated_at = Column(DateTime(timezone=True),server_default=func.now(),server_onupdate=func.now())