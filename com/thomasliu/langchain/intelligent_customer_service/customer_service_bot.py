import os
from dotenv import load_dotenv
from openai import OpenAI
from pymilvus import MilvusClient
from sentence_transformers import SentenceTransformer
from document_loader import load_documents, split_text

load_dotenv()

MODEL_PATH = "/home/thomas/Downloads/models/Qwen3-Embedding-0.6B"
MILVUS_URI = "http://192.168.3.22:19530"
DIMENSION = 1024
COLLECTION_NAME = "customer_service_kb"

RAG_PROMPT_TEMPLATE = """你是一个客服助手。根据以下知识库内容回答用户问题。

知识库：
{context}

用户问题：{question}

注意：如果知识库中没有相关信息，请如实告知用户你不知道。"""


def call_deepseek(prompt: str) -> str:
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com"),
    )
    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "deepseek-v4-pro"),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        extra_body={"thinking": {"type": "disabled"}},
    )
    return resp.choices[0].message.content


class CustomerServiceBot:
    def __init__(self):
        self.model = SentenceTransformer(MODEL_PATH)
        self.client = MilvusClient(uri=MILVUS_URI)
        self._init_collection()

    def _init_collection(self):
        if not self.client.has_collection(COLLECTION_NAME):
            self.client.create_collection(
                collection_name=COLLECTION_NAME,
                dimension=DIMENSION,
                auto_id=True,
                metric_type="COSINE",
            )

    def initialize_data(self):
        stats = self.client.query(COLLECTION_NAME, output_fields=["count(*)"])
        count = stats[0]["count(*)"] if stats else 0
        if count == 0:
            print("正在初始化知识库...")
            text = load_documents()
            chunks = split_text(text)
            embeddings = self.model.encode(chunks).tolist()
            data = [
                {"vector": emb, "text": chunk, "source": "policy_doc"}
                for emb, chunk in zip(embeddings, chunks)
            ]
            self.client.insert(COLLECTION_NAME, data)
            print(f"成功存储 {len(chunks)} 条向量数据")

    def answer(self, question: str) -> str:
        print(f"\n[用户提问]: {question}")
        query_emb = self.model.encode(question).tolist()
        results = self.client.search(
            collection_name=COLLECTION_NAME,
            data=[query_emb],
            limit=3,
            output_fields=["text"],
        )
        docs = [r["entity"]["text"] for r in results[0]]
        context = "\n".join(docs)
        prompt = RAG_PROMPT_TEMPLATE.format(context=context, question=question)
        print("[系统思考中...]")
        answer = call_deepseek(prompt)
        print(f"[客服回答]: {answer}")
        return answer


if __name__ == "__main__":
    bot = CustomerServiceBot()
    bot.initialize_data()

    bot.answer("我想退货，需要满足什么条件？")
    bot.answer("我是金牌会员，退货运费怎么算？")
    bot.answer("你们老板是谁？")
