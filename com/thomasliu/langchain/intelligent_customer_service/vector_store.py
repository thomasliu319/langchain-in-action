import chromadb
from chromadb.utils import embedding_functions
from document_loader import load_documents, split_text

# 初始化 ChromaDB 客户端（持久化存储到本地）
chroma_client = chromadb.PersistentClient(path="./chroma_db")

# 直接加载已下载好的模型
MODEL_PATH = "/home/thomas/Downloads/models/Qwen3-Embedding-0.6B"
emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=MODEL_PATH)


def store_vectors(chunks: list[str], collection_name: str = "customer_service_kb"):
    collection = chroma_client.get_or_create_collection(
        name=collection_name,
        embedding_function=emb_fn,
    )
    ids = [f"id_{i}" for i in range(len(chunks))]
    metadatas = [{"source": "policy_doc"} for _ in chunks]
    collection.add(documents=chunks, metadatas=metadatas, ids=ids)
    print(f"成功存储 {len(chunks)} 条向量数据")
    return collection


def query_knowledge_base(query_text: str, n_results: int = 3) -> list[str]:
    collection = chroma_client.get_collection(
        name="customer_service_kb",
        embedding_function=emb_fn,
    )
    results = collection.query(query_texts=[query_text], n_results=n_results)
    retrieved_docs = results["documents"][0]
    print(f"\n--- 检索结果 (Top {n_results}) ---")
    for i, doc in enumerate(retrieved_docs):
        print(f"[{i + 1}] {doc}")
    return retrieved_docs


if __name__ == "__main__":
    raw_text = load_documents()
    chunks = split_text(raw_text)
    collection = store_vectors(chunks)

    print("\n" + "=" * 40)
    query_knowledge_base("金牌会员有什么福利？")
