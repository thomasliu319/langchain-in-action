"""知识库管理路由"""
import json
from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import StreamingResponse

from ..services import kb_service

router = APIRouter(prefix="/api/kb", tags=["知识库"])


@router.get("/collections")
async def list_collections():
    """列出所有集合"""
    names = kb_service.list_collections()
    infos = [kb_service.get_collection_info(n) for n in names]
    return {"collections": infos}


@router.get("/collection/{name}")
async def collection_info(name: str):
    """获取指定集合信息"""
    return kb_service.get_collection_info(name)


@router.delete("/collection/{name}")
async def drop_collection(name: str):
    """删除集合"""
    return kb_service.drop_collection(name)


@router.post("/search")
def search_kb(query: str = Form(...), collection: str = Form("customer_service_kb"), n_results: int = Form(3)):
    """知识库向量检索"""
    results = kb_service.query_knowledge_base(query, collection=collection, n_results=n_results)
    return {"results": results, "count": len(results)}


@router.post("/load-md")
async def load_markdown(file_path: str = Form(...), source_tag: str = Form("kb_doc")):
    """加载 Markdown 文件到知识库"""
    try:
        text = kb_service.load_markdown_file(file_path)
        chunks = kb_service.text_to_chunks(text)
        count = kb_service.insert_text_chunks(chunks, source_tag=source_tag)
        return {"file": file_path, "chunks": count, "characters": len(text)}
    except FileNotFoundError:
        raise HTTPException(400, f"文件不存在: {file_path}")
    except Exception as e:
        raise HTTPException(500, f"加载失败: {str(e)}")


@router.post("/init-policy")
async def init_policy():
    """初始化预设政策文档到知识库"""
    chunks = kb_service.load_policy_docs()
    count = kb_service.insert_text_chunks(chunks, source_tag="policy_doc")
    return {"status": "ok", "chunks": count}
