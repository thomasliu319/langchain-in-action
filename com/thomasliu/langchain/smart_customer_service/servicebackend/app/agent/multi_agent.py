from langgraph.graph import StateGraph,END

from app.agent.attending_doctor import attending_doctor_node
from app.agent.medical_examiner import medical_examiner_node
from app.agent.memory import init_memory_system, get_short_term_memory, get_long_term_memory
from app.agent.pharmacist import pharmacist_node
from app.agent.state import MedicalAgentState
from app.agent.supervisor import supervisor_node


# ==================== 构建多智能体系统 ====================
# 创建医疗智能体系统（中心辐射式架构：supervisor路由到子智能体，一问一答模式）
def create_medical_agent_system():
    # 初始化记忆系统
    init_memory_system()

    # 获取记忆实例（使用函数确保获取最新实例）
    checkpointer = get_short_term_memory()

    store = get_long_term_memory()

    builder = StateGraph(MedicalAgentState)

    # 添加节点（4个智能体，从各自文件导入）
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("medical_examiner", medical_examiner_node)
    builder.add_node("attending_doctor", attending_doctor_node)
    builder.add_node("pharmacist", pharmacist_node)

    # 入口点
    builder.set_entry_point("supervisor")

    # supervisor 的条件边：根据 LLM 路由决策
    builder.add_conditional_edges(
        "supervisor",
        lambda state: state.get("next", "__end__"),
        {
                "medical_examiner": "medical_examiner",
                "attending_doctor": "attending_doctor",
                "pharmacist": "pharmacist",
                "__end__": END
        }
    )

    # 所有子智能体完成后直接结束（一问一答）
    builder.add_edge("medical_examiner", END)
    builder.add_edge("attending_doctor", END)
    builder.add_edge("pharmacist", END)

    # 使用函数返回的记忆实例（确保已初始化）
    graph = builder.compile(checkpointer=checkpointer, store=store)

    return graph