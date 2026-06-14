"""
Redis 检查点存储器 — 替代 PostgresSaver

存储 LangGraph 线程检查点到 Redis，自动 TTL 过期。
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Iterator, Optional

import redis.asyncio as aredis
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    ChannelVersions,
    get_checkpoint_id,
)
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.checkpoint.serde.types import SendProtocol
from langgraph.errors import EmptyChannelError
from langgraph.managed.base import ManagedValueMapping
from langgraph.constants import TASKS
from pydantic import BaseModel
from redis import Redis as SyncRedis
from typing_extensions import Self

from app.config.settings import settings

# ==================== 常量 ====================

_CHECKPOINT_TTL = settings.REDIS_CHECKPOINT_TTL  # 秒
_SERIALIZER = JsonPlusSerializer()


# ==================== 检查点数据序列化 ====================


def _serialize(obj: Any) -> str:
    # dumps_typed 返回 (type_tag, bytes)，JSON 编码为 [tag, hex_data]
    tag, data = _SERIALIZER.dumps_typed(obj)
    return json.dumps([tag, data.hex()])


def _deserialize(raw: str) -> Any:
    tag, hex_data = json.loads(raw)
    return _SERIALIZER.loads_typed((tag, bytes.fromhex(hex_data)))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex


# ==================== Redis 检查点存储器 ====================


class RedisCheckpointer(BaseCheckpointSaver):
    """
    基于 Redis 的 LangGraph 检查点存储器。
    每个线程的检查点存储在 Redis 中，键自动 TTL 过期。
    """

    def __init__(self, redis_client: Optional[Any] = None):
        super().__init__(serde=_SERIALIZER)
        self._redis: Optional[Any] = None
        self._async_redis: Optional[Any] = None

    @classmethod
    def from_conn_str(cls, conn_str: str = "") -> Self:
        """工厂方法：从连接字符串创建实例"""
        instance = cls()
        instance._redis = SyncRedis.from_url(conn_str or settings.REDIS_URL, decode_responses=True)
        instance._async_redis = None
        return instance

    async def _get_async_redis(self):
        if self._async_redis is None:
            self._async_redis = aredis.from_url(settings.REDIS_URL, decode_responses=True)
        return self._async_redis

    def _get_sync_redis(self):
        if self._redis is None:
            self._redis = SyncRedis.from_url(settings.REDIS_URL, decode_responses=True)
        return self._redis

    # ---------- 键管理 ----------

    @staticmethod
    def _checkpoint_key(thread_id: str, checkpoint_ns: str, checkpoint_id: str) -> str:
        return f"cp:{thread_id}:{checkpoint_ns}:{checkpoint_id}"

    @staticmethod
    def _metadata_key(thread_id: str, checkpoint_ns: str, checkpoint_id: str) -> str:
        return f"cp_meta:{thread_id}:{checkpoint_ns}:{checkpoint_id}"

    @staticmethod
    def _latest_key(thread_id: str, checkpoint_ns: str) -> str:
        return f"cp_latest:{thread_id}:{checkpoint_ns}"

    # ---------- 公共接口（同步） ----------

    def get(self, config: dict) -> Optional[Checkpoint]:
        """获取检查点数据"""
        redis = self._get_sync_redis()
        thread_id = config["configurable"]["thread_id"]
        checkpoint_id = get_checkpoint_id(config)
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")

        if not checkpoint_id:
            # 获取最新的 checkpoint_id
            latest_key = self._latest_key(thread_id, checkpoint_ns)
            checkpoint_id = redis.get(latest_key)

        if not checkpoint_id:
            return None

        cp_key = self._checkpoint_key(thread_id, checkpoint_ns, checkpoint_id)
        raw = redis.get(cp_key)
        if not raw:
            return None
        return _deserialize(raw)

    def get_tuple(self, config: dict) -> Optional[CheckpointTuple]:
        """获取检查点元组"""
        redis = self._get_sync_redis()
        thread_id = config["configurable"]["thread_id"]
        checkpoint_id = get_checkpoint_id(config)
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")

        if not checkpoint_id:
            latest_key = self._latest_key(thread_id, checkpoint_ns)
            checkpoint_id = redis.get(latest_key)

        if not checkpoint_id:
            return None

        cp_key = self._checkpoint_key(thread_id, checkpoint_ns, checkpoint_id)
        meta_key = self._metadata_key(thread_id, checkpoint_ns, checkpoint_id)

        raw_cp = redis.get(cp_key)
        raw_meta = redis.get(meta_key)

        if not raw_cp:
            return None

        checkpoint = _deserialize(raw_cp)
        metadata = _deserialize(raw_meta) if raw_meta else {}

        config_val = {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint_id,
            }
        }

        return CheckpointTuple(
            config=config_val,
            checkpoint=checkpoint,
            metadata=metadata,
            parent_config=None,
        )

    def list(
        self,
        config: Optional[dict] = None,
        *,
        filter: Optional[dict[str, Any]] = None,
        before: Optional[dict] = None,
        limit: Optional[int] = None,
    ) -> Iterator[CheckpointTuple]:
        """列出线程的检查点"""
        redis = self._get_sync_redis()
        if config is None:
            return iter([])

        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")

        # 使用 scan 模式获取该线程的所有检查点
        pattern = f"cp:{thread_id}:{checkpoint_ns}:*"
        cursor = 0
        items = []
        while True:
            cursor, keys = redis.scan(cursor, match=pattern, count=100)
            for key in keys:
                parts = key.split(":")
                if len(parts) >= 4:
                    cid = parts[-1]
                    raw = redis.get(key)
                    if raw:
                        meta_key = self._metadata_key(thread_id, checkpoint_ns, cid)
                        raw_meta = redis.get(meta_key)
                        items.append(
                            CheckpointTuple(
                                config={
                                    "configurable": {
                                        "thread_id": thread_id,
                                        "checkpoint_ns": checkpoint_ns,
                                        "checkpoint_id": cid,
                                    }
                                },
                                checkpoint=_deserialize(raw),
                                metadata=_deserialize(raw_meta) if raw_meta else {},
                                parent_config=None,
                            )
                        )
            if cursor == 0:
                break

        # 按时间倒序（假设 checkpoint_id 是时间戳排序的）
        items.sort(key=lambda x: x.config["configurable"]["checkpoint_id"], reverse=True)
        if limit:
            items = items[:limit]
        return iter(items)

    def put(
        self,
        config: dict,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> dict:
        """保存检查点"""
        redis = self._get_sync_redis()

        configurable = config["configurable"].copy()
        thread_id = configurable.pop("thread_id")
        checkpoint_ns = configurable.pop("checkpoint_ns", "")
        checkpoint_id = configurable.pop("checkpoint_id", None) or _new_id()

        next_config = {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint_id,
            }
        }

        # 保存检查点数据
        cp_key = self._checkpoint_key(thread_id, checkpoint_ns, checkpoint_id)
        meta_key = self._metadata_key(thread_id, checkpoint_ns, checkpoint_id)
        latest_key = self._latest_key(thread_id, checkpoint_ns)

        redis.setex(cp_key, _CHECKPOINT_TTL, _serialize(checkpoint))
        redis.setex(meta_key, _CHECKPOINT_TTL, _serialize(metadata))

        # 更新最新检查点指针
        redis.setex(latest_key, _CHECKPOINT_TTL, checkpoint_id)

        return next_config

    # ---------- 异步接口（LangGraph 内部使用） ----------

    async def aput(
        self,
        config: dict,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> dict:
        redis = await self._get_async_redis()
        configurable = config["configurable"].copy()
        thread_id = configurable.pop("thread_id")
        checkpoint_ns = configurable.pop("checkpoint_ns", "")
        checkpoint_id = configurable.pop("checkpoint_id", None) or _new_id()

        next_config = {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint_id,
            }
        }

        cp_key = self._checkpoint_key(thread_id, checkpoint_ns, checkpoint_id)
        meta_key = self._metadata_key(thread_id, checkpoint_ns, checkpoint_id)
        latest_key = self._latest_key(thread_id, checkpoint_ns)

        await redis.setex(cp_key, _CHECKPOINT_TTL, _serialize(checkpoint))
        await redis.setex(meta_key, _CHECKPOINT_TTL, _serialize(metadata))
        await redis.setex(latest_key, _CHECKPOINT_TTL, checkpoint_id)

        return next_config

    def put_writes(
        self,
        config: dict,
        writes: list[tuple[str, Any]],
        task_id: str,
    ) -> None:
        if not writes:
            return
        redis = self._get_sync_redis()
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = config["configurable"]["checkpoint_id"]
        writes_key = f"cp_writes:{thread_id}:{checkpoint_ns}:{checkpoint_id}:{task_id}"
        redis.setex(writes_key, _CHECKPOINT_TTL, _serialize(writes))

    async def aput_writes(
        self,
        config: dict,
        writes: list[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        if not writes:
            return
        redis = await self._get_async_redis()
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = config["configurable"]["checkpoint_id"]
        writes_key = f"cp_writes:{thread_id}:{checkpoint_ns}:{checkpoint_id}:{task_id}"
        await redis.setex(writes_key, _CHECKPOINT_TTL, _serialize(writes))

    async def aget_tuple(self, config: dict) -> Optional[CheckpointTuple]:
        redis = await self._get_async_redis()
        thread_id = config["configurable"]["thread_id"]
        checkpoint_id = get_checkpoint_id(config)
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")

        if not checkpoint_id:
            latest_key = self._latest_key(thread_id, checkpoint_ns)
            checkpoint_id = await redis.get(latest_key)

        if not checkpoint_id:
            return None

        cp_key = self._checkpoint_key(thread_id, checkpoint_ns, checkpoint_id)
        meta_key = self._metadata_key(thread_id, checkpoint_ns, checkpoint_id)

        raw_cp = await redis.get(cp_key)
        raw_meta = await redis.get(meta_key)

        if not raw_cp:
            return None

        checkpoint = _deserialize(raw_cp)
        metadata = _deserialize(raw_meta) if raw_meta else {}

        config_val = {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint_id,
            }
        }

        return CheckpointTuple(
            config=config_val,
            checkpoint=checkpoint,
            metadata=metadata,
            parent_config=None,
        )

    async def alist(
        self,
        config: Optional[dict] = None,
        *,
        filter: Optional[dict[str, Any]] = None,
        before: Optional[dict] = None,
        limit: Optional[int] = None,
    ) -> AsyncIterator[CheckpointTuple]:
        if config is None:
            return

        redis = await self._get_async_redis()
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        pattern = f"cp:{thread_id}:{checkpoint_ns}:*"

        cursor = 0
        items = []
        while True:
            cursor, keys = await redis.scan(cursor, match=pattern, count=100)
            for key in keys:
                parts = key.split(":")
                if len(parts) >= 4:
                    cid = parts[-1]
                    raw = await redis.get(key)
                    if raw:
                        meta_key = self._metadata_key(thread_id, checkpoint_ns, cid)
                        raw_meta = await redis.get(meta_key)
                        items.append(
                            CheckpointTuple(
                                config={
                                    "configurable": {
                                        "thread_id": thread_id,
                                        "checkpoint_ns": checkpoint_ns,
                                        "checkpoint_id": cid,
                                    }
                                },
                                checkpoint=_deserialize(raw),
                                metadata=_deserialize(raw_meta) if raw_meta else {},
                                parent_config=None,
                            )
                        )
            if cursor == 0:
                break

        items.sort(key=lambda x: x.config["configurable"]["checkpoint_id"], reverse=True)
        if limit:
            items = items[:limit]
        for item in items:
            yield item

    async def aget(self, config: dict) -> Optional[Checkpoint]:
        redis = await self._get_async_redis()
        thread_id = config["configurable"]["thread_id"]
        checkpoint_id = get_checkpoint_id(config)
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")

        if not checkpoint_id:
            latest_key = self._latest_key(thread_id, checkpoint_ns)
            checkpoint_id = await redis.get(latest_key)

        if not checkpoint_id:
            return None

        cp_key = self._checkpoint_key(thread_id, checkpoint_ns, checkpoint_id)
        raw = await redis.get(cp_key)
        if not raw:
            return None
        return _deserialize(raw)

    def setup(self) -> None:
        """无需建表，Redis 自动处理"""
        pass
