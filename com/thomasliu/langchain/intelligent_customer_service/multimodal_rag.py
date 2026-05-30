"""
多模态 PDF 识别与向量化工具
- 文字内容 → Qwen3-Embedding-0.6B 嵌入
- 图片/表格 → Qwen2.5-VL-7B-Instruct 理解
- 结果清洗 → 统一格式 → 存入 Milvus

用法:
  python multimodal_rag.py                                          # 处理默认 PDF
  python multimodal_rag.py /path/to/file.pdf --collection my_kb
"""
import os
import json
import time
import sys
import argparse
import warnings
from typing import Optional
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from PIL import Image
from pdf2image import convert_from_path

load_dotenv()

warnings.filterwarnings("ignore")

MODEL_PATH_VL = "/home/thomas/Downloads/models/Qwen2.5-VL-7B-Instruct"
MODEL_PATH_EMB = "/home/thomas/Downloads/models/Qwen3-Embedding-0.6B"
MILVUS_URI = os.getenv("MILVUS_URI", "http://192.168.3.22:19530")
COLLECTION_NAME = "multimodal_kb"
EMBED_DIM = 1024

_llm = None
_processor = None
_embed_model = None
_milvus = None


def get_vl_model():
    global _llm, _processor
    if _llm is None:
        from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
        import torch
        print("加载 Qwen2.5-VL-7B-Instruct ...")
        _llm = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            MODEL_PATH_VL, torch_dtype=torch.float16, device_map="auto",
        )
        _processor = AutoProcessor.from_pretrained(MODEL_PATH_VL)
    return _llm, _processor


def get_embed_model():
    global _embed_model
    if _embed_model is None:
        from sentence_transformers import SentenceTransformer
        print("加载 Qwen3-Embedding-0.6B ...")
        _embed_model = SentenceTransformer(MODEL_PATH_EMB)
    return _embed_model


def get_milvus():
    global _milvus
    if _milvus is None:
        from pymilvus import MilvusClient
        _milvus = MilvusClient(uri=MILVUS_URI)
    return _milvus


# ─── PDF → IMG ───

def pdf_to_images(pdf_path: str, dpi: int = 150, max_size: int = 1280) -> list[Image.Image]:
    images = convert_from_path(pdf_path, dpi=dpi)
    result = []
    for img in images:
        img.thumbnail((max_size, max_size), Image.LANCZOS)
        result.append(img)
    return result


# ─── Qwen2.5-VL 识别 ───

def analyze_page(image: Image.Image) -> str:
    llm, processor = get_vl_model()
    prompt = (
        "You are an OCR assistant. Extract ALL visible text from this product document page. "
        "Include: product name, model number, specifications, instructions, "
        "button labels, diagrams, tables, and any other text. "
        "Preserve original language and formatting. Be thorough and complete."
    )
    messages = [
        {"role": "user", "content": [
            {"type": "image", "image": image},
            {"type": "text", "text": prompt},
        ]}
    ]
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = processor(text=[text], images=[image], padding=True, return_tensors="pt")
    inputs = {k: v.to(llm.device) for k, v in inputs.items()}

    generated_ids = llm.generate(**inputs, max_new_tokens=2048)
    input_len = inputs["input_ids"].shape[1]
    response = processor.decode(generated_ids[0][input_len:], skip_special_tokens=True)
    return response.strip()


# ─── 清洗与格式化 ───

def clean_text(raw: str) -> str:
    lines = raw.split("\n")
    cleaned = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def structure_content(raw: str, source: str, page: int) -> dict:
    return {
        "source": source,
        "page": page,
        "raw_text": raw,
        "clean_text": clean_text(raw),
        "content_type": "document_page",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


# ─── BM25 索引（本地构建，用于混合检索） ───

_bm25 = None
_bm25_corpus = None
_bm25_idx = {}  # text → index mapping for O(1) lookup


def _build_bm25_index(collection_name: str):
    global _bm25, _bm25_corpus, _bm25_idx
    from rank_bm25 import BM25Okapi
    client = get_milvus()
    docs = client.query(
        collection_name,
        output_fields=["text"],
        filter='chunk_label == "semantic_chunk"',
        limit=10000,
    )
    _bm25_corpus = [d["text"] for d in docs]
    _bm25_idx = {t: i for i, t in enumerate(_bm25_corpus)}
    _bm25 = BM25Okapi([t.split() for t in _bm25_corpus])
    print(f"BM25 索引已构建: {len(_bm25_corpus)} 条")


# ─── Reranker ───

_reranker = None


def get_reranker():
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder
        model_path = "/home/thomas/Downloads/models/bge-reranker-v2-m3"
        print("加载 BGE-Reranker ...")
        _reranker = CrossEncoder(model_path, device="cpu")
    return _reranker


# ─── 分块 & 嵌入 ───

def chunk_text(text: str, chunk_size: int = 300, overlap: int = 30) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_text(text)
    return chunks if chunks else [text]


def embed_chunks(chunks: list[str]) -> list[list[float]]:
    model = get_embed_model()
    return model.encode(chunks).tolist()


# ─── 存入 Milvus ───

def init_milvus(collection_name: str):
    client = get_milvus()
    if not client.has_collection(collection_name):
        client.create_collection(
            collection_name=collection_name,
            dimension=EMBED_DIM,
            auto_id=True,
            metric_type="COSINE",
        )
        print(f"创建集合: {collection_name}")
    return client


def store_to_milvus(entries: list[dict], collection_name: str):
    client = init_milvus(collection_name)
    for entry in entries:
        res = client.insert(collection_name, entry)
        if res.get("insert_count", 0) == 0:
            print(f"  ⚠ 插入失败: chunk_{entry.get('chunk_index')}")
    client.flush(collection_name)
    print(f"写入 {len(entries)} 条向量 → {collection_name}")


# ─── 完整流程 ───

def process_pdf(
    pdf_path: str,
    collection_name: str = COLLECTION_NAME,
    dpi: int = 150,
):
    filename = os.path.basename(pdf_path)
    print(f"\n{'='*50}")
    print(f"处理: {filename}")

    print("1/4 转换 PDF → 图片 ...")
    images = pdf_to_images(pdf_path, dpi=dpi)
    print(f"   共 {len(images)} 页")

    all_entries = []
    for i, img in enumerate(images):
        print(f"2/4 第{i+1}页 Qwen2.5-VL 识别 ...")
        t0 = time.time()
        raw = analyze_page(img)
        t1 = time.time()
        print(f"   耗时: {t1-t0:.1f}s, 输出: {len(raw)} 字符")

        print(f"3/4 清洗 & 语义分块 & 嵌入 ...")
        structured = structure_content(raw, filename, i + 1)
        clean = structured["clean_text"]

        # 整页大块（全局上下文）
        full_emb = embed_chunks([clean])[0]
        all_entries.append({
            "vector": full_emb,
            "text": clean,
            "source": filename,
            "page": i + 1,
            "chunk_index": 0,
            "chunk_label": "full_page",
            "content_type": "document_page",
            "timestamp": structured["timestamp"],
        })

        # 语义小块（按段落切分，聚焦检索）
        chunks = chunk_text(clean)
        embeddings = embed_chunks(chunks)
        for j, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            all_entries.append({
                "vector": emb,
                "text": chunk,
                "source": filename,
                "page": i + 1,
                "chunk_index": j + 1,
                "chunk_label": "semantic_chunk",
                "content_type": "document_page",
                "timestamp": structured["timestamp"],
            })

    print(f"4/4 存入 Milvus ({len(all_entries)} 条向量) ...")
    store_to_milvus(all_entries, collection_name)

    print(f"\n✓ 完成! 共 {len(all_entries)} 条向量")
    return all_entries


def query_kb(
    query: str,
    collection_name: str = COLLECTION_NAME,
    top_k: int = 50,
    final_k: int = 3,
    alpha: float = 0.5,
):
    """
    混合检索 (Vector + BM25) → Rerank → Top final_k

    Args:
        query: 查询文本
        collection_name: Milvus 集合名
        top_k: 粗排数量
        final_k: 精排后返回数量
        alpha: 向量与 BM25 权重 (0=纯BM25, 1=纯向量)
    """
    import numpy as np

    client = get_milvus()
    model = get_embed_model()

    _build_bm25_index(collection_name)
    bm25, corpus, idx_map = _bm25, _bm25_corpus, _bm25_idx
    if not corpus:
        print("知识库为空")
        return []

    # 1. 向量检索 TopK
    q_emb = model.encode(query).tolist()
    vec_results = client.search(
        collection_name=collection_name,
        data=[q_emb],
        limit=top_k,
        output_fields=["text", "source", "chunk_index"],
        filter='chunk_label == "semantic_chunk"',
    )

    # 2. BM25 打分
    bm25_scores = np.array(bm25.get_scores(query.split()))
    bm25_max = bm25_scores.max()
    bm25_max = bm25_max if bm25_max > 0 else 1.0

    # 3. 合并候选集（向量 + BM25 加权融合）
    candidates = {}
    for r in vec_results[0]:
        text = r["entity"]["text"]
        vec_score = r["distance"]
        corpus_i = idx_map.get(text, -1)
        bm25_norm = bm25_scores[corpus_i] / bm25_max if corpus_i >= 0 else 0
        combined = alpha * vec_score + (1 - alpha) * bm25_norm
        candidates[text] = {
            "score": combined,
            "source": r["entity"]["source"],
            "chunk_index": r["entity"]["chunk_index"],
            "text": text,
        }

    # 加入 BM25 高匹配但向量未召回的结果
    bm25_top = bm25_scores.argsort()[::-1][:top_k]
    for i in bm25_top:
        if bm25_scores[i] <= 0:
            break
        text = corpus[i]
        if text not in candidates:
            bm25_norm = bm25_scores[i] / bm25_max
            candidates[text] = {
                "score": (1 - alpha) * bm25_norm,
                "source": "BM25",
                "chunk_index": -1,
                "text": text,
            }

    # 4. 粗排取 TopK
    ranked = sorted(candidates.values(), key=lambda x: x["score"], reverse=True)[:top_k]

    # 5. Rerank 精排
    reranker = get_reranker()
    pairs = [[query, r["text"]] for r in ranked]
    rerank_scores = reranker.predict(pairs)
    for i, score in enumerate(rerank_scores):
        ranked[i]["rerank_score"] = float(score)

    final = sorted(ranked, key=lambda x: x["rerank_score"], reverse=True)[:final_k]

    print(f"\n查询: {query}\n")
    for r in final:
        print(f"  [rerank={r['rerank_score']:.3f}, hybrid={r['score']:.3f}]")
        print(f"  {r['text'][:300]}")
        print()
    return final


def generate_answer(query: str, chunks: list[dict]) -> str:
    """
    基于检索结果生成带引用的回答（流式输出）

    Args:
        query: 用户问题
        chunks: query_kb 返回的语义块列表（带 text, chunk_index, source）
    """
    from openai import OpenAI

    context_parts = []
    for i, c in enumerate(chunks):
        context_parts.append(f"[引用{i+1}] {c['text']}")
    context = "\n\n".join(context_parts)

    system_prompt = (
        "你是一个基于知识库的问答助手。\n"
        "规则：\n"
        "1. 只依据上方提供的上下文回答，不要编造信息。\n"
        "2. 如果上下文不足以回答，请明确说「上下文未提及」。\n"
        "3. 在回答中标注引用来源，格式为 [引用1]、[引用2] 等。\n"
        "4. 引用编号必须与上下文中的 [引用N] 对应。"
    )
    user_prompt = f"上下文：\n{context}\n\n问题：{query}"

    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com"),
    )
    stream = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "deepseek-v4-pro"),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
        stream=True,
        extra_body={"thinking": {"type": "disabled"}},
    )
    collected = []
    for chunk in stream:
        delta = chunk.choices[0].delta
        token = delta.content or ""
        if token:
            collected.append(token)
            print(token, end="", flush=True)
    print()
    return "".join(collected)


# ─── CLI ───

def main():
    parser = argparse.ArgumentParser(description="多模态 PDF → Milvus 管道")
    parser.add_argument("pdf", nargs="?", default=None,
                        help="PDF 文件路径 (默认: 使用预设文件)")
    parser.add_argument("--collection", default=COLLECTION_NAME,
                        help=f"Milvus 集合名 (默认: {COLLECTION_NAME})")
    parser.add_argument("--dpi", type=int, default=150,
                        help="PDF 渲染 DPI (默认: 150)")
    parser.add_argument("--query", help="混合检索 + 重排 (不调用 LLM)")
    parser.add_argument("--ask", help="完整 RAG: 检索 → LLM 生成带引用的回答")
    args = parser.parse_args()

    if args.ask:
        chunks = query_kb(args.ask, args.collection)
        if chunks:
            generate_answer(args.ask, chunks)
        return

    if args.query:
        query_kb(args.query, args.collection)
        return

    pdf_path = args.pdf or "/home/thomas/mySpace/langchain-in-action/RF-EM001R [Eyeris 1] US Quick Guide Card-Pen remote.pdf"

    if not os.path.exists(pdf_path):
        print(f"文件不存在: {pdf_path}")
        sys.exit(1)

    process_pdf(pdf_path, args.collection, dpi=args.dpi)


if __name__ == "__main__":
    main()
