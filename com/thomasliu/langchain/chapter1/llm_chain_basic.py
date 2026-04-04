import os
from langchain_deepseek import ChatDeepSeek
from langchain_core.prompts import PromptTemplate

llm = ChatDeepSeek(
    model=os.getenv("MODEL_NAME", "deepseek-reasoner"),
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    temperature=0.8,
)

prompt_template = PromptTemplate(
    input_variables=[],
    template="请用简明扼要的语言描述企业创新的重要性，并说明它如何影响企业的长远发展。",
)

chain = prompt_template | llm

if __name__ == "__main__":
    result = chain.invoke({})
    print("生成的企业创新描述：")
    print(result.content if hasattr(result, "content") else result)
