"""
ReAct Agent 服务：封装 agent_rag.py 中的 Agent 循环
支持知识库检索、订单查询、退款处理等工具
"""
import os
import json
from openai import OpenAI
from pymilvus import MilvusClient
from sentence_transformers import SentenceTransformer

from ..config import settings

# ─── 全局惰性加载 ───
_embed_model = None
_milvus = None
_llm_client = None

# Mock 订单数据
MOCK_ORDERS = {
    "ORD-123": {"status": "已发货", "product": "智能眼部按摩器 Eyeris 1", "amount": 599.00, "date": "2025-05-20"},
    "ORD-456": {"status": "待发货", "product": "替换硅胶垫", "amount": 39.00, "date": "2025-05-28"},
}


def _get_embed_model():
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer(settings.EMB_MODEL_PATH)
    return _embed_model


def _get_milvus():
    global _milvus
    if _milvus is None:
        _milvus = MilvusClient(uri=settings.MILVUS_URI)
    return _milvus


def _get_llm():
    global _llm_client
    if _llm_client is None:
        _llm_client = OpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL)
    return _llm_client


# ─── 工具函数 ───

def search_knowledge_base(query: str) -> str:
    """从知识库检索与 query 相关的文档内容"""
    model = _get_embed_model()
    client = _get_milvus()
    q_emb = model.encode(query).tolist()
    results = client.search(collection_name=settings.KB_COLLECTION, data=[q_emb], limit=3, output_fields=["text"])
    if not results or not results[0]:
        return "未找到相关信息"
    return "\n".join(r["entity"]["text"] for r in results[0])


def get_order_details(order_id: str) -> str:
    """根据订单号查询订单详情"""
    order = MOCK_ORDERS.get(order_id)
    if not order:
        return json.dumps({"error": f"未找到订单 {order_id}"}, ensure_ascii=False)
    return json.dumps(order, ensure_ascii=False)


def process_refund(order_id: str, reason: str) -> str:
    """为指定订单提交退款申请"""
    if order_id not in MOCK_ORDERS:
        return json.dumps({"error": f"未找到订单 {order_id}"}, ensure_ascii=False)
    return json.dumps({"status": "success", "order_id": order_id, "message": f"退款申请已提交: {reason}"}, ensure_ascii=False)


TOOL_DEFINITIONS = [
    {"type": "function", "function": {"name": "search_knowledge_base", "description": "搜索知识库查找发票信息、商品明细、产品规格、退换货政策等所有文档内容", "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "搜索关键词，如发票号码、商品名、订单号等"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "get_order_details", "description": "查询订单详情（仅限 ORD-123 和 ORD-456）", "parameters": {"type": "object", "properties": {"order_id": {"type": "string", "description": "订单号"}}, "required": ["order_id"]}}},
    {"type": "function", "function": {"name": "process_refund", "description": "提交退款申请", "parameters": {"type": "object", "properties": {"order_id": {"type": "string", "description": "订单号"}, "reason": {"type": "string", "description": "退款原因"}}, "required": ["order_id", "reason"]}}},
]

AVAILABLE_FUNCTIONS = {
    "search_knowledge_base": search_knowledge_base,
    "get_order_details": get_order_details,
    "process_refund": process_refund,
}

SYSTEM_PROMPT = (
    "你是一个智能客服助手。\n"
    "规则：\n"
    "1. 用工具获取信息来回答，不要凭空回答。\n"
    "2. 不要猜测用户意图来决定用哪个工具，不确定时可先搜知识库。\n"
    "3. 如果某个工具返回空或无帮助，换另一个工具再试。\n"
    "4. 拿到结果后用一两句精炼的话回答核心问题，不要罗列原始数据。"
)


# ─── 知识库初始化 ───

def init_knowledge_base():
    """如果集合不存在或为空，初始化知识库"""
    client = _get_milvus()
    if not client.has_collection(settings.KB_COLLECTION):
        client.create_collection(collection_name=settings.KB_COLLECTION, dimension=settings.EMBED_DIM, auto_id=True, metric_type="COSINE")

    stats = client.query(settings.KB_COLLECTION, output_fields=["count(*)"])
    if stats and stats[0]["count(*)"] > 0:
        return {"status": "ok", "message": "知识库已存在且有数据"}

    # 加载模拟文档
    from ..services.kb_service import load_policy_docs
    chunks = load_policy_docs()
    if not chunks:
        return {"status": "error", "message": "无法加载文档"}

    embeddings = _get_embed_model().encode(chunks).tolist()
    data = [{"vector": emb, "text": chunk, "source": "policy_doc"} for emb, chunk in zip(embeddings, chunks)]
    client.insert(settings.KB_COLLECTION, data)
    return {"status": "ok", "message": f"知识库初始化完成，写入 {len(chunks)} 条"}


# ─── Agent 主循环（同步） ───

def run_agent(user_input: str, messages: list | None = None) -> str:
    """执行 ReAct Agent 循环，返回最终回答"""
    llm = _get_llm()
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    if messages:
        msgs.extend(messages)
    msgs.append({"role": "user", "content": user_input})
    return _react_loop(llm, msgs)


def _react_loop(llm: OpenAI, messages: list) -> str:
    """ReAct 循环：LLM 决定调用工具或直接回答"""
    max_iterations = 10
    for _ in range(max_iterations):
        resp = llm.chat.completions.create(
            model=settings.OPENAI_MODEL, messages=messages,
            tools=TOOL_DEFINITIONS, tool_choice="auto",
            temperature=0.3,
            extra_body={"thinking": {"type": "disabled"}},
        )
        choice = resp.choices[0]
        if choice.finish_reason == "stop":
            return choice.message.content or ""
        if choice.finish_reason == "tool_calls":
            messages.append(choice.message)
            for tc in choice.message.tool_calls:
                fn_name = tc.function.name
                fn_args = json.loads(tc.function.arguments)
                fn = AVAILABLE_FUNCTIONS.get(fn_name)
                if fn:
                    result = fn(**fn_args)
                else:
                    result = json.dumps({"error": f"Unknown tool: {fn_name}"})
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
    return "抱歉，处理超时，请重试。"


# ─── Agent 流式输出（供 SSE 使用） ───

def run_agent_stream(user_input: str, messages: list | None = None):
    """ReAct Agent 流式版本：产出结构化事件（thinking / token）"""
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    if messages:
        msgs.extend(messages)
    msgs.append({"role": "user", "content": user_input})

    llm = _get_llm()
    max_iterations = 10
    for iteration in range(max_iterations):
        resp = llm.chat.completions.create(
            model=settings.OPENAI_MODEL, messages=msgs,
            tools=TOOL_DEFINITIONS, tool_choice="auto",
            temperature=0.3,
            extra_body={"thinking": {"type": "disabled"}},
        )
        choice = resp.choices[0]
        if choice.finish_reason == "stop":
            text = choice.message.content or ""
            # stream final answer token by token
            import re
            tokens = re.split(r'(?<=[，。！？])', text)
            for token in tokens:
                if token.strip():
                    yield {"type": "token", "content": token}
            return

        if choice.finish_reason == "tool_calls":
            msgs.append(choice.message)
            for tc in choice.message.tool_calls:
                fn_name = tc.function.name
                fn_args = json.loads(tc.function.arguments)
                yield {"type": "thinking", "content": f"调用工具: {fn_name}"}
                fn = AVAILABLE_FUNCTIONS.get(fn_name)
                if fn:
                    result = fn(**fn_args)
                else:
                    result = json.dumps({"error": f"Unknown tool: {fn_name}"})
                has_data = "未找到" not in result and "error" not in result
                summary = "已找到相关信息" if has_data else "未找到相关信息"
                yield {"type": "thinking", "content": f"工具返回: {summary}"}
                msgs.append({"role": "tool", "tool_call_id": tc.id, "content": result})
    yield {"type": "token", "content": "抱歉，处理超时，请重试。"}
