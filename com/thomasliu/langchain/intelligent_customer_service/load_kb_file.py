"""
加载指定 Markdown 文件到 Milvus 向量知识库
用法: conda run -n langchain-dev python load_kb_file.py
"""
import os
import re
import sys
from dotenv import load_dotenv
from pymilvus import MilvusClient
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

MODEL_PATH = "/home/thomas/Downloads/models/Qwen3-Embedding-0.6B"
MILVUS_URI = os.getenv("MILVUS_URI", "http://192.168.3.22:19530")
DIMENSION = 1024
COLLECTION_NAME = "customer_service_kb"

embed_model = SentenceTransformer(MODEL_PATH)
client = MilvusClient(uri=MILVUS_URI)


def strip_front_matter(text: str) -> str:
    return re.sub(r"^---.*?---\s*", "", text, flags=re.DOTALL)


def load_file(filepath: str) -> str:
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    content = strip_front_matter(content)
    content = re.sub(r"<[^>]+>", "", content)
    content = re.sub(r"\n{3,}", "\n\n", content)
    return content.strip()


def split_text(text: str, chunk_size: int = 300, chunk_overlap: int = 50) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_text(text)
    print(f"切分为 {len(chunks)} 个块")
    for i, chunk in enumerate(chunks, 1):
        print(f"\n块 {i}:")
        print(chunk[:120] + ("..." if len(chunk) > 120 else ""))
    return chunks


def init_collection():
    if not client.has_collection(COLLECTION_NAME):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            dimension=DIMENSION,
            auto_id=True,
            metric_type="COSINE",
        )
        print(f"创建集合 {COLLECTION_NAME}")


def insert_chunks(chunks: list[str], source_tag: str = "b01_quality"):
    embeddings = embed_model.encode(chunks).tolist()
    data = [
        {"vector": emb, "text": chunk, "source": source_tag}
        for emb, chunk in zip(embeddings, chunks)
    ]
    client.insert(COLLECTION_NAME, data)
    print(f"成功写入 {len(chunks)} 条向量到 {COLLECTION_NAME}")


if __name__ == "__main__":
    filepath = "/home/thomas/mySpace/langchain-in-action/3.2.5.3 B01买家问题 Buyer problems.md"
    text = load_file(filepath)
    print(f"读取文件: {filepath}")
    print(f"有效文本长度: {len(text)} 字符")
    print("--- 文本预览 ---")
    print(text[:300])
    print("...")

    chunks = split_text(text)
    if not chunks:
        print("No chunks to insert")
        sys.exit(0)

    init_collection()
    insert_chunks(chunks, source_tag="b01_quality")

    stats = client.query(COLLECTION_NAME, output_fields=["count(*)"])
    total = stats[0]["count(*)"] if stats else 0
    print(f"\n知识库总量: {total} 条")
