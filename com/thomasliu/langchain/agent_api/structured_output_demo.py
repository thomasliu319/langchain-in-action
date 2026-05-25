import os
from dotenv import load_dotenv
from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

# ---------- 1. 定义 Pydantic 模型 ----------
class Resume(BaseModel):
    name: str = Field(description="候选人姓名")
    phone: Optional[str] = Field(default=None, description="手机号码，格式为11位数字")
    email: Optional[str] = Field(default=None, description="电子邮箱地址")
    skills: List[str] = Field(default_factory=list, description="掌握的技能关键词列表")

# ---------- 2. 创建解析器 ----------
parser = PydanticOutputParser(pydantic_object=Resume)

# ---------- 3. 初始化模型 ----------
model = ChatOpenAI(
    model=os.getenv("OPENAI_MODEL", "deepseek-v4-pro"),
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com"),
    temperature=0.1,
)

# ---------- 4. 构建 Prompt 模板 ----------
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个简历信息提取助手，请从用户提供的简历文本中提取信息。\n{format_instructions}"),
    ("human", "{resume_text}"),
])

# ---------- 5. 组装链 ----------
chain = prompt | model | parser

# ---------- 6. 测试数据 ----------
resume_text = """
姓名：张三
电话：13812345678
邮箱：zhangsan@example.com
掌握 Python、Java、SQL，有三年后端开发经验。
"""

# ---------- 7. 调用并获取结构化结果 ----------
result = chain.invoke({
    "resume_text": resume_text,
    "format_instructions": parser.get_format_instructions(),
})

# ---------- 8. 打印结果 ----------
print("=== 结构化输出结果 ===")
print(f"姓名：{result.name}")
print(f"电话：{result.phone}")
print(f"邮箱：{result.email}")
print(f"技能：{', '.join(result.skills)}")
print(f"\n原始 Pydantic 对象：{result}")
