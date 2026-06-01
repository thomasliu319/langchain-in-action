from pydantic import BaseModel, Field
from typing import Optional


# ─── RAG Models ───

class QueryRequest(BaseModel):
    query: str = Field(..., description="查询文本")
    collection: str = "multimodal_kb"
    top_k: int = Field(default=50, ge=1, le=100)
    final_k: int = Field(default=3, ge=1, le=20)
    alpha: float = Field(default=0.5, ge=0, le=1, description="向量检索权重 (0=纯BM25, 1=纯向量)")


class AskRequest(BaseModel):
    query: str = Field(..., description="用户问题")
    collection: str = "multimodal_kb"


class PdfProcessRequest(BaseModel):
    pdf_path: str = Field(..., description="PDF 文件路径")
    collection: str = "multimodal_kb"
    dpi: int = Field(default=150, ge=50, le=300)


class RerankResult(BaseModel):
    score: float
    source: str
    chunk_index: int
    text: str
    rerank_score: float


class QueryResponse(BaseModel):
    results: list[RerankResult]


# ─── Agent Models ───

class ChatRequest(BaseModel):
    message: str = Field(..., description="用户输入")
    thread_id: Optional[str] = Field(default="default", description="会话 ID，相同 ID 保持上下文")


# ─── KB Models ───

class KbInitRequest(BaseModel):
    source: str = "policy_doc"


class LoadMdRequest(BaseModel):
    file_path: str = Field(..., description="Markdown 文件路径")
    source_tag: str = "kb_doc"


class CollectionInfo(BaseModel):
    name: str
    exists: bool
    count: int


# ─── Model Mgmt ───

class DownloadRequest(BaseModel):
    repo_id: str = Field(..., description="HuggingFace 仓库 ID")
