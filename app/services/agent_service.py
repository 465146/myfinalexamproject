"""智能体调度服务 - 根据意图调度不同处理流程，维护会话历史"""
import uuid
from typing import Dict, List, Optional
from app.nlp.tasks import (
    intent_recognition,
    information_extraction,
    INTENT_QUICK_REPLIES,
)
from app.services.llm_service import (
    chat_deepseek,
    CAMPUS_SYSTEM_PROMPT,
)
from app.services.rag_service import rag_chat
from app.utils.text import strip_markdown

# 服务端会话历史 {session_id: [messages]}
conversation_history: Dict[str, List[dict]] = {}


def _get_history(session_id: str, ai_type: str) -> list[dict]:
    """获取指定会话的历史记录"""
    key = f"{session_id}_{ai_type}"
    return conversation_history.get(key, [])


def _init_session(session_id: str, ai_type: str) -> list[dict]:
    """初始化会话，添加系统提示词"""
    key = f"{session_id}_{ai_type}"
    if key not in conversation_history:
        conversation_history[key] = [
            {"role": "system", "content": CAMPUS_SYSTEM_PROMPT}
        ]
    return conversation_history[key]


def clear_session(session_id: str):
    """清除指定会话的历史记录"""
    keys_to_delete = [k for k in conversation_history if k.startswith(f"{session_id}_")]
    for key in keys_to_delete:
        del conversation_history[key]
    return len(keys_to_delete) > 0


def _call_deepseek(session_id: str, question: str) -> tuple[str, list]:
    """调用 DeepSeek 并维护会话历史，返回 (answer, sources)"""
    history = _init_session(session_id, "deepseek")
    history.append({"role": "user", "content": question})
    answer = chat_deepseek(history, temperature=0.7)
    history.append({"role": "assistant", "content": answer})
    return answer, []


def process_query(
    question: str,
    session_id: str = "",
    ai_type: str = "rag",
) -> dict:
    """
    智能体主调度流程：
    1. 意图识别 → 确定用户意图类别
    2. 信息抽取 → 提取关键实体
    3. RAG问答 → 基于知识库上下文生成回答（带会话历史）
    4. 返回结构化结果
    """
    # 生成或使用现有会话ID
    if not session_id:
        session_id = str(uuid.uuid4())

    # Step 1: 意图识别
    intent_result = intent_recognition(question)
    intent = intent_result.get("intent", "general")

    # Step 2: 信息抽取
    extraction_result = information_extraction(question, intent)

    # Step 3: 选择 AI 类型进行对话（"fastgpt" 保持向后兼容）
    if ai_type in ("rag", "fastgpt"):
        history = _init_session(session_id, "rag")
        history.append({"role": "user", "content": question})

        try:
            answer, sources = rag_chat(history, temperature=0.3)
            history.append({"role": "assistant", "content": answer})
        except Exception as e:
            print(f"本地 RAG 调用失败，降级到 DeepSeek: {e}")
            answer, sources = _call_deepseek(session_id, question)
    else:
        answer, sources = _call_deepseek(session_id, question)

    # 获取推荐问题
    quick_replies = INTENT_QUICK_REPLIES.get(intent, [])

    return {
        "answer": strip_markdown(answer),
        "session_id": session_id,
        "ai_type": ai_type,
        "intent": intent_result,
        "entities": extraction_result.get("entities", []),
        "sources": sources,
        "quick_replies": quick_replies[:4],
    }
