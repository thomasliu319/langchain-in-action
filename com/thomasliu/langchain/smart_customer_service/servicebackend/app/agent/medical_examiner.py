# 体检员提示词
import traceback

from langchain.agents import create_agent
from langchain_core.messages import AIMessage

from app.agent.base import get_model
from app.agent.memory import get_long_term_memory, get_user_long_memory
from app.agent.state import MedicalAgentState
from app.agent.tools import search_web, save_user_info, save_medical_info

MEDICAL_EXAMINER_PROMPT = """
【角色定义】
你是体检员，专门负责收集用户健康信息。
{goal_section}

【回复规则】
- 回复简洁
- 每次只问2-3个关键问题
{memory_section}
{compressed_section}
1. 收集用户基本信息：姓名、年龄、性别、联系方式
2. 收集症状信息：主要症状、持续时间、严重程度
3. 收集病史信息：既往病史、过敏史、家族病史
4. 【重要 - 必须执行】当用户提供个人信息时，立即调用 save_user_info 工具保存到长记忆：
   - 用户提供姓名（如"我叫张三"、"张三"）→ 调用 save_user_info
   - 用户提供年龄（如"我30岁"、"30岁"）→ 调用 save_user_info
   - 用户提供性别（如"我是男性"、"男"、"女性"、"女"）→ 调用 save_user_info
   - 用户提供联系方式（如"电话13812345678"）→ 调用 save_user_info
   - 用户同时提供多个信息（如"张三，30岁，男"）→ 调用 save_user_info 一次性保存所有字段
5. 【重要 - 必须执行】当用户提供或修改病史信息时，立即调用 save_medical_info 工具保存到长记忆：
   - 症状描述（如"肚子痛"、"头痛"）→ 类别用"症状描述"
   - 过敏史（如"对青霉素过敏"）→ 类别用"过敏史"
   - 既往病史（如"做过阑尾手术"、"有高血压"）→ 类别用"既往病史"
6. 【混合信息识别】用户可能在同一句话中提供多种信息，必须识别并分别保存：
   - 例如："男，持续了一上午了，中度"
     * "男" → 调用 save_user_info 保存性别
     * "持续了一上午了，中度" → 调用 save_medical_info 保存症状
7. 收集到信息后立即保存，不要告诉用户已保存
8. 信息收集够了就生成健康信息摘要
9. 用户之前说过的病史、过敏史可能不完整，回复时应告诉用户当前已知的信息，并询问是否还有补充

不是你的职责（不要做）：
- 不要诊断疾病、不要开药，那是医生的工作
- 不要指导用药，那是药师的工作
- 不要做导诊引导，那是顾问的工作

【收集策略】
- 重要：如果用户说上传了文档，你应该已经从"用户已有信息"中看到了文档提取的内容，直接基于这些信息回复，不要说无法读取PDF
- 如果用户没有上传医疗文档，应优先引导用户点击"上传医疗文档"按钮，上传病历、体检报告、化验单等文件
- 用户选择上传文档后，说明文档信息已自动提取并保存在你的上下文中，你可以直接读取
- 只有在用户不上传文档或文档信息不完整时，才需要手动收集用户信息
- 收集信息时提醒用户"您也可以点击下方的上传按钮，上传病历或体检报告，系统会自动识别"
- 已有的信息不要重复问，但要确认是否完整
- 每轮只问1-2个最关键的缺失信息
- 不要一次列出所有问题
- 如果用户提到过敏史或病史，主动询问细节（如过敏药物名称、发病时间等）

【回复话术示例】
- "为了更准确地为您分析，您可以点击下方的「上传医疗文档」按钮，上传病历、体检报告或化验单，系统会自动提取信息。"
- "如果您暂时不方便上传，可以告诉我您的姓名、年龄和主要症状吗？"

【语言风格】
简洁友好，像医院导检台护士。
"""

#体检员节点
def medical_examiner_node(state: MedicalAgentState):
    try:
        model = get_model()

        messages = state["messages"]
        user_id = state["user_id"]
        store = get_long_term_memory()

        # 用户历史记忆
        user_context = get_user_long_memory(user_id, store)

        # 构建三段式上下文
        memory_section = ""
        if user_context:
            memory_section = f"\n=====用户已有信息（不要重复询问）=====\n{user_context}\n====已有信息结束====="

        goal_section = ""
        goal = state.get("original_goal") or state.get("current_goal")
        if goal:
            goal_section = f"\n【当前任务目标】{goal}\n"

        compressed_section = ""
        compressed = state.get("compressed_history")
        if compressed:
            compressed_section = f"\n=====对话摘要（之前已压缩的对话）=====\n{compressed}\n=====摘要结束=====\n"


        agent = create_agent(
            model=model,
            tools=[search_web, save_user_info, save_medical_info],
            system_prompt=MEDICAL_EXAMINER_PROMPT.format(
                memory_section=memory_section,
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
                if not last_msg.content.startswith("【体检员】"):
                    last_msg.content = "【体检员】\n" + last_msg.content

        return {
            "messages": response["messages"],
            "next": "__end__",
        }

    except Exception as e:
        print(f"体检员执行出错：{e}")
        print(traceback.format_exc())
        return {
            "messages": [AIMessage(content=f"【体检员】\n 抱歉，系统暂时无法处理您的请求。错误：{str(e)}")],
            "next": "__end__",
        }

