"""ReAct Agent 路由"""
import json
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse

from ..services import agent_service
from ..services.models import ChatRequest

router = APIRouter(prefix="/api/agent", tags=["Agent"])


@router.post("/chat")
async def chat(req: ChatRequest):
    """一次性 Agent 回答"""
    try:
        reply = agent_service.run_agent(req.message)
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(500, f"Agent 调用失败: {str(e)}")


def _run_chat_stream(message: str):
    """Agent 流式输出的公共逻辑"""
    def gen():
        for event in agent_service.run_agent_stream(message):
            yield f"data: {json.dumps(event)}\n\n"
        yield "data: [DONE]\n\n"
    return gen()


@router.get("/chat-stream")
async def chat_stream_get(message: str = Query(...)):
    """流式 Agent 回答（SSE），GET 版本供 EventSource 调用"""
    try:
        return StreamingResponse(_run_chat_stream(message), media_type="text/event-stream; charset=utf-8")
    except Exception as e:
        return StreamingResponse(_error_gen(f"Agent 调用失败: {str(e)}"), media_type="text/event-stream; charset=utf-8")


@router.post("/init-kb")
async def init_kb():
    """初始化客服知识库"""
    result = agent_service.init_knowledge_base()
    return result


def _error_gen(msg: str):
    import json
    yield f"data: {json.dumps({'content': msg, 'type': 'error'})}\n\n"
    yield "data: [DONE]\n\n"
