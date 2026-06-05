import asyncio
from typing import Optional

from langchain_core.messages import HumanMessage

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agent.multi_agent import create_medical_agent_system
from app.api.auth import get_current_user
from app.database.postgresql import get_postgres_db
from app.models.conversation import Conversation
from app.models.user import User

router = APIRouter()

_agent_graph = None

def get_agent():
    global _agent_graph
    if _agent_graph is None:
        _agent_graph = create_medical_agent_system()
    return _agent_graph

class ChatRequest(BaseModel):
    message: str
    thread_id: str
    user_id: Optional[str] = None

@router.post("/send")
async def chat_send(
        req: ChatRequest,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_postgres_db)
):
    conversation = db.query(Conversation).filter(Conversation.id == req.thread_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")

    try:
        graph = get_agent()

        result = await asyncio.to_thread(
            lambda: graph.invoke(
                {
                    "messages": [HumanMessage(content=req.message)],
                    "user_id": str(current_user.id),
                    "thread_id": req.thread_id,
                    "medical_documents": [],
                    "diagnosis": None,
                    "prescription": None,
                },
                config={"configurable": {"thread_id": req.thread_id}}
            )
        )

        messages = result.get("messages", [])
        reply_content = ""
        for msg in reversed(messages):
            if hasattr(msg, "type") and msg.type == "ai" and msg.content:
                reply_content = msg.content
                break

        conversation.last_message = reply_content[:200]
        db.commit()

        return {
            "success": True,
            "message": reply_content
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_msg = f"{type(e).__name__}: {str(e)}"
        print(f"AI回复失败:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"AI回复失败: {error_msg}")
