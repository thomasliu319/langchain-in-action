"""
记忆系统：短期记忆(Redis + TTL) + 长期记忆(PostgreSQL / Milvus 可切换)

架构：
- 短期：自定义 RedisCheckpointer（LangGraph 线程检查点，自动 TTL 过期）
- 长期：PostgresStore 或 MilvusStore（由 LONG_TERM_MEMORY_TYPE 控制）
"""
import traceback
from typing import Any, Optional

from app.config.settings import settings
from app.database.redis_checkpointer import RedisCheckpointer

# ==================== 全局实例 ====================

_short_term_memory: Optional[RedisCheckpointer] = None
_long_term_memory: Any = None
_long_term_pool: Any = None


# ==================== 初始化 ====================


def _init_postgres_store():
    """初始化 PostgreSQL 长期记忆"""
    global _long_term_memory, _long_term_pool
    from langgraph.store.postgres import PostgresStore
    from psycopg_pool import ConnectionPool

    _long_term_pool = ConnectionPool(
        conninfo=settings.POSTGRES_LONG_TERM_URL,
        min_size=2, max_size=10,
        kwargs={
            "autocommit": True, "prepare_threshold": 0,
            "keepalives": 1, "keepalives_idle": 30,
            "keepalives_interval": 10, "keepalives_count": 3,
        },
    )
    _long_term_memory = PostgresStore(_long_term_pool)
    _long_term_memory.setup()
    print("  \u2705 PostgreSQL \u957f\u671f\u8bb0\u5fc6\u5c31\u7eea")


def _init_milvus_store():
    """初始化 Milvus 长期记忆"""
    global _long_term_memory
    from app.database.milvus_store import MilvusStore

    _long_term_memory = MilvusStore()
    _long_term_memory.setup()
    print(f"  \u2705 Milvus \u957f\u671f\u8bb0\u5fc6\u5c31\u7eea\uff08URI: {settings.MILVUS_URI}\uff09")


def init_memory_system():
    """初始化记忆系统（启动时调用一次）"""
    global _short_term_memory, _long_term_memory, _long_term_pool

    if _short_term_memory is not None and _long_term_memory is not None:
        return

    print("\U0001f504 \u521d\u59cb\u5316\u8bb0\u5fc6\u7cfb\u7edf...")

    # 1. Redis 短期记忆
    try:
        _short_term_memory = RedisCheckpointer.from_conn_str(settings.REDIS_URL)
        print(f"  \u2705 Redis \u77ed\u671f\u8bb0\u5fc6\u5c31\u7eea\uff08TTL: {settings.REDIS_CHECKPOINT_TTL}s\uff09")
    except Exception as e:
        print(f"  \u274c Redis \u77ed\u671f\u8bb0\u5fc6\u521d\u59cb\u5316\u5931\u8d25\uff1a{e}")
        raise

    # 2. 长期记忆（按配置选择后端）
    try:
        backend = settings.LONG_TERM_MEMORY_TYPE
        if backend == "milvus":
            _init_milvus_store()
        elif backend == "postgres":
            _init_postgres_store()
        else:
            raise ValueError(f"\u672a\u77e5\u7684\u957f\u671f\u8bb0\u5fc6\u540e\u7aef: {backend}\uff0c\u8bf7\u8bbe\u7f6e LONG_TERM_MEMORY_TYPE=postgres \u6216 milvus")
    except Exception as e:
        print(f"  \u274c \u957f\u671f\u8bb0\u5fc6\u521d\u59cb\u5316\u5931\u8d25\uff1a{e}")
        raise

    print("  \u2705 \u8bb0\u5fc6\u7cfb\u7edf\u521d\u59cb\u5316\u5b8c\u6210")


# ==================== 短期记忆（Redis 检查点）====================


def get_short_term_memory():
    """获取 LangGraph 检查点存储器（Redis 后端，自动 TTL 过期）"""
    global _short_term_memory
    if _short_term_memory is None:
        init_memory_system()
    return _short_term_memory


# ==================== 长期记忆（PostgreSQL / Milvus）====================


def get_long_term_memory():
    """获取长期记忆实例（按配置返回 PostgresStore 或 MilvusStore）"""
    global _long_term_memory
    if _long_term_memory is None:
        init_memory_system()
    return _long_term_memory


# ==================== 兼容接口 ====================


def save_user_long_memory(
    store: Any,
    namespace: tuple,
    item_id: str,
    data: dict,
):
    """保存用户数据到长期记忆。
    
    store.put(namespace, item_id, data) — 兼容 PostgresStore 和 MilvusStore。
    """
    if store is None:
        store = get_long_term_memory()
    try:
        store.put(namespace, item_id, data)
    except Exception as e:
        print(f"保存长记忆出错: {e}")
        print(traceback.format_exc())


def get_user_long_memory(
    user_id: str,
    store: Any = None,
    query: Optional[str] = None,
) -> str:
    """
    获取用户长记忆的格式化文本。
    
    从长期存储中检索用户基本信息和医疗历史，拼接为文本供 LLM 使用。
    兼容 PostgresStore 和 MilvusStore 两种后端。
    """
    if store is None:
        store = get_long_term_memory()

    user_info = []

    try:
        # 用户基本信息
        preferences = store.search(("user_preferences", user_id))
        if preferences:
            pref_dict = {}
            for item in preferences:
                key_parts = str(item.key).split("|") if "|" in str(item.key) else [str(item.key)]
                item_id = key_parts[-1] if key_parts else str(item.key)
                pref_dict[item_id] = item.value

            pref_text = "\n".join(
                f"{v.get('key')}: {v.get('value')}"
                for v in pref_dict.values()
            )
            user_info.append("【用户基本信息】\n" + pref_text)

        # 医疗历史
        medical_history = store.search(("user_medical_history", user_id))
        if medical_history:
            cat_map = {}
            for item in medical_history:
                cat = item.value.get("category", "unknown")
                content = item.value.get("content", "")
                if cat not in cat_map:
                    cat_map[cat] = []
                cat_map[cat].append(content)

            hist_lines = []
            for cat, contents in cat_map.items():
                if len(contents) == 1:
                    hist_lines.append(f"{cat}: {contents[0]}")
                else:
                    items_text = "\n".join(f"{i+1}. {c}" for i, c in enumerate(contents))
                    hist_lines.append(f"{cat}:\n{items_text}")

            user_info.append("【医疗历史】\n" + "\n".join(hist_lines))

    except Exception as e:
        print(f"获取长记忆出错: {e}")
        print(traceback.format_exc())

    return "\n\n".join(user_info) if user_info else ""
