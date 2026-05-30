"""
第四讲：基于 RAG 的 Agent 智能体开发实战
整合 Milvus 向量知识库 + DeepSeek 函数调用 + ReAct 循环
"""
import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from pymilvus import MilvusClient
from sentence_transformers import SentenceTransformer
from document_loader import load_documents, split_text

load_dotenv()

# ─── 配置 ───
MODEL_PATH = "/home/thomas/Downloads/models/Qwen3-Embedding-0.6B"
MILVUS_URI = "http://192.168.3.22:19530"
DIMENSION = 1024
COLLECTION_NAME = "customer_service_kb"

llm_client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com"),
)
embed_model = SentenceTransformer(MODEL_PATH)
milvus = MilvusClient(uri=MILVUS_URI)

SYSTEM_PROMPT = """你是一个严谨的电商业务助手。
你有以下工具可用：
1. search_knowledge_base — 查询公司政策、退货规则、会员权益等
2. get_order_details — 查询订单状态和发货信息
3. process_refund — 提交退款申请（需要用户明确确认后才能调用）

规则：
- 禁止伪造订单数据，必须使用 get_order_details 查询
- 涉及退款等资金操作时，必须先确认用户意图，再调用工具
- 如果工具返回 Error，直接告诉用户错误原因，不要编造成功结果
"""

# ─── 工具函数 ───

def search_knowledge_base(query: str) -> str:
    """从知识库检索相关政策文档"""
    if not milvus.has_collection(COLLECTION_NAME):
        return "知识库为空，请先初始化数据"
    query_emb = embed_model.encode(query).tolist()
    results = milvus.search(
        collection_name=COLLECTION_NAME,
        data=[query_emb],
        limit=3,
        output_fields=["text"],
    )
    docs = [r["entity"]["text"] for r in results[0]]
    return "\n".join(docs) if docs else "未找到相关信息"


def get_order_details(order_id: str) -> str:
    """查询订单详情"""
    mock_db = {
        "ORD-123": {"status": "已发货", "delivery_date": "2023-12-01", "items": ["iPhone 15"]},
        "ORD-456": {"status": "待付款", "items": ["MacBook Pro"]},
    }
    result = mock_db.get(order_id)
    if result:
        return json.dumps(result, ensure_ascii=False)
    return json.dumps({"error": "订单不存在"})


def process_refund(order_id: str, reason: str) -> str:
    """提交退款申请"""
    print(f"  正在处理订单 {order_id} 的退款，原因：{reason}")
    return json.dumps({"status": "success", "message": "退款申请已提交人工审核"}, ensure_ascii=False)


# ─── 工具描述（DeepSeek 函数调用 JSON Schema） ───

agent_tools = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "当问题涉及退货政策、会员权益、运费规则等通用知识时使用",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词或问题"}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_order_details",
            "description": "根据订单号查询订单状态、发货信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "订单编号，如 ORD-123"}
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "process_refund",
            "description": "提交退款申请，需要用户明确确认后才能调用",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "订单编号"},
                    "reason": {"type": "string", "description": "退款原因"},
                },
                "required": ["order_id", "reason"],
            },
        },
    },
]

available_functions = {
    "search_knowledge_base": search_knowledge_base,
    "get_order_details": get_order_details,
    "process_refund": process_refund,
}


# ─── ReAct 循环 ───

def run_agent(user_input: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_input},
    ]
    step = 0
    while True:
        step += 1
        response = llm_client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "deepseek-v4-pro"),
            messages=messages,
            tools=agent_tools,
            tool_choice="auto",
            extra_body={"thinking": {"type": "disabled"}},
        )
        response_msg = response.choices[0].message
        tool_calls = response_msg.tool_calls

        if tool_calls:
            messages.append(response_msg)
            for tool_call in tool_calls:
                fn_name = tool_call.function.name
                fn_args = json.loads(tool_call.function.arguments)
                fn_call = available_functions[fn_name]
                print(f"  [Agent 动作 {step}] 调用: {fn_name}  参数: {fn_args}")
                fn_response = fn_call(**fn_args)
                print(f"  [工具返回 {step}] {fn_response}")
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": fn_name,
                    "content": str(fn_response),
                })
        else:
            print(f"\n🤖 [Agent 回答]: {response_msg.content}")
            return response_msg.content


# ─── 初始化知识库 ───

def init_knowledge_base():
    if not milvus.has_collection(COLLECTION_NAME):
        milvus.create_collection(
            collection_name=COLLECTION_NAME,
            dimension=DIMENSION,
            auto_id=True,
            metric_type="COSINE",
        )
    stats = milvus.query(COLLECTION_NAME, output_fields=["count(*)"])
    count = stats[0]["count(*)"] if stats else 0
    if count == 0:
        print("初始化知识库...")
        text = load_documents()
        chunks = split_text(text)
        embeddings = embed_model.encode(chunks).tolist()
        data = [
            {"vector": emb, "text": chunk, "source": "policy_doc"}
            for emb, chunk in zip(embeddings, chunks)
        ]
        milvus.insert(COLLECTION_NAME, data)
        print(f"知识库初始化完成，共 {len(chunks)} 条")


if __name__ == "__main__":
    init_knowledge_base()

    test_cases = [
        "我的订单 ORD-123 还没收到，是不是丢件了？还有你们的退款政策是啥？",
        "帮我查一下订单 ORD-456",
        "帮我退款订单 ORD-456，我不想要了",
    ]
    for question in test_cases:
        print(f"\n{'='*50}\n[用户]: {question}\n{'='*50}")
        run_agent(question)
