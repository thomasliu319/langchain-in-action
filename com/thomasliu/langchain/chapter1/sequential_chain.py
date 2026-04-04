# -*- coding: utf-8 -*-
import os
from langchain_core.prompts import PromptTemplate
from langchain_deepseek import ChatDeepSeek

llm = ChatDeepSeek(
    model=os.getenv("MODEL_NAME", "deepseek-chat"),
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    temperature=0.7,
)


def step1_intent(x):
    """步骤1: 识别意图"""
    prompt = f"请根据以下输入识别用户意图：{x['input_text']}"
    result = llm.invoke(prompt)
    return {"intent": result.content, "input_text": x["input_text"]}


def step2_entity(x):
    """步骤2: 提取实体"""
    prompt = (
        f"根据用户的意图 '{x['intent']}'，从以下输入中提取相关实体：{x['input_text']}"
    )
    result = llm.invoke(prompt)
    return {"entities": result.content, **x}


def step3_action(x):
    """步骤3: 确定动作"""
    prompt = (
        f"根据意图 '{x['intent']}' 和提取的实体 '{x['entities']}'，确定要执行的操作。"
    )
    result = llm.invoke(prompt)
    return {"action": result.content, **x}


def step4_response(x):
    """步骤4: 生成响应"""
    prompt = f"根据确定的动作 '{x['action']}' 生成用户的响应。"
    result = llm.invoke(prompt)
    return result


def run_sequential_chain(input_text):
    """运行顺序链"""
    x = {"input_text": input_text}
    x = step1_intent(x)
    x = step2_entity(x)
    x = step3_action(x)
    x = step4_response(x)
    return x


if __name__ == "__main__":
    input_text = "我想查询深圳今天的天气。"
    final_response = run_sequential_chain(input_text)
    print(
        "\n最终生成的响应:",
        final_response.content
        if hasattr(final_response, "content")
        else final_response,
    )
