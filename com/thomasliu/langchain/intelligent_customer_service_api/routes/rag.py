"""多模态 RAG 路由"""
import os
import json
from fastapi import APIRouter, UploadFile, File, Form, Query, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse

from ..services import rag_service
from ..services.models import QueryRequest, AskRequest

router = APIRouter(prefix="/api/rag", tags=["RAG"])


@router.post("/query")
async def query(req: QueryRequest):
    """混合检索 + 重排序（不调用 LLM）"""
    results = rag_service.query_kb(query=req.query, collection_name=req.collection, top_k=req.top_k, final_k=req.final_k, alpha=req.alpha)
    return {"results": results}


def _run_ask(query: str, collection: str):
    """RAG 检索 + 流式生成的公共逻辑"""
    chunks = rag_service.query_kb(query=query, collection_name=collection)
    if not chunks:
        return _sse_gen("知识库中未找到相关信息。")

    def gen():
        for token in rag_service.generate_answer_stream(query, chunks):
            yield f"data: {json.dumps({'content': token, 'type': 'token'})}\n\n"
        refs = [{"source": c["source"], "rerank_score": round(c.get("rerank_score", 0), 3)} for c in chunks]
        yield f"data: {json.dumps({'type': 'references', 'references': refs})}\n\n"
        yield "data: [DONE]\n\n"
    return gen()


@router.get("/ask")
async def ask_get(query: str = Query(...), collection: str = Query("multimodal_kb")):
    """完整 RAG：SSE 流式（供 EventSource 浏览器调用）"""
    return StreamingResponse(_run_ask(query, collection), media_type="text/event-stream; charset=utf-8")


@router.post("/ask")
async def ask_post(req: AskRequest):
    """完整 RAG：SSE 流式（POST 版本）"""
    return StreamingResponse(_run_ask(req.query, req.collection), media_type="text/event-stream; charset=utf-8")


@router.post("/process-pdf")
async def process_pdf(file: UploadFile = File(...), collection: str = Form("multimodal_kb"), dpi: int = Form(150)):
    """上传 PDF 并处理入库"""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "仅支持 PDF 文件")

    temp_path = f"/tmp/{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(await file.read())

    try:
        result = rag_service.process_pdf(pdf_path=temp_path, collection_name=collection, dpi=dpi)
        return result
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.post("/process-pdf-path")
async def process_pdf_path(pdf_path: str = Form(...), collection: str = Form("multimodal_kb"), dpi: int = Form(150)):
    """处理服务器上已有的 PDF 文件"""
    if not os.path.exists(pdf_path):
        raise HTTPException(400, f"文件不存在: {pdf_path}")
    result = rag_service.process_pdf(pdf_path=pdf_path, collection_name=collection, dpi=dpi)
    return result


@router.post("/ocr")
async def ocr_image(file: UploadFile = File(...)):
    """OCR 识别上传的图片"""
    from PIL import Image
    import io
    image = Image.open(io.BytesIO(await file.read()))
    text = rag_service.analyze_page(image)
    return {"text": text, "length": len(text)}


def _sse_gen(text: str):
    yield f"data: {json.dumps({'content': text, 'type': 'token'})}\n\n"
    yield "data: [DONE]\n\n"
