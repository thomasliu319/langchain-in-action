# -*- coding: utf-8 -*-

"""
@author: thomasliu319@gmail.com
@description: PyCharm
@file: llm_chain_with_memory.py
@time: 4/4/26 17:13
"""
import os
from langchain_core.prompts import PromptTemplate
from langchain_deepseek import ChatDeepSeek


llm = ChatDeepSeek(
    model=os.getenv("MODEL_NAME", "deepseek-reasoner"),
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    temperature= 0.7,
)

prompt_template = PromptTemplate(
    input_variables=["product_name", "features"],
    template="请介绍产品{product_name},其特点为{features}。",
)

chain = prompt_template | llm

if __name__ == "__main__":
    result = chain.invoke(
        {"product_name": "小爱音箱", "features": "语音控制、智能家居联动"}
    )
    print(result.content if hasattr(result, "content") else result)
