"""
向量长期记忆 — 替代 PostgresStore

基于 ChromaDB 的语义检索记忆系统。
保存时自动嵌入，查询时按语义相似度召回最相关片段。
"""
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

from app.config.settings import settings

# ==================== 常量 ====================

_EMBED_MODEL = settings.EMBED_MODEL_NAME
_TOP_K = settings.VECTOR_MEMORY_TOP_K
_PERSIST_DIR = settings.CHROMA_PERSIST_DIR


# 集合名称（替代 PostgresStore 的 namespace）
_COLLECTIONS = {
    "user_preferences": "user_preferences",
    "user_medical_history": "user_medical_history",
    "user_medical_records": "user_medical_records",
}


# ==================== 嵌入模型（全局单例） ====================

_embedder: Optional[SentenceTransformer] = None


def _get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(_EMBED_MODEL)
    return _embedder


# ==================== ChromaDB 客户端（全局单例） ====================

_chroma_client: Optional[chromadb.Client] = None


def _get_chroma() -> chromadb.Client:
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(
            path=_PERSIST_DIR,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _chroma_client


# ==================== 结果封装 ====================


class VectorMemoryItem:
    """类似 PostgresStore.search 返回的 item，有 .key 和 .value 属性"""

    def __init__(self, key: str, value: dict, distance: float = 0.0):
        self.key = key
        self.value = value
        self.distance = distance


# ==================== 向量记忆主类 ====================


class VectorMemory:
    """
    基于 ChromaDB 的长期记忆。

    替代 PostgresStore 的语义版：
    - save → 自动嵌入 + 存入 Chroma
    - search → 按 query 语义检索 top-K

    使用方式与 PostgresStore 兼容：
        memory = VectorMemory()
        memory.put(namespace, item_id, data)       # 保存
        results = memory.search(namespace)          # 语义检索（需要 query）
        results = memory.search(namespace, query="用户的症状是什么")  # 指定查询
    """

    def __init__(self):
        self._client = _get_chroma()
        self._embedder = _get_embedder()
        self._collections: dict[str, Any] = {}

    def _get_collection(self, namespace_key: str):
        """获取或创建 Chroma 集合"""
        if namespace_key not in self._collections:
            try:
                self._collections[namespace_key] = self._client.get_collection(namespace_key)
            except ValueError:
                self._collections[namespace_key] = self._client.create_collection(
                    name=namespace_key,
                    metadata={"hnsw:space": "cosine"},
                )
        return self._collections[namespace_key]

    def _make_key(self, namespace: tuple, item_id: str) -> str:
        """生成唯一键：namespace|user_id|item_id"""
        return "|".join(str(p) for p in namespace) + f"|{item_id}"

    def put(self, namespace: tuple, item_id: str, data: dict) -> None:
        """保存一条记录到向量存储。

        参数:
            namespace: (集合类型, user_id) 或 (集合类型, user_id, 子类型)
            item_id: 记录唯一 ID
            data: 数据字典（必须含 content 或其他可搜索字段）
        """
        # 解析命名空间
        ns_key = namespace[0] if len(namespace) >= 1 else "default"
        user_id = str(namespace[1]) if len(namespace) >= 2 else "default"

        collection = self._get_collection(ns_key)
        doc_id = self._make_key(namespace, item_id)

        # 构建搜索文本（用于嵌入）
        search_text = self._build_search_text(ns_key, data)

        # 添加时间戳
        if "timestamp" not in data:
            data["timestamp"] = datetime.now(timezone.utc).isoformat()

        # 元数据（用于过滤）
        metadata = {
            "user_id": user_id,
            "namespace": json.dumps(list(namespace)),
            "item_id": item_id,
        }
        # 限制 metadata 大小（Chroma 对 metadata 有大小限制）
        data_str = json.dumps(data, ensure_ascii=False)
        if len(data_str) > 1000:
            data["content"] = data.get("content", "")[:800]
            data_str = json.dumps(data, ensure_ascii=False)

        metadata["data_json"] = data_str[:2000]

        # 生成嵌入
        embedding = self._embedder.encode(search_text).tolist()

        # upsert（存在则覆盖）
        collection.upsert(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[search_text],
            metadatas=[metadata],
        )

    def search(
        self,
        namespace: tuple,
        query: Optional[str] = None,
        user_id: Optional[str] = None,
        k: int = 0,
    ) -> list[VectorMemoryItem]:
        """语义检索。

        参数:
            namespace: (集合类型,) 或 (集合类型, user_id) 等
            query: 检索查询（如果为 None，用默认查询获取最近记录）
            user_id: 用户 ID 过滤（如果 namespace 中未包含）
            k: 返回数量（默认用全局配置）

        返回:
            按相关性降序排列的 VectorMemoryItem 列表
        """
        ns_key = namespace[0] if len(namespace) >= 1 else "default"
        # 从 namespace 中提取 user_id
        ns_user_id = str(namespace[1]) if len(namespace) >= 2 else None
        effective_user_id = user_id or ns_user_id

        collection = self._get_collection(ns_key)
        k = k or _TOP_K

        # 构建过滤条件
        where = {}
        if effective_user_id:
            where["user_id"] = effective_user_id

        # 执行查询
        if query:
            query_embedding = self._embedder.encode(query).tolist()
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(k, 50),
                where=where,
            )
        else:
            # 无查询时，用空嵌入返回最近添加的条目
            # Chroma 不支持无嵌入查询，使用一个零向量
            dim = self._embedder.get_sentence_embedding_dimension()
            zero_emb = [0.0] * dim
            results = collection.query(
                query_embeddings=[zero_emb],
                n_results=min(k, 50),
                where=where,
            )

        items = []
        if results["ids"] and results["ids"][0]:
            for idx, doc_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][idx] if results["metadatas"] else {}
                distance = results["distances"][0][idx] if results["distances"] else 0.0

                # 反序列化 data
                data = {}
                data_raw = metadata.get("data_json", "{}")
                try:
                    data = json.loads(data_raw)
                except (json.JSONDecodeError, TypeError):
                    data = {"content": results["documents"][0][idx] if results["documents"] else ""}

                items.append(VectorMemoryItem(key=doc_id, value=data, distance=distance))

        return items

    def get(self, namespace: tuple, item_id: str) -> Optional[dict]:
        """按 ID 获取单条记录"""
        ns_key = namespace[0] if len(namespace) >= 1 else "default"
        collection = self._get_collection(ns_key)
        doc_id = self._make_key(namespace, item_id)

        try:
            result = collection.get(ids=[doc_id])
            if result["ids"]:
                metadata = result["metadatas"][0] if result["metadatas"] else {}
                data_raw = metadata.get("data_json", "{}")
                return json.loads(data_raw)
        except Exception:
            pass
        return None

    def delete(self, namespace: tuple, item_id: str) -> None:
        """删除一条记录"""
        ns_key = namespace[0] if len(namespace) >= 1 else "default"
        collection = self._get_collection(ns_key)
        doc_id = self._make_key(namespace, item_id)
        try:
            collection.delete(ids=[doc_id])
        except Exception:
            pass

    # ---------- 辅助方法 ----------

    def _build_search_text(self, ns_key: str, data: dict) -> str:
        """从数据构建可搜索文本"""
        parts = []
        if "key" in data and "value" in data:
            parts.append(f"{data['key']}: {data['value']}")
        if "category" in data and "content" in data:
            parts.append(f"{data['category']}: {data['content']}")
        if "content" in data and "category" not in data:
            parts.append(str(data["content"]))
        # 兜底：序列化整个 dict
        if not parts:
            parts.append(json.dumps(data, ensure_ascii=False))
        return " ".join(parts)

    def get_user_info_text(self, user_id: str, query: Optional[str] = None) -> str:
        """获取用户信息格式化的文本（向后兼容 get_user_long_memory）"""
        parts = []

        # 查询用户基本信息
        prefs = self.search(
            ("user_preferences", user_id),
            query=query or "用户基本信息",
            k=20,
        )
        if prefs:
            pref_lines = []
            seen = set()
            for item in prefs:
                key = item.value.get("key", "")
                val = item.value.get("value", "")
                if key and val and key not in seen:
                    seen.add(key)
                    pref_lines.append(f"{key}: {val}")
            if pref_lines:
                parts.append("【用户基本信息】\n" + "\n".join(pref_lines))

        # 查询医疗历史
        history = self.search(
            ("user_medical_history", user_id),
            query=query or "医疗记录",
            k=20,
        )
        if history:
            cat_map: dict[str, list[str]] = {}
            for item in history:
                cat = item.value.get("category", "其他")
                content = item.value.get("content", "")
                if cat not in cat_map:
                    cat_map[cat] = []
                if content:
                    cat_map[cat].append(content)

            hist_lines = []
            for cat, contents in cat_map.items():
                if len(contents) == 1:
                    hist_lines.append(f"{cat}: {contents[0]}")
                else:
                    items_text = "\n".join(f"{i+1}. {c}" for i, c in enumerate(contents))
                    hist_lines.append(f"{cat}:\n{items_text}")
            if hist_lines:
                parts.append("【医疗历史】\n" + "\n".join(hist_lines))

        # 查询诊断记录
        diag = self.search(
            ("user_medical_records", user_id, "diagnosis"),
            query=query or "诊断记录",
            k=5,
        )
        if diag:
            diag_lines = []
            for item in diag:
                content = item.value.get("content", "")
                if content:
                    diag_lines.append(content[:200])
            if diag_lines:
                parts.append("【诊断记录】\n" + "\n".join(diag_lines))

        return "\n\n".join(parts) if parts else ""

    def search_relevant(self, query: str, user_id: str, k: int = 5) -> str:
        """语义搜索最相关的记忆片段，返回文本"""
        results = []
        for ns_key in ["user_preferences", "user_medical_history", "user_medical_records"]:
            items = self.search(
                (ns_key, user_id),
                query=query,
                k=max(2, k // 2),
            )
            for item in items:
                text = self._build_search_text(ns_key, item.value)
                if text:
                    results.append(text)

        return "\n".join(results[:k]) if results else ""
