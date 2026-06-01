"""
知识库管理服务：封装向量存储 CRUD、Markdown 加载、模拟文档加载
"""
import os
import re
from pymilvus import MilvusClient
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..config import settings

# ─── 全局惰性加载 ───
_embed_model = None
_milvus = None


def _get_embed_model():
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer(settings.EMB_MODEL_PATH)
    return _embed_model


def _get_milvus():
    global _milvus
    if _milvus is None:
        _milvus = MilvusClient(uri=settings.MILVUS_URI)
    return _milvus


# ─── Collection 管理 ───

def list_collections() -> list[str]:
    return _get_milvus().list_collections()


def get_collection_info(name: str) -> dict:
    client = _get_milvus()
    exists = client.has_collection(name)
    count = 0
    if exists:
        stats = client.query(name, output_fields=["count(*)"])
        count = stats[0]["count(*)"] if stats else 0
    return {"name": name, "exists": exists, "count": count}


def drop_collection(name: str):
    client = _get_milvus()
    if client.has_collection(name):
        client.drop_collection(name)
        return {"status": "ok", "message": f"集合 {name} 已删除"}
    return {"status": "ok", "message": f"集合 {name} 不存在"}


# ─── 向量检索 ───

def query_knowledge_base(query_text: str, collection: str = None, n_results: int = 3) -> list[str]:
    collection = collection or settings.KB_COLLECTION
    client = _get_milvus()
    if not client.has_collection(collection):
        return []
    model = _get_embed_model()
    q_emb = model.encode(query_text).tolist()
    results = client.search(collection_name=collection, data=[q_emb], limit=n_results, output_fields=["text"])
    if not results or not results[0]:
        return []
    return [r["entity"]["text"] for r in results[0]]


# ─── 文档加载 ───

def load_policy_docs() -> list[str]:
    """返回预设的客服政策文档（模拟数据）"""
    text = (
        "【退换货政策】自签收之日起7天内，如产品存在质量问题，可申请退货退款。15天内可申请换货。"
        "超出15天但在保修期内，可享受免费维修服务。\n\n"
        "【发货说明】订单生成后48小时内发货。预售商品以页面标注时间为准。"
        "发货后您将收到短信通知，包含快递单号和查询链接。\n\n"
        "【会员权益】金牌会员享受双倍积分、生日礼包和专属客服。"
        "钻石会员额外享受免运费和优先发货权益。\n\n"
        "【保修政策】本产品享受1年有限保修。保修期内，非人为损坏的硬件故障免费维修。"
        "人为损坏、意外损坏或未经授权拆卸不在保修范围内。"
    )
    splitter = RecursiveCharacterTextSplitter(chunk_size=100, chunk_overlap=20, separators=["\n\n", "\n", ". ", " ", ""])
    chunks = splitter.split_text(text)
    return chunks if chunks else [text]


def load_markdown_file(filepath: str) -> str:
    """读取 Markdown 文件，去除 front-matter 和 HTML 标签"""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    content = re.sub(r"^---.*?---\s*", "", content, flags=re.DOTALL)
    content = re.sub(r"<[^>]+>", "", content)
    content = re.sub(r"\n{3,}", "\n\n", content)
    return content.strip()


def insert_text_chunks(chunks: list[str], collection: str = None, source_tag: str = "kb_doc"):
    collection = collection or settings.KB_COLLECTION
    client = _get_milvus()
    if not client.has_collection(collection):
        client.create_collection(collection_name=collection, dimension=settings.EMBED_DIM, auto_id=True, metric_type="COSINE")

    embeddings = _get_embed_model().encode(chunks).tolist()
    data = [{"vector": emb, "text": chunk, "source": source_tag} for emb, chunk in zip(embeddings, chunks)]
    client.insert(collection, data)
    return len(chunks)


def text_to_chunks(text: str, chunk_size: int = 300, overlap: int = 50) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=overlap, separators=["\n\n", "\n", ". ", " ", ""])
    return splitter.split_text(text)
