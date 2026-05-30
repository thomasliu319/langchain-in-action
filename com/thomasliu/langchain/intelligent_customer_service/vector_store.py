import os
from dotenv import load_dotenv
from pymilvus import MilvusClient
from sentence_transformers import SentenceTransformer
from document_loader import load_documents, split_text

load_dotenv()

MODEL_PATH = "/home/thomas/Downloads/models/Qwen3-Embedding-0.6B"
MILVUS_URI = os.getenv("MILVUS_URI", "http://192.168.3.22:19530")
DIMENSION = 1024
COLLECTION_NAME = "customer_service_kb"

model = SentenceTransformer(MODEL_PATH)
client = MilvusClient(uri=MILVUS_URI)


def _init_collection():
    if client.has_collection(COLLECTION_NAME):
        return
    client.create_collection(
        collection_name=COLLECTION_NAME,
        dimension=DIMENSION,
        auto_id=True,
        metric_type="COSINE",
    )


def store_vectors(chunks: list[str]):
    _init_collection()
    embeddings = model.encode(chunks).tolist()
    data = [
        {"vector": emb, "text": chunk, "source": "policy_doc"}
        for emb, chunk in zip(embeddings, chunks)
    ]
    client.insert(COLLECTION_NAME, data)
    print(f"成功存储 {len(chunks)} 条向量数据")


def query_knowledge_base(query_text: str, n_results: int = 3) -> list[str]:
    _init_collection()
    query_emb = model.encode(query_text).tolist()
    results = client.search(
        collection_name=COLLECTION_NAME,
        data=[query_emb],
        limit=n_results,
        output_fields=["text"],
    )
    docs = [r["entity"]["text"] for r in results[0]]
    print(f"\n--- 检索结果 (Top {n_results}) ---")
    for i, doc in enumerate(docs):
        print(f"[{i + 1}] {doc}")
    return docs


def drop_collection():
    if client.has_collection(COLLECTION_NAME):
        client.drop_collection(COLLECTION_NAME)
        print(f"集合 {COLLECTION_NAME} 已删除")


if __name__ == "__main__":
    raw_text = load_documents()
    chunks = split_text(raw_text)
    store_vectors(chunks)

    print("\n" + "=" * 40)
    query_knowledge_base("金牌会员有什么福利？")
