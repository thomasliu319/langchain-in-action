import os
import uuid
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.store.postgres import PostgresStore
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig


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


# ---------- 3. 初始化 ----------
with PostgresStore.from_conn_string(DB_URI) as store:
    store.setup()

    with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
        checkpointer.setup()

        # ---------- 4. 初始化模型 ----------
        model = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "deepseek-v4-pro"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com"),
            temperature=0.3,
            extra_body={"thinking": {"type": "disabled"}},
        )

        # ---------- 5. 定义工具 ----------
        @tool
        def save_user_info(key: str, value: str, config: RunnableConfig) -> str:
            """保存用户的信息到长记忆

            Args:
                key: 信息的键名（如：name, vip_status, preference）
                value: 信息的值
            """
            user_id = config["configurable"]["user_id"]
            namespace = ("user_preferences", user_id)
            item_id = str(uuid.uuid4())
            store.put(namespace, item_id, {"key": key, "value": value})
            return f"已保存用户信息 {key}: {value}"


        @tool
        def get_user_info(config: RunnableConfig) -> str:
            """从长记忆获取用户所有的信息"""
            user_id = config["configurable"]["user_id"]
            namespace = ("user_preferences", user_id)
            items = store.search(namespace)
            preferences = []
            for item in items:
                key = item.value.get("key", "未知")
                value = item.value.get("value", "未知")
                preferences.append(f"{key}: {value}")
            return "\n".join(preferences) if preferences else "没有找到用户信息"

        # ---------- 6. 创建 Agent ----------
        agent = create_agent(
            model=model,
            tools=[save_user_info, get_user_info],
            system_prompt="""你是一个客服助手。
                当用户提到个人信息时，用 save_user_info 保存。
                当用户询问个人信息时，用 get_user_info 查询。""",
            checkpointer=checkpointer,
            store=store
        )

        # ---------- 7. 测试 ----------
        user_id = "user_002"
        config = {"configurable": {"user_id": user_id, "thread_id": "session_123"}}

        print("=== 第一轮对话 ===")
        response1 = agent.invoke(
            {"messages": [("user", "我是thomas，我是 VIP 用户，我喜欢 详细的产品说明")]},
            config=config
        )
        print("助手：", response1["messages"][-1].content)

        print("\n=== 第二轮对话（相同 thread_id）===")
        response2 = agent.invoke(
            {"messages": [("user", "我刚刚说了什么")]},
            config=config
        )
        print("助手：", response2["messages"][-1].content)

        print("\n=== 第三轮对话（新 thread_id）===")
        config2 = {"configurable": {"user_id": user_id, "thread_id": "session_1234"}}
        response3 = agent.invoke(
            {"messages": [("user", "我是谁？我喜欢什么？")]},
            config=config2
        )
        print("助手：", response3["messages"][-1].content)
