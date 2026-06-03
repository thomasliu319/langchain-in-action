from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.store.postgres import PostgresStore
from psycopg_pool import ConnectionPool

from app.config.settings import settings

#短记忆数据库连接池
short_term_pool = None
#长记忆数据库连接池
long_term_pool = None

#段记忆储存器实例
short_term_memory = None
#长记忆储存器实例
long_term_memory = None

#初始化 记忆  连接池
def init_memory_system():
    global short_term_pool, long_term_pool, short_term_memory, long_term_memory

    if short_term_pool is None:
        try:
            print("短记忆连接池 初始化中")
            short_term_pool = ConnectionPool(conninfo=settings.POSTGRES_SHORT_TERM_URL, min_size=2, max_size=10,
                                             kwargs={"autocommit": True, "prepare_threshold": 0, "keepalives": 1,
                                                     "keepalives_idle": 30, "keepalives_interval": 10,
                                                     "keepalives_count": 3})

            short_term_memory = PostgresSaver(short_term_pool)

            short_term_memory.setup()

            print("初始化短记忆连接池成功")

            #长记忆连接池
            long_term_pool = ConnectionPool(conninfo=settings.POSTGRES_LONG_TERM_URL, min_size=2, max_size=10,
                                            kwargs={"autocommit": True, "prepare_threshold": 0, "keepalives": 1,
                                                    "keepalives_idle": 30, "keepalives_interval": 10,
                                                    "keepalives_count": 3})

            long_term_memory = PostgresStore(long_term_pool)

            long_term_memory.setup()
            print("初始化长记忆连接池成功")
        except Exception as e:
            print(f"记忆系统初始化失败: {str(e)}")
            raise

#获取短记忆实例
def get_short_term_memory():
    global  short_term_pool
    if short_term_memory is None:
        init_memory_system()
    return short_term_memory


#获取长记忆 实例
def get_long_term_memory():
    global  long_term_pool
    if long_term_memory is None:
        init_memory_system()
    return long_term_memory