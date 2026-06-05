from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.store.postgres import PostgresStore
from psycopg_pool import ConnectionPool

from app.config.settings import settings

#短记忆数据库连接池
short_term_pool = None
#长记忆数据库连接池
long_term_pool = None

#段记忆储存器实例
short_term_memory = None
#长记忆储存器实例
long_term_memory = None

#初始化 记忆  连接池
def init_memory_system():
    global short_term_pool, long_term_pool, short_term_memory, long_term_memory

    if short_term_pool is None:
        try:
            print("短记忆连接池 初始化中")
            short_term_pool = ConnectionPool(conninfo=settings.POSTGRES_SHORT_TERM_URL, min_size=2, max_size=10,
                                             kwargs={"autocommit": True, "prepare_threshold": 0, "keepalives": 1,
                                                     "keepalives_idle": 30, "keepalives_interval": 10,
                                                     "keepalives_count": 3})

            short_term_memory = PostgresSaver(short_term_pool)

            short_term_memory.setup()

            print("初始化短记忆连接池成功")

            #长记忆连接池
            long_term_pool = ConnectionPool(conninfo=settings.POSTGRES_LONG_TERM_URL, min_size=2, max_size=10,
                                            kwargs={"autocommit": True, "prepare_threshold": 0, "keepalives": 1,
                                                    "keepalives_idle": 30, "keepalives_interval": 10,
                                                    "keepalives_count": 3})

            long_term_memory = PostgresStore(long_term_pool)

            long_term_memory.setup()
            print("初始化长记忆连接池成功")
        except Exception as e:
            print(f"记忆系统初始化失败: {str(e)}")
            raise

#获取短记忆实例
def get_short_term_memory():
    global short_term_memory
    if short_term_memory is None:
        init_memory_system()
    return short_term_memory


#获取长记忆 实例
def get_long_term_memory():
    global long_term_memory
    if long_term_memory is None:
        init_memory_system()
    return long_term_memory


#长记忆管理

#保存用户数据到长记忆 个人信息+医疗记录
def save_user_long_memory(store, namespace: tuple, item_id: str, data: dict):
    if store is None:
        store = get_long_term_memory()
    try:
        store.put(namespace, item_id, data)
    except Exception as e:
        print(f"保存用户信息长记忆出错：{str(e)}")


#获取用户长记忆 个人信息+医疗记录
def get_user_long_memory(user_id:str,store=None)->str:
    if store is None:
        store = get_long_term_memory()

    user_info = []

    try:
        # 用户个人信息获取
        preferences = store.search(("user_preferences", user_id))

        if preferences:
            pref_dict={}

            for item in preferences:
                #langgraph 储存数据时  自动用 |  连接 key，  namespace|user_id|item_id
                key_parts = item.key.split("|") if "|" in item.key else [item.key]
                item_id = key_parts[-1] if key_parts else item.key
                #去重
                pref_dict[item_id] = item.value

            #输出最新的值
            pref_text="\n".join([
                f"{value.get('key')}:{value.get('value')}"
                for value in pref_dict.values()
            ])

            user_info.append("【用户基本信息】\n"+pref_text)

            #获取用户医疗历史
            medical_history = store.search(("user_medical_history", user_id))

            if medical_history:
                medical_by_category = {}
                #遍历所有医疗历史
                for item in medical_history:
                    #获取类别  过敏史  手术史  家族病史
                    category = item.value.get("category", "unknown")
                    #获取内容
                    content = item.value.get("content", "")
                    if category not in medical_by_category:
                        medical_by_category[category] = []
                    medical_by_category[category].append(content)
                # 格式化输出
                history_lines=[]
                for category,contents in medical_by_category.items():
                    #如果只有一条 直接显示
                    if len(contents) == 1:
                        history_lines.append(f"{category}:{contents[0]}")
                    else:
                        items_text = "\n".join([
                            f"{i+1}.{c}" for i,c in enumerate(contents)
                        ])
                        history_lines.append(f"{category}:\n{items_text}")
                #拼接所有医疗历史
                medical_text = "\n".join(history_lines)
                user_info.append(" 【医疗历史】\n"+medical_text)

    except Exception as e:
        print(f"获取用户长记忆出错：{str(e)}")

    return "\n\n".join(user_info)   if user_info else ""

