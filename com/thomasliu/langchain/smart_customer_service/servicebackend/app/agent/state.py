from typing import Annotated, TypedDict, List, Optional

from langgraph.graph import add_messages


#状态模块
class MedicalAgentState(TypedDict):

    # 消息列表（自动积累）
    messages: Annotated[list, add_messages]

    user_id: str

    thread_id: str

    medical_documents: List

    diagnosis: Optional[str]

    prescription: Optional[str]

    next: Optional[str]