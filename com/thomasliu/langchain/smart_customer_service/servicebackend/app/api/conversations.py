from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from openai.resources.fine_tuning.checkpoints import checkpoints
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agent.memory import get_short_term_memory
from app.api.auth import get_current_user
from app.database.postgresql import get_postgres_db
from app.models.conversation import Conversation
from app.models.user import User

#创建路由实例

router = APIRouter()

#会话创建请求的 模型
class ConversationCreate(BaseModel):
    id: str

    title: str


#创建新会话 接口
@router.post("/create")
async def create_conversation(
        conversation: ConversationCreate,
        user_id: int,
        current_user:User = Depends(get_current_user),
        db: Session = Depends(get_postgres_db)
):

    try:
        existing_conv = db.query(Conversation).filter(Conversation.id == conversation.id).first()

        if existing_conv:
            raise HTTPException(status_code=400, detail="会话id已经存在")

        #创建新会话 ORM 对象

        new_conv = Conversation(id=conversation.id, title=conversation.title,user_id=user_id, last_message="",
                                last_active=datetime.now(), created_at=datetime.now())

        db.add(new_conv)

        db.commit();

        db.refresh(new_conv)

        return {
            "message": "会话创建成功",
            "conversation":{
                "id": new_conv.id,
                "title": new_conv.title,
                "last_message": new_conv.user_id,
                "last_active": new_conv.last_active,
                "created_at": new_conv.created_at
            }
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"会话创建失败str(e)")



#获取会话列表
@router.get("/list")
async def  list_conversations(
        user_id: int,
        current_user:User = Depends(get_current_user),
        db: Session = Depends(get_postgres_db)
):

    try:

        conversations = (db.query(Conversation).filter(Conversation.user_id == user_id).order_by(Conversation.last_active).all())

        result = []

        for conversation in conversations:
            result.append({
                "id": conversation.id,
                "title": conversation.title,
                "user_id": conversation.user_id,
                "last_message": conversation.last_message,
                "last_active": conversation.last_active,
                "create_at": conversation.created_at
            })

        return {
            "conversations": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"会话列表获取失败： {str(e)}")

#删除会话接口
@router.delete("/delete")
async def delete_conservation(
        conversation_id:str,
        current_user:User = Depends(get_current_user),
        db: Session = Depends(get_postgres_db)
    ):
    try:
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()

        if not conversation:
            raise HTTPException(status_code=404, detail="会话不存在")

        #删除会话 会话列表中删除 +  短期记忆删除
        try:
            checkpointer = get_short_term_memory()

            if checkpointer:
                checkpointer.delete_thread(thread_id=conversation_id)
                print("清理短记忆成功")
        except Exception as e:
            print(f"清理短记忆失败 :{str(e)} ")

        db.delete(conversation)
        db.commit()


        return {
            "message": "会话删除成功"
        }
    except HTTPException :
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"会话删除失败 :{str(e)} ")

# 获取会话详情接口
@router.get("/get")
async def  get_conversation(
        conversation_id:str,
        current_user:User = Depends(get_current_user),
        db: Session = Depends(get_postgres_db)
    ):

    try:

        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()

        if not conversation:
            raise HTTPException(status_code=404, detail="会话不存在")

        #消息列表
        message_list = []
        try:
            checkpointer = get_short_term_memory()

            config = {"configurable":{"thread_id": conversation_id}}

            checkpoints = list(checkpointer.list(config))

            if checkpoints:
                latest = checkpoints[0]

                checkpoint_data = latest.checkpoint

                channel_values = checkpoint_data.get("channel_values", {})

                messages = channel_values.get("messages", [])

                for msg in messages:
                    if hasattr(msg, 'content') and hasattr(msg, 'type'):

                        # 过滤
                        if msg.type in ['human','ai']:
                            if msg.content and str(msg.content).strip():

                                role = "user" if msg.type == "human" else "assistant"

                                message_list.append({
                                    "role": role,
                                    "content": msg.content
                                })

        except Exception as e:
            print(f"读取短记忆失败： {str(e)}")
            import traceback
            print(traceback.format_exc())

        return {
            "conversation": {
                "id": conversation.id,
                "title": conversation.title,
                "user_id": conversation.user_id,
                "last_message": conversation.last_message,
                "last_active": conversation.last_active,
                "created_at": conversation.created_at,
            },
            "messages": message_list
        }


    except HTTPException :
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"会话详情获取失败：{str(e)}"
        )





