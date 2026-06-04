import json
import uuid

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from tavily import TavilyClient

from app.agent.memory import get_long_term_memory
from app.config.settings import settings

#初始化 Tavily客户端
tavily = TavilyClient(api_key=settings.TAVILY_API_KEY)

@tool
def search_web(query:str) ->str:
    """
    搜索互联网获取实时信息
    参数 query 是搜索关键词
    当用户需要最新信息、新闻、医疗资讯等时使用此工具
    """
    try:
        result = tavily.search(query, max_results=3)

        summaries = [item["content"] for item in result.get("results", [])]

        return "\n".join(summaries) if summaries else "未找到相关的信息"
    except Exception as e:
        return f"搜索出错：{str(e)}"

#保存用户信息
@tool
def save_user_info(info_json:str,config:RunnableConfig) ->str:
    """
    保存或更新用户基本信息到长期记忆。
    参数 info_json 是 JSON 字符串，包含要保存的字段和值。
    当用户提供或修改个人信息时使用此工具。
    """
    try:
        info = json.loads(info_json)

        user_id = config["configurable"]["user_id"]

        store = get_long_term_memory()

        saved_items=[]

        field_names={
            "name":"姓名",
            "age":"年龄",
            "gender":"性别",
            "phone":"手机号码",
            "contract":"联系方式",
            "blood_type":"血型",
            "height":"身高",
            "weight":"体重"
        }

        for key,value in info.items():

            if value and str(value).strip():

                #构建命名空间
                namespace = ("user_preferences", user_id)

                #构建数据项 ID
                item_id = f"basic_info{key}"

                #获取字段的中文名称
                label = field_names.get(key, key)

                #保存 相同的 item_id 会覆盖旧数据
                store.put(namespace, item_id, {"key": label, "value": str(value).strip()})

                # 记录已保存的项
                saved_items.append(f"{label}:{value}")

        if saved_items:
            print(f"保存用户基本信息--ok:{'.'.join(saved_items)}")
            return f"保存用户基本信息--ok:{'.'.join(saved_items)}"
    except Exception as e:
        return f"保存用户信息出错：{str(e)}"

#保存用户医疗信息
@tool
def save_medical_info(category:str,content:str,config:RunnableConfig) ->str:
    """
    保存或更新用户医疗相关信息到长期记忆。
    参数 category 是信息类别（symptom/allergy/past_history/family_history/lifestyle/other）。
    参数 content 是具体内容。
    当用户提供或修改病史、过敏史、症状等医疗信息时使用此工具。
    """
    try:
        user_id = config["configurable"]["user_id"]

        store = get_long_term_memory()

        category_names={
            "symptom":"症状描述",
            "allergy":"过敏史",
            "past_history":"既往病史",
            "family_history":"家族病史",
            "lifestyle":"生活习惯",
            "other":"其他医疗信息"
        }

        label = category_names.get(category, category)

        namespace = ("user_medical_history", user_id)

        item_id = f"medical_{category}_{uuid.uuid4().hex[:8]}"

        store.put(namespace,item_id,{
            "category":label,
            "content":content,
            "timestamp":str(uuid.uuid1())
        })

        print(f"保存用户医疗信息 [{label}] :{content[:50]}")
        return f"已保存{label} :{content[:50]}..."

    except Exception as e:
        return f"保存用户医疗信息出错：{str(e)}"




