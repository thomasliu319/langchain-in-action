from typing import TypedDict, List

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from com.thomasliu.langchain.langgraph_demo.config import DeepSeekConfig


class AgentState(TypedDict, total=False):
    messages: List[BaseMessage]
    intent: str # "RAG" | "TOOL" | "REFUND"

def build_llm() -> ChatOpenAI:
    cfg = DeepSeekConfig.from_env()
    return ChatOpenAI(
        model=cfg.model,
        api_key=cfg.api_key,
        base_url=cfg.base_url,
        temperature=0.2,
    )


def intent_classifier(llm: ChatOpenAI):
    def _node(state: AgentState) -> AgentState:
        msg = state["messages"][-1].content
        prompt = (
            "你是企业级客服意图分类器。\n"
            "请把用户问题分类为三类之一：\n"
            "RAG（咨询/知识问答），TOOL（需要查订单/操作），REFUND（退款/敏感审批）。\n"
            "只输出一个单词：RAG 或 TOOL 或 REFUND。\n"
            f"用户问题：{msg}"
        )
        resp = llm.invoke([HumanMessage(content=prompt)])
        intent = resp.content.strip().upper()
        if intent not in {"RAG", "TOOL", "REFUND"}:
            intent = "RAG"
        return {"intent": intent}

    return _node

def rag_node(llm: ChatOpenAI):
    def _node(state: AgentState)-> AgentState:
        query = state["messages"][-1].content
        docs = "知识库：退款政策为 7 天无理由；超过 7 天需人工审核。"
        resp = llm.invoke([HumanMessage(content=f"基于背景知识：{docs}\n回答用户问题：{query}")])
        return {"messages": [resp]}

    return _node


def tool_node(_: ChatOpenAI):
    def _node(state: AgentState) -> AgentState:
        # 这里演示“工具调用结果”，你可以替换为真实 API
        return {"messages": [AIMessage(content="工具调用结果：订单 ORD-10001 状态=已发货。")]}

    return _node

def refund_node(_: ChatOpenAI):
    def _node(state: AgentState) -> AgentState:
        return {"messages": [AIMessage(content="退款属于敏感操作：已进入审批流程（示例）。")]}

    return _node


def router(state: AgentState) -> str:
    intent = state.get("intent", "RAG")
    if intent == "RAG":
        return "rag"
    if intent == "TOOL":
        return "tools"
    if intent == "REFUND":
        return "refund"
    return "rag"


def build_customer_service_graph():
    load_dotenv()
    llm = build_llm()

    g = StateGraph(AgentState)
    g.add_node("classifier", intent_classifier(llm))
    g.add_node("rag", rag_node(llm))
    g.add_node("tools", tool_node(llm))
    g.add_node("refund", refund_node(llm))

    g.set_entry_point("classifier")
    g.add_conditional_edges("classifier", router, {"rag": "rag", "tools":"tools", "refund":"refund"})
    g.add_edge("rag", END)
    g.add_edge("tools", END)
    g.add_edge("refund", END)
    return g.compile()


def chat_once(user_text: str) -> str:
    app = build_customer_service_graph()
    result = app.invoke({"messages": [HumanMessage(content=user_text)]})
    messages = result.get("messages", [])
    if messages:
        return messages[-1].content
    return "(no response)"


def demo():
    for q in ["退款政策是什么？", "帮我查一下订单 ORD-10001 的状态", "我要退款，金额 2000"]:
        ans = chat_once(q)
        print("\n用户：", q)
        print("客服：", ans)


if __name__ == "__main__":
    demo()
