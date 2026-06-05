import traceback
import uuid

from langchain.agents import create_agent
from langchain_core.messages import SystemMessage, AIMessage
from app.agent.base import get_model
from app.agent.memory import get_long_term_memory, get_user_long_memory, save_user_long_memory
from app.agent.state import MedicalAgentState
from app.agent.tools import search_web, save_medical_info

# 药师提示词
PHARMACIST_PROMPT = """
【角色定义】
你是药师，只负责药品和用药相关问题。

【回复规则】
- 回复简洁实用

【职责范围】
你的职责（只做这些）：
1. 根据诊断和处方，给出详细用药指导：药名、剂量、服用时间、注意事项
2. 审核过敏禁忌，有问题直接提醒并给替代方案
3. 药品咨询：药物副作用、相互作用、存储方式
4. 提供药品替代方案（经济型/同类替代）
5. 回复时应说明药物的禁忌症，并主动询问用户是否有相关禁忌（如胃病、肝肾功能问题、怀孕等），有则需要替换药物
6. 可以使用 search_web 工具搜索药物相关知识（如药物详细信息、最新用药指南）

不是你的职责（不要做）：
- 不要诊断疾病，那是医生的工作
- 不要收集用户基本信息，那是体检员的工作
- 不要做导诊引导，那是顾问的工作

【语言风格】
简明扼要，像药房窗口的药师。
"""

#药师节点
def pharmacist_node(state: MedicalAgentState):
    try:
        model = get_model()

        messages = state["messages"]

        user_id = state["user_id"]

        store = get_long_term_memory()

        #从状态中获取 诊断信息 （来自于主治医生）
        diagnosis = state.get("diagnosis","")

        #如果有诊断信息 添加到消息列表末尾
        if diagnosis:
            messages = messages+[SystemMessage(content=f"\n\n【诊断信息】\n {diagnosis}")]

        #用户 个人信息和医疗信息
        user_context = get_user_long_memory(user_id, store)

        if user_context:
            system_message = SystemMessage(content=f"用户历史信息（特别注意过敏史）:\n\n{user_context}")

            messages = [system_message]+messages

        agent = create_agent(model=model, tools=[search_web, save_medical_info],
                             system_prompt=PHARMACIST_PROMPT)


        #构建配置信息
        config={
            "configurable":{
                "user_id": user_id,
                "thread_id": state["thread_id"]
            }
        }

        response = agent.invoke({"messages": messages}, config=config)

        if response["messages"]:
            last_msg = response["messages"][-1]

            if isinstance(last_msg,AIMessage):
                if not last_msg.content.startswith("【药师】"):
                    last_msg.content = "【药师】 \n"+last_msg.content

                #保存处方
                save_user_long_memory(
                    store,
                    ("user_medical_records",user_id,"prescription"),
                    f"prescription_{uuid.uuid4().hex[:8]}",
                    {"content":last_msg.content,"timestamp": str(uuid.uuid1())}
                )

        return {
            "messages": response["messages"],

            "prescription":response["messages"][-1].content if response["messages"] else "",

            "next":"__end__"
        }
    except Exception as e:
        print(f"药师执行出错:{e}")
        print(traceback.format_exc())
        return {
            "messages":[AIMessage(content=f"【药师】\n 抱歉，系统暂时无法处理您的请求。错误：{str(e)}")],
            "next":"__end__"
        }