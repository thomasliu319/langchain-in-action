"""质量保障模块：目标追踪 / 上下文压缩 / 目标对齐 / 反思"""
import traceback

from langchain_core.messages import SystemMessage, HumanMessage

from app.agent.base import get_model

# ==================== 常量 ====================

_GOAL_EXTRACT_PROMPT = """
从用户的第一条消息中提取他的核心意图（一句话概括）。

输出格式（只输出这行）：
意图：<一句话描述用户想做什么>
"""

_ALIGNMENT_PROMPT = """
你是质量检查员，判断当前对话进展是否偏离了用户的原始目标。

【原始目标】
{original_goal}

【最新进展】
{latest_exchange}

如果回答以下任一问题为"是"，则结果为 DRIFTED：
1. 子智能体是否在做不属于它职责范围的事（如体检员在开药）？
2. 是否连续多轮没有推进目标？
3. 对话是否陷入无关的闲聊而忽略了主目标？

如果进展正常，结果为 ALIGNED。
如果上下文过长需要压缩，结果为 SUMMARIZE_NEEDED。

输出格式（只输出一行）：
判断：ALIGNED / DRIFTED / SUMMARIZE_NEEDED
理由：<一句话>
"""

_COMPRESS_PROMPT = """
你是一个医疗对话摘要器。将新对话合并到已有摘要中。

【已有摘要】
{existing_summary}

【新对话】
{new_conversation}

【要求】
1. 将新对话中的新信息合并到已有摘要中
2. 保留所有医疗相关事实（症状、病史、过敏史、诊断、处方、基本信息）
3. 按时间顺序组织
4. 保留用户已提供但尚未处理的需求
5. 压缩后的完整摘要控制在 500 字以内
6. 输出的开头标注「对话摘要」

合并后的摘要：
"""

# 达到此轮数触发上下文压缩
_COMPRESS_AFTER_TURNS = 3


# ==================== 核心函数 ====================


def extract_goal(messages: list, existing_goal: str | None = None) -> str:
    """从消息中提取用户意图，已有目标则直接返回"""
    if existing_goal:
        return existing_goal

    try:
        model = get_model()
        goal_msg = [SystemMessage(content=_GOAL_EXTRACT_PROMPT)] + messages
        resp = model.invoke(goal_msg)
        text = resp.content.strip()
        if "意图：" in text:
            return text.split("意图：", 1)[-1].strip()
        return text
    except Exception as e:
        print(f"目标提取失败：{e}")
        return messages[-1].content[:100] if messages else "未知"


def check_alignment(
    original_goal: str,
    messages: list,
) -> tuple[str, str]:
    """检查当前进展是否与原始目标对齐，返回 (signal, reason)"""
    if not original_goal:
        return "ALIGNED", ""

    try:
        # 取最近一轮的交互作为检查素材
        recent = "\n".join(
            f"{'用户' if isinstance(m, HumanMessage) else '助手'}: {m.content[:200]}"
            for m in messages[-4:]
        )

        model = get_model()
        prompt = _ALIGNMENT_PROMPT.format(original_goal=original_goal, latest_exchange=recent)
        resp = model.invoke([SystemMessage(content=prompt)])
        text = resp.content.strip()

        if "DRIFTED" in text:
            signal = "drifted"
        elif "SUMMARIZE_NEEDED" in text:
            signal = "summarize_needed"
        else:
            signal = "aligned"

        reason = ""
        if "理由：" in text:
            reason = text.split("理由：", 1)[-1].strip()
        return signal, reason

    except Exception as e:
        print(f"目标对齐检查失败：{e}")
        return "aligned", ""


def compress_context(
    messages: list,
    existing_summary: str = "",
    state: dict | None = None,
) -> str:
    """
    增量压缩：只压缩上次压缩之后的新消息，再合并到已有摘要。

    参数:
        messages: 全量消息列表
        existing_summary: 已有的 compressed_history
        state: state 字典（用于计算 from_index）

    返回:
        合并后的完整摘要
    """
    try:
        # 计算从哪条消息开始是新消息
        raw_turns = (state or {}).get("raw_turns_since_compress", 0)
        # 每条消息按 2 轮算（user + AI），取尾部最新的消息
        n_new = max(raw_turns * 2, 4)  # 至少取 4 条
        new_msgs = messages[-n_new:] if len(messages) > n_new else messages

        new_text = "\n".join(
            f"{'用户' if isinstance(m, HumanMessage) else '助手'}: {m.content[:500]}"
            for m in new_msgs
        )
        if len(new_text) < 100:
            return existing_summary

        model = get_model()

        if existing_summary:
            prompt = _COMPRESS_PROMPT.format(
                existing_summary=existing_summary,
                new_conversation=new_text,
            )
        else:
            prompt = _COMPRESS_PROMPT.format(
                existing_summary="（无）",
                new_conversation=new_text,
            )

        resp = model.invoke([SystemMessage(content=prompt)])
        return resp.content.strip()

    except Exception as e:
        print(f"上下文压缩失败：{e}")
        return existing_summary


def should_compress(state: dict) -> bool:
    """判断是否需要进行上下文压缩"""
    raw_turns = state.get("raw_turns_since_compress", 0)
    return raw_turns >= _COMPRESS_AFTER_TURNS


# ==================== Reflector 节点（用于 LangGraph）====================


def reflector_node(state: dict) -> dict:
    """
    反射器节点：每次子智能体执行完毕后运行。
    1. 检查目标对齐
    2. 判断是否需要压缩上下文
    3. 发出反射信号供路由决策
    """
    updates: dict = {"reflection_signal": "aligned", "last_reflection": ""}

    messages = state.get("messages", [])
    goal = state.get("original_goal") or ""

    try:
        # 第 1 步：提取目标（首次运行）
        if not goal:
            goal = extract_goal(messages)
            updates["original_goal"] = goal

        # 第 2 步：检查目标对齐
        alignment, reason = check_alignment(goal, messages)
        updates["reflection_signal"] = alignment
        updates["last_reflection"] = f"[{alignment}] {reason}".strip()

        # 第 3 步：判断是否需要压缩
        # 增量压缩：已有摘要 + 新消息
        raw_turns = state.get("raw_turns_since_compress", 0)
        if should_compress(state) or alignment == "summarize_needed":
            existing = state.get("compressed_history", "")
            summary = compress_context(messages, existing_summary=existing, state=state)
            if summary and summary != existing:
                updates["compressed_history"] = summary
                updates["raw_turns_since_compress"] = 0
        else:
            updates["raw_turns_since_compress"] = raw_turns + 1

        print(f" 【反射器】对齐={alignment} | 目标={goal[:50]}")
        if reason:
            print(f" 【反射器】理由={reason}")

    except Exception as e:
        print(f"反射器执行出错：{e}")
        print(traceback.format_exc())
        updates["reflection_signal"] = "aligned"

    return updates
