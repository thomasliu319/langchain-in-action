from typing import TypedDict, List

from langgraph.constants import END
from langgraph.graph import StateGraph


class RefundState(TypedDict, total=False):
    order_id: str
    amount: float
    reason: str
    approval_status: str # 'pending' | 'approved' | 'needs_review' | 'rejected'
    audit_log: List[str]


def initial_review_node(state: RefundState) -> RefundState:
    amount = float(state.get("amount", 0))
    log = list(state.get("audit_log", []))

    if amount < 100:
        log.append("系统自动审批：金额小于100,直接通过")
        return {"approval_status": "approved", "audit_log": log}
    else:
        log.append("系统自动审批：金额大于100,转交财务审核")
        return {"approval_status": "needs_review", "audit_log": log}


def finance_review_node(state: RefundState) -> RefundState:
    log = list(state.get("audit_log", []))
    log.append("财务审核：已确认退款金额无误，批准通过")
    return {"approval_status":"approved", "audit_log": log}

def route_logic(state: RefundState) -> RefundState:
    status = state.get("approval_status", "pending")
    if status == "approved":
        return "end"
    if status == "needs_review":
        return "finance"
    return "end"


def build_refund_workflow():
    wf = StateGraph(RefundState)
    wf.add_node("initial_review", initial_review_node)
    wf.add_node("finance_review", finance_review_node)

    wf.set_entry_point("initial_review")
    wf.add_conditional_edges(
        "initial_review",
        route_logic,
        {"end": END, "finance": "finance_review"}
    )
    wf.add_edge("finance_review", END)
    return wf.compile()


def demo():
    app = build_refund_workflow()

    case_small = {"order_id": "ORD-10001", "amount": 50, "reason": "误购", "approval_status": "pending",
                  "audit_log": []}
    case_big = {"order_id": "ORD-10002", "amount": 999, "reason": "质量问题", "approval_status": "pending",
                "audit_log": []}

    for case in (case_small, case_big):
        out = app.invoke(case)
        print("\n--- 输入 ---")
        print(case)
        print("--- 输出 ---")
        print(out)
        print("审批日志：")
        for line in out.get("audit_log", []):
            print(" -", line)


if __name__ == "__main__":
    demo()


