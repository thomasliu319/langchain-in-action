import json
import uuid
from typing import Any

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from tavily import TavilyClient

from app.agent.memory import get_long_term_memory
from app.config.settings import settings

# ==================== 工具调用可靠性基础 ====================

_MAX_RETRIES = 2


def _try_parse_json(raw: str, retries: int = _MAX_RETRIES) -> tuple[dict | None, str]:
    """带重试的 JSON 解析，返回 (data, error_msg)"""
    for attempt in range(1 + retries):
        try:
            return json.loads(raw), ""
        except json.JSONDecodeError as e:
            if attempt < retries:
                return None, (
                    f"JSON 格式错误（第 {attempt + 1} 次尝试）：{e}\n"
                    f"请确保输出为合法 JSON，例如 {{\"name\": \"张三\", \"age\": \"30\"}}"
                )
            return None, (
                f"JSON 解析失败（已重试 {retries} 次）：{e}\n"
                f"原始输入：{raw[:200]}\n"
                f"请检查：1) 键名是否用双引号包裹；2) 字符串值是否用双引号包裹；3) 无多余逗号"
            )


def _validate_fields(data: dict, allowed_fields: dict[str, str]) -> tuple[dict[str, Any], list[str]]:
    """过滤合法字段，返回 (valid_data, errors)"""
    valid = {}
    errors = []
    for key, value in data.items():
        if key not in allowed_fields:
            errors.append(f"未知字段「{key}」，合法字段：{list(allowed_fields.keys())}")
        elif not value or not str(value).strip():
            errors.append(f"字段「{key}」的值为空，已跳过")
        else:
            valid[key] = str(value).strip()
    return valid, errors


# ==================== 工具定义 ====================

tavily = TavilyClient(api_key=settings.TAVILY_API_KEY)

# 保存用户信息时允许的字段及其中文名
_USER_FIELDS = {
    "name": "姓名",
    "age": "年龄",
    "gender": "性别",
    "phone": "手机号码",
    "contract": "联系方式",
    "blood_type": "血型",
    "height": "身高",
    "weight": "体重",
}

# 保存医疗信息时允许的类别
_MEDICAL_CATEGORIES = {
    "symptom": "症状描述",
    "allergy": "过敏史",
    "past_history": "既往病史",
    "family_history": "家族病史",
    "lifestyle": "生活习惯",
    "other": "其他医疗信息",
}


@tool
def search_web(query: str, config: RunnableConfig | None = None) -> str:
    """
    搜索互联网获取实时信息。
    参数 query 是搜索关键词（越精确越好）。
    当用户需要最新信息、新闻、医疗资讯等时使用此工具。
    """
    for attempt in range(1 + _MAX_RETRIES):
        try:
            result = tavily.search(query, max_results=3)
            summaries = [item["content"] for item in result.get("results", [])]
            if summaries:
                return "\n\n".join(summaries)
            return f"未找到「{query}」的相关信息，请尝试更换关键词"
        except Exception as e:
            if attempt < _MAX_RETRIES:
                continue
            return (
                f"搜索「{query}」出错（已重试 {_MAX_RETRIES} 次）：{e}\n"
                f"建议：简化关键词或稍后重试"
            )


@tool
def save_user_info(info_json: str, config: RunnableConfig) -> str:
    """
    保存或更新用户基本信息到长期记忆。
    参数 info_json 是 JSON 字符串，格式为 {"字段名": "值"}。
    合法字段名：name(姓名), age(年龄), gender(性别), phone(手机号码),
               contract(联系方式), blood_type(血型), height(身高), weight(体重)。
    当用户提供或修改个人信息时使用此工具。
    """
    # --- 第 1 层：JSON 格式校验（带重试） ---
    info, err = _try_parse_json(info_json)
    if err:
        return f"[参数错误] {err}"

    # --- 第 2 层：字段合法性校验 ---
    valid_data, field_errors = _validate_fields(info, _USER_FIELDS)
    if field_errors:
        return f"[参数错误] {'；'.join(field_errors)}"

    # --- 第 3 层：执行业务逻辑 ---
    try:
        user_id = config["configurable"]["user_id"]
        store = get_long_term_memory()
        saved = []

        for key, value in valid_data.items():
            namespace = ("user_preferences", user_id)
            item_id = f"basic_info_{key}"
            label = _USER_FIELDS[key]
            store.put(namespace, item_id, {"key": label, "value": value})
            saved.append(f"{label}:{value}")

        print(f"保存用户基本信息 OK: {' | '.join(saved)}")
        return f"✅ 已保存：{'；'.join(saved)}"

    except Exception as e:
        return (
            f"[系统错误] 保存用户信息失败：{e}\n"
            f"请尝试用更简单的格式重新提交，或联系管理员。"
        )


@tool
def save_medical_info(category: str, content: str, config: RunnableConfig) -> str:
    """
    保存或更新用户医疗相关信息到长期记忆。
    参数 category 是信息类别，可选值：symptom(症状描述), allergy(过敏史),
                past_history(既往病史), family_history(家族病史),
                lifestyle(生活习惯), other(其他医疗信息)。
    参数 content 是具体内容。
    当用户提供或修改病史、过敏史、症状等医疗信息时使用此工具。
    """
    # --- 第 1 层：参数合法性校验 ---
    if category not in _MEDICAL_CATEGORIES:
        valid_cats = "、".join(f"「{k}」({v})" for k, v in _MEDICAL_CATEGORIES.items())
        return (
            f"[参数错误] 未知类别「{category}」。\n"
            f"合法类别：{valid_cats}\n"
            f"请选择其中一个类别重新调用。"
        )

    if not content or not content.strip():
        return "[参数错误] 内容不能为空，请提供具体信息后重试。"

    # --- 第 2 层：执行业务逻辑 ---
    try:
        user_id = config["configurable"]["user_id"]
        store = get_long_term_memory()
        label = _MEDICAL_CATEGORIES[category]
        namespace = ("user_medical_history", user_id)
        item_id = f"medical_{category}_{uuid.uuid4().hex[:8]}"

        store.put(namespace, item_id, {
            "category": label,
            "content": content.strip(),
            "timestamp": str(uuid.uuid1()),
        })

        print(f"保存用户医疗信息 [{label}]：{content[:60]}")
        return f"✅ 已保存{label}：{content[:60]}{'…' if len(content) > 60 else ''}"

    except Exception as e:
        return (
            f"[系统错误] 保存医疗信息失败：{e}\n"
            f"请稍后重试，或联系管理员。"
        )




