# 主治医生提示词
import traceback
import uuid

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, SystemMessage

from app.agent.base import get_model
from app.agent.memory import get_long_term_memory, get_user_long_memory, save_user_long_memory
from app.agent.state import MedicalAgentState
from app.agent.tools import save_medical_info, search_web

ATTENDING_DOCTOR_PROMPT = """
【角色定义】
你是主治医生，只负责诊断和制定治疗方案。
{goal_section}

【回复规则】
- 回复简洁专业
{compressed_section}

【职责范围】
你的职责（只做这些）：
1. 根据体检员收集的症状和报告，给出诊断结果（疾病名称、严重程度）
2. 制定治疗方案：药物处方（名称、剂量、用法、疗程）+ 生活/饮食建议
3. 注意用户过敏史和禁忌（如怀孕），有禁忌时提醒并换药
4. 开具的药物必须避开用户已知的过敏和禁忌
5. 病情严重时建议线下就医，一般情况直接给方案
6. 如果开了药物，回复结尾引导用户："如需了解用药注意事项或副作用，可以询问药师"
7. 可以使用 search_web 工具搜索药物相关知识（如药物相互作用、替代方案）

不是你的职责（不要做）：
- 不要询问用户基本信息（姓名、年龄等），那是体检员的工作
- 不要详细解释药物使用方法，那是药师的工作
- 不要做导诊引导，那是顾问的工作

【语言风格】
专业简洁，像门诊医生问诊。
"""



#主治医生节点
def attending_doctor_node(state: MedicalAgentState):
    try:
        model = get_model()

        messages = state["messages"]
        user_id = state["user_id"]
        store = get_long_term_memory()

        # 用户历史记忆
        user_context = get_user_long_memory(user_id, store)

        if user_context:
            system_message = SystemMessage(content=f"用户历史信息:\n\n{user_context}")
            messages = [system_message] + messages

        # 构建目标段 + 压缩上下文段
        goal_section = ""
        goal = state.get("original_goal") or state.get("current_goal")
        if goal:
            goal_section = f"\n【当前任务目标】{goal}\n"

        compressed_section = ""
        compressed = state.get("compressed_history")
        if compressed:
            compressed_section = f"\n=====对话摘要=====\n{compressed}\n=====摘要结束====="


        agent = create_agent(
            model=model,
            tools=[search_web, save_medical_info],
            system_prompt=ATTENDING_DOCTOR_PROMPT.format(
                goal_section=goal_section,
                compressed_section=compressed_section,
            ),
        )

        config = {
            "configurable": {
                "user_id": user_id,
                "thread_id": state["thread_id"],
            }
        }

        response = agent.invoke({"messages": messages}, config=config)

        if response["messages"]:
            last_msg = response["messages"][-1]

            if isinstance(last_msg, AIMessage):
                if not last_msg.content.startswith("【主治医生】"):
                    last_msg.content = "【主治医生】 \n" + last_msg.content

                save_user_long_memory(
                    store,
                    ("user_medical_records", user_id, "diagnosis"),
                    f"diagnosis_{uuid.uuid4().hex[:8]}",
                    {"content": last_msg.content, "timestamp": str(uuid.uuid1())},
                )

        return {
            "messages": response["messages"],
            "diagnosis": response["messages"][-1].content if response["messages"] else "",
            "next": "__end__",
        }
    except Exception as e:
        print(f"主治医生执行出错:{e}")
        print(traceback.format_exc())
        return {
            "messages": [AIMessage(content=f"【主治医生】\n 抱歉，系统暂时无法处理您的请求。错误：{str(e)}")],
            "next": "__end__",
        }