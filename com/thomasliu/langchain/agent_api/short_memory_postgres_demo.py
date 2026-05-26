import os
import uuid
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langgraph.checkpoint.postgres import PostgresSaver

load_dotenv()

# ---------- 1. 配置环境变量 ----------
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("请先设置环境变量 OPENAI_API_KEY")

# ---------- 2. 配置 PostgreSQL 数据库连接 ----------
DB_URI = (
    f"postgresql://"
    f"{os.getenv('POSTGRES_USER', 'postgres')}:"
    f"{os.getenv('POSTGRES_PASSWORD', 'postgres')}@"
    f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
    f"{os.getenv('POSTGRES_PORT', '5432')}/"
    f"{os.getenv('POSTGRES_DB', 'langchain_db')}"
)

# ---------- 3. 初始化模型 ----------
model = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "deepseek-v4-pro"),
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com"),
        extra_body={"thinking": {"type": "disabled"}},
    )

# ---------- 4. 初始化 PostgreSQL Checkpoint（短记忆）----------
print("正在初始化 PostgreSQL Checkpoint（短记忆）...")
with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
    checkpointer.setup()
    print("PostgreSQL Checkpoint 表结构初始化成功")

    # ---------- 5. 创建 Agent（启用短记忆）----------
    agent = create_agent(
        model=model,
        tools=[],
        system_prompt="你是一个友好的助手",
        checkpointer=checkpointer,
    )

    # ---------- 6. 使用相同 thread_id 维持对话 ----------
    config = {"configurable": {"thread_id": "user_123_session_001"}}

    print("=== 第一轮对话 ===")
    response1 = agent.invoke(
        {"messages": [("user", "我叫thomas，喜欢编程")]},
        config=config
    )
    print("助手:", response1["messages"][-1].content)

    print("\n=== 第二轮对话（相同 thread_id，模型应记住用户）===")
    response2 = agent.invoke(
        {"messages": [("user", "我刚才说了我叫什么名字？")]},
        config=config
    )
    print("助手:", response2["messages"][-1].content)

    print("\n=== 第三轮对话 新 thread_id，模型会忘记之前的内容===")
    new_config = {"configurable": {"thread_id": "user_123_session_002"}}
    response3 = agent.invoke(
        {"messages": [("user", "我叫什么名字？")]},
        config=new_config
    )
    print("助手:", response3["messages"][-1].content)


