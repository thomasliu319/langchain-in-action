from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.config.settings import settings
# 创建 PostgreSQL 数据库连接引擎
postgres_engine = create_engine(settings.POSTGRES_SESSION_URL, pool_pre_ping=True, pool_recycle=3600)

#postgresql 会话工厂
PostgresSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=postgres_engine)

#ORM模型基类
PostgresBase = declarative_base()


#获取 PostgreSQL数据库会话
def get_postgres_db():
    """
        获取数据库会话
    """
    # 创建一个新的 PostgreSQL 数据库会话实例
    db = PostgresSessionLocal()
    try:
        # 将数据库会话对象返回给调用者（路由函数）
        yield db
    finally:
        # 关闭数据库会话，释放连接回连接池
        db.close()