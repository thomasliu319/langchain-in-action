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

    # ===== 目标追踪 =====
    original_goal: Optional[str]           # 用户原始意图（首次对话提取）
    current_goal: Optional[str]            # 当前子目标（经 supervisor 分解）

    # ===== 上下文压缩 =====
    compressed_history: Optional[str]      # 压缩后的历史摘要
    raw_turns_since_compress: int          # 自上次压缩后的原始轮数

    # ===== 质量反思 =====
    last_reflection: Optional[str]         # 上一步的目标对齐检查结果
    reflection_signal: Optional[str]       # 反思信号: "aligned" / "drifted" / "summarize_needed"

    # ===== 工具调用可靠性 =====
    tool_errors: List[str]                 # 本轮工具调用错误记录（用于 LLM 自愈）