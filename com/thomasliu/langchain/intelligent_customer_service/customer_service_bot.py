import os
from dotenv import load_dotenv
from openai import OpenAI
import chromadb
from chromadb.utils import embedding_functions
from document_loader import load_documents, split_text

load_dotenv()

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
        self.chroma_client = chromadb.PersistentClient(path="./chroma_db")
        MODEL_PATH = "/home/thomas/Downloads/models/Qwen3-Embedding-0.6B"
        self.emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=MODEL_PATH
        )
        self.collection = self.chroma_client.get_or_create_collection(
            name="customer_service_kb",
            embedding_function=self.emb_fn,
        )

    def initialize_data(self):
        if self.collection.count() == 0:
            print("正在初始化知识库...")
            text = load_documents()
            chunks = split_text(text)
            ids = [f"id_{i}" for i in range(len(chunks))]
            metadatas = [{"source": "policy_doc"} for _ in chunks]
            self.collection.add(documents=chunks, metadatas=metadatas, ids=ids)
            print(f"成功存储 {len(chunks)} 条向量数据")

    def answer(self, question: str) -> str:
        print(f"\n[用户提问]: {question}")
        results = self.collection.query(query_texts=[question], n_results=3)
        docs = results["documents"][0]
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
