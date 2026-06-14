"""
Milvus 长期记忆存储 — 可切换替代 PostgresStore

兼容接口：
  - store.put(namespace: tuple, item_id: str, data: dict)
  - store.search(namespace: tuple, query_string: str | None = None, limit: int = 50) -> list[item]
  - store.setup()

注意：Milvus `client.query()` 在标量 VARCHAR 过滤上有 bug，
所有过滤查询统一走 `client.search()`（配合零向量 / 语义向量）。

嵌入模型由 `settings.EMBED_MODEL_NAME` 指定（默认本地路径），
向量维度从已加载的模型中自动检测。
"""
import json
from typing import Any, Optional

from pymilvus import MilvusClient, DataType

from app.config.settings import settings

_COLLECTION_NAME = "user_long_memory"


class MilvusStoreItem:
    """模拟 PostgresStore.search 返回的 item，有 .key 和 .value 属性"""

    def __init__(self, key: str, value: dict):
        self.key = key
        self.value = value


class MilvusStore:
    """
    基于 Milvus 的长期记忆存储。
    完全兼容 PostgresStore 的 put / search 接口。
    嵌入模型维度自动检测，首次 setup() 时确定。
    """

    def __init__(self, collection_name: str = _COLLECTION_NAME):
        self._collection_name = collection_name
        self._client: Optional[MilvusClient] = None
        self._embedder: Optional[Any] = None
        self._dim: Optional[int] = None
        self._setup_done = False

    # ---------- 底层连接 ----------

    def _get_client(self) -> MilvusClient:
        if self._client is None:
            self._client = MilvusClient(uri=settings.MILVUS_URI)
        return self._client

    def _get_embed_dim(self) -> int:
        """获取嵌入维度，懒加载模型后自动检测"""
        if self._dim is None:
            model = self._get_embedder()
            self._dim = model.get_embedding_dimension() if model else 384
        return self._dim

    def _zero_vector(self) -> list[float]:
        return [0.0] * self._get_embed_dim()

    def _get_embedder(self):
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                try:
                    self._embedder = SentenceTransformer(
                        settings.EMBED_MODEL_NAME,
                        device="cpu",
                    )
                    self._embedder.encode("test", normalize_embeddings=True)
                except Exception as e:
                    print(f"  [Milvus] 警告：嵌入模型加载失败（{e}）")
                    self._embedder = None
        return self._embedder

    def _embed(self, text: str) -> list[float]:
        model = self._get_embedder()
        if model is None:
            return self._zero_vector()
        try:
            return model.encode(text, normalize_embeddings=True).tolist()
        except Exception as e:
            print(f"  [Milvus] 嵌入失败，使用零向量（{e}）")
            return self._zero_vector()

    # ---------- 集合管理 ----------

    def setup(self):
        """创建或重建集合，确保维度与嵌入模型一致"""
        if self._setup_done:
            return
        client = self._get_client()

        dim = self._get_embed_dim()
        model_name = settings.EMBED_MODEL_NAME.split("/")[-1]
        collection_exists = client.has_collection(self._collection_name)

        if collection_exists:
            desc = client.describe_collection(self._collection_name)
            old_dim = desc.get("params", {}).get("dim", 0)
            if old_dim != dim:
                print(f"  [Milvus] 维度变化（{old_dim}→{dim}），重建集合 {self._collection_name}")
                client.drop_collection(self._collection_name)
                collection_exists = False

        if not collection_exists:
            schema = client.create_schema(auto_id=True, enable_dynamic_field=True)
            schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
            schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=dim)
            schema.add_field(field_name="namespace0", datatype=DataType.VARCHAR, max_length=128)
            schema.add_field(field_name="namespace1", datatype=DataType.VARCHAR, max_length=128)
            schema.add_field(field_name="item_key", datatype=DataType.VARCHAR, max_length=512)
            schema.add_field(field_name="item_id", datatype=DataType.VARCHAR, max_length=256)
            schema.add_field(field_name="data_json", datatype=DataType.VARCHAR, max_length=65535)

            index_params = client.prepare_index_params()
            index_params.add_index(field_name="vector", metric_type="COSINE")

            client.create_collection(
                collection_name=self._collection_name,
                schema=schema,
                index_params=index_params,
            )
            print(f"  [Milvus] 集合创建完成（dim={dim}, model={model_name}）")

        self._setup_done = True

    # ---------- 公共接口 ----------

    def put(self, namespace: tuple, item_id: str, data: dict):
        self.setup()
        client = self._get_client()

        key = "|".join(str(p) for p in namespace) + "|" + item_id
        data_json = json.dumps(data, ensure_ascii=False)
        search_text = f"{' '.join(str(p) for p in namespace)} {item_id} {data_json}"
        vector = self._embed(search_text)

        zv = self._zero_vector()
        old = client.search(
            collection_name=self._collection_name,
            data=[zv],
            filter=f'item_key == "{key}"',
            limit=10,
            output_fields=["id"],
        )
        ids = [h["id"] for h in old[0]]
        if ids:
            client.delete(self._collection_name, ids=ids)

        client.insert(self._collection_name, [{
            "vector": vector,
            "item_key": key,
            "namespace0": str(namespace[0]) if len(namespace) >= 1 else "",
            "namespace1": str(namespace[1]) if len(namespace) >= 2 else "",
            "item_id": item_id,
            "data_json": data_json,
        }])

        client.flush(self._collection_name)

    def search(
        self,
        namespace: tuple,
        query_string: Optional[str] = None,
        limit: int = 50,
    ) -> list[MilvusStoreItem]:
        self.setup()
        client = self._get_client()

        filter_parts = [f'namespace0 == "{str(namespace[0])}"']
        if len(namespace) >= 2:
            filter_parts.append(f'namespace1 == "{str(namespace[1])}"')
        filter_str = " and ".join(filter_parts)

        query_vec = self._embed(query_string) if query_string else self._zero_vector()

        results = client.search(
            collection_name=self._collection_name,
            data=[query_vec],
            filter=filter_str,
            limit=limit,
            output_fields=["item_id", "data_json"],
        )

        items = []
        for hits in results:
            for hit in hits:
                try:
                    value = json.loads(hit["entity"]["data_json"])
                except (json.JSONDecodeError, KeyError, TypeError):
                    value = {}
                items.append(MilvusStoreItem(
                    key=hit["entity"].get("item_id", ""),
                    value=value,
                ))
        return items
