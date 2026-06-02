from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


from app.config.settings import settings

#创建 mysql 数据库连接引擎
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, pool_recycle=3600)

#创建数据库会话工程
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

#创建 ORM 模型基类
Base = declarative_base()

#获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()