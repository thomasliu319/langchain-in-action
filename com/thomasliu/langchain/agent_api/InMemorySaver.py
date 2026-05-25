import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

load_dotenv()

# ---------- 1. 初始化模型 ----------
model = ChatOpenAI(
    model=os.getenv("OPENAI_MODEL", "deepseek-v4-pro"),
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com"),
)

# 创建记忆存储
checkpointer = InMemorySaver();

agent = create_agent(
    model=model,
    tools=[],
    system_prompt="你是一个友好的聊天助手",
    checkpointer=checkpointer
)

#  使用同一个 thread_id 保持会话
config = {"configurable": {"thread_id": "user_123"}}

# 第一轮对话
response1 = agent.invoke(
    {"messages": [("user", "我叫张三，喜欢打篮球")]},
    config = config
)

print("助手：", response1["messages"][-1].content)

# 第二轮对话
response2 = agent.invoke(
    {"messages": [("user", "我叫什么名字？我喜欢什么运动？")]},
    config = config
)

print("助手：", response2["messages"][-1].content)