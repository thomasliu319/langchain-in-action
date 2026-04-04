import os
from langchain_deepseek import ChatDeepSeek
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence

llm = ChatDeepSeek(
    model=os.getenv("MODEL_NAME", "deepseek-chat"),
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    temperature=0.7,
)

history = []


def step1_intent(input_text):
    prompt = f"请根据以下输入识别用户意图：{input_text}"
    result = llm.invoke(prompt)
    return result.content


def step2_entity(intent, input_text):
    prompt = f"根据用户的意图 '{intent}'，从以下输入中提取相关实体：{input_text}"
    result = llm.invoke(prompt)
    return result.content


def step3_action(intent, entities):
    prompt = f"根据意图 '{intent}' 和提取的实体 '{entities}'，确定要执行的操作。"
    result = llm.invoke(prompt)
    return result.content


def step4_response(action):
    prompt = f"根据确定的动作 '{action}' 生成用户的响应。"
    result = llm.invoke(prompt)
    return result.content


def run_sequential_chain(input_text):
    global history
    intent = step1_intent(input_text)
    entities = step2_entity(intent, input_text)
    action = step3_action(intent, entities)
    response = step4_response(action)

    history.append(
        {
            "input": input_text,
            "intent": intent,
            "entities": entities,
            "action": action,
            "response": response,
        }
    )

    return {
        "intent": intent,
        "entities": entities,
        "action": action,
        "response": response,
    }


if __name__ == "__main__":
    input_text = "我想查询北京的天气。"
    result = run_sequential_chain(input_text)
    print("\n最终生成的响应:", result["response"])

    input_text_2 = "那明天呢？"
    result_2 = run_sequential_chain(input_text_2)
    print("\n最终生成的响应 (第二轮):", result_2["response"])

    print("\n对话历史:")
    for i, h in enumerate(history):
        print(f"\n--- 第{i + 1}轮 ---")
        print(f"输入: {h['input']}")
        print(f"响应: {h['response']}")
