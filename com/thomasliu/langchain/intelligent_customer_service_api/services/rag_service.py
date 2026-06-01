"""
多模态 RAG 服务：封装 multimodal_rag.py 中的业务逻辑
提供模型惰性加载、PDF 处理、混合检索、流式生成等能力
"""
import os
import json
import time
import warnings
from PIL import Image
from pdf2image import convert_from_path
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..config import settings

warnings.filterwarnings("ignore")

# ─── 全局惰性加载（单例模式，复用模型） ───
_llm = None
_processor = None
_embed_model = None
_milvus = None
_bm25 = None
_bm25_corpus = None
_bm25_idx = {}
_reranker = None
_is_omni_model = False


def _get_vl_model():
    global _llm, _processor, _is_omni_model
    if _llm is None:
        import torch
        from transformers import AutoProcessor

        model_path = settings.VL_MODEL_PATH
        model_name = os.path.basename(model_path)

        with open(os.path.join(model_path, "config.json")) as f:
            archs = json.load(f).get("architectures", [])

        if "Qwen2_5Omni" in str(archs):
            from transformers import Qwen2_5OmniForConditionalGeneration as ModelClass
            _is_omni_model = True
        elif "Qwen2_5_VL" in str(archs):
            from transformers import Qwen2_5_VLForConditionalGeneration as ModelClass
        else:
            from transformers import AutoModelForCausalLM as ModelClass

        _llm = ModelClass.from_pretrained(model_path, torch_dtype=torch.float16, device_map="auto")
        _processor = AutoProcessor.from_pretrained(model_path)
    return _llm, _processor


def _get_embed_model():
    global _embed_model
    if _embed_model is None:
        from sentence_transformers import SentenceTransformer
        _embed_model = SentenceTransformer(settings.EMB_MODEL_PATH)
    return _embed_model


def _get_milvus():
    global _milvus
    if _milvus is None:
        from pymilvus import MilvusClient
        _milvus = MilvusClient(uri=settings.MILVUS_URI)
    return _milvus


def _get_reranker():
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder
        _reranker = CrossEncoder(settings.RERANKER_MODEL_PATH, device="cpu")
    return _reranker


# ─── PDF → IMG ───

def pdf_to_images(pdf_path: str, dpi: int = 150, max_size: int = 1280) -> list[Image.Image]:
    images = convert_from_path(pdf_path, dpi=dpi)
    result = []
    for img in images:
        img.thumbnail((max_size, max_size), Image.LANCZOS)
        result.append(img)
    return result


# ─── OCR ───

def analyze_page(image: Image.Image) -> str:
    llm, processor = _get_vl_model()
    prompt = (
        "You are an OCR assistant. Extract ALL visible text from this product document page. "
        "Include: product name, model number, specifications, instructions, "
        "button labels, diagrams, tables, and any other text. "
        "Preserve original language and formatting. Be thorough and complete."
    )
    messages = [{"role": "user", "content": [{"type": "image", "image": image}, {"type": "text", "text": prompt}]}]
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = processor(text=[text], images=[image], padding=True, return_tensors="pt")
    inputs = {k: v.to(llm.device) for k, v in inputs.items()}
    gen_kwargs = {"max_new_tokens": 2048}
    if _is_omni_model:
        gen_kwargs["generation_mode"] = "text"
    generated_ids = llm.generate(**inputs, **gen_kwargs)
    input_len = inputs["input_ids"].shape[1]
    response = processor.decode(generated_ids[0][input_len:], skip_special_tokens=True)
    return response.strip()


# ─── 清洗 ───

def clean_text(raw: str) -> str:
    return "\n".join(line.strip() for line in raw.split("\n") if line.strip())


def structure_content(raw: str, source: str, page: int) -> dict:
    return {
        "source": source, "page": page, "raw_text": raw,
        "clean_text": clean_text(raw), "content_type": "document_page",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


# ─── 分块 & 嵌入 ───

def chunk_text(text: str, chunk_size: int = 300, overlap: int = 30) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=overlap, separators=["\n\n", "\n", ". ", " ", ""])
    chunks = splitter.split_text(text)
    return chunks if chunks else [text]


def embed_chunks(chunks: list[str]) -> list[list[float]]:
    return _get_embed_model().encode(chunks).tolist()


# ─── Milvus ───

def init_milvus(collection_name: str, dim: int = 1024):
    client = _get_milvus()
    if not client.has_collection(collection_name):
        client.create_collection(collection_name=collection_name, dimension=dim, auto_id=True, metric_type="COSINE")
    return client


def store_to_milvus(entries: list[dict], collection_name: str):
    client = init_milvus(collection_name)
    for entry in entries:
        res = client.insert(collection_name, entry)
        if res.get("insert_count", 0) == 0:
            pass
    client.flush(collection_name)


# ─── 完整 PDF 处理 ───

def process_pdf(pdf_path: str, collection_name: str = None, dpi: int = 150):
    collection_name = collection_name or settings.RAG_COLLECTION
    filename = os.path.basename(pdf_path)

    images = pdf_to_images(pdf_path, dpi=dpi)
    all_entries = []
    for i, img in enumerate(images):
        raw = analyze_page(img)
        structured = structure_content(raw, filename, i + 1)
        clean = structured["clean_text"]

        full_emb = embed_chunks([clean])[0]
        all_entries.append({"vector": full_emb, "text": clean, "source": filename, "page": i + 1, "chunk_index": 0, "chunk_label": "full_page", "content_type": "document_page", "timestamp": structured["timestamp"]})

        chunks = chunk_text(clean)
        embeddings = embed_chunks(chunks)
        for j, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            all_entries.append({"vector": emb, "text": chunk, "source": filename, "page": i + 1, "chunk_index": j + 1, "chunk_label": "semantic_chunk", "content_type": "document_page", "timestamp": structured["timestamp"]})

    store_to_milvus(all_entries, collection_name)
    return {"file": filename, "pages": len(images), "vectors": len(all_entries)}


# ─── BM25 ───

def _build_bm25_index(collection_name: str):
    global _bm25, _bm25_corpus, _bm25_idx
    from rank_bm25 import BM25Okapi
    docs = _get_milvus().query(collection_name, output_fields=["text"], filter='chunk_label == "semantic_chunk"', limit=10000)
    _bm25_corpus = [d["text"] for d in docs]
    _bm25_idx = {t: i for i, t in enumerate(_bm25_corpus)}
    _bm25 = BM25Okapi([t.split() for t in _bm25_corpus])


# ─── 混合检索 + Rerank ───

def query_kb(query: str, collection_name: str = None, top_k: int = 50, final_k: int = 3, alpha: float = 0.5):
    import numpy as np
    collection_name = collection_name or settings.RAG_COLLECTION

    client = _get_milvus()
    model = _get_embed_model()
    _build_bm25_index(collection_name)

    if not _bm25_corpus:
        return []

    q_emb = model.encode(query).tolist()
    vec_results = client.search(collection_name, data=[q_emb], limit=top_k, output_fields=["text", "source", "chunk_index"], filter='chunk_label == "semantic_chunk"')

    bm25_scores = np.array(_bm25.get_scores(query.split()))
    bm25_max = max(bm25_scores.max(), 1.0)

    candidates = {}
    for r in vec_results[0]:
        text = r["entity"]["text"]
        vec_score = r["distance"]
        corpus_i = _bm25_idx.get(text, -1)
        bm25_norm = bm25_scores[corpus_i] / bm25_max if corpus_i >= 0 else 0
        combined = alpha * vec_score + (1 - alpha) * bm25_norm
        candidates[text] = {"score": combined, "source": r["entity"]["source"], "chunk_index": r["entity"]["chunk_index"], "text": text}

    bm25_top = bm25_scores.argsort()[::-1][:top_k]
    for i in bm25_top:
        if bm25_scores[i] <= 0:
            break
        text = _bm25_corpus[i]
        if text not in candidates:
            candidates[text] = {"score": (1 - alpha) * bm25_scores[i] / bm25_max, "source": "BM25", "chunk_index": -1, "text": text}

    ranked = sorted(candidates.values(), key=lambda x: x["score"], reverse=True)[:top_k]

    reranker = _get_reranker()
    rerank_scores = reranker.predict([[query, r["text"]] for r in ranked])
    for i, score in enumerate(rerank_scores):
        ranked[i]["rerank_score"] = float(score)

    final = sorted(ranked, key=lambda x: x["rerank_score"], reverse=True)[:final_k]
    return final


# ─── 流式生成（同步 generator，供 StreamingResponse 使用） ───

def generate_answer_stream(query: str, chunks: list[dict]):
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

    client = OpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL)
    stream = client.chat.completions.create(
        model=settings.OPENAI_MODEL, temperature=0, stream=True,
        extra_body={"thinking": {"type": "disabled"}},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"上下文：\n{context}\n\n问题：{query}"},
        ],
    )
    for chunk in stream:
        token = chunk.choices[0].delta.content or ""
        if token:
            yield token
