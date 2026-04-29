"""API 路由 - 聊天、意图识别、信息抽取、语义检索等接口"""
import json
from fastapi import APIRouter, HTTPException
from app.models.schemas import ChatRequest, ChatResponse
from app.services.agent_service import process_query, clear_session
from app.nlp.tasks import (
    intent_recognition,
    information_extraction,
    INTENT_CATEGORIES,
    INTENT_QUICK_REPLIES,
)

router = APIRouter()


@router.get("/")
async def index():
    """健康检查"""
    return {"status": "ok", "service": "校园智能办事助手"}


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    智能问答接口
    - ai_type="fastgpt": 使用 FastGPT 知识库 RAG 问答
    - ai_type="deepseek": 使用 DeepSeek 直接对话
    服务端维护会话历史，前端只需传 session_id
    """
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=400, detail="问题不能为空")

    if request.ai_type not in ["fastgpt", "deepseek"]:
        raise HTTPException(status_code=400, detail="无效的 AI 类型，请使用 fastgpt 或 deepseek")

    try:
        result = process_query(
            question=request.question,
            session_id=request.session_id or "",
            ai_type=request.ai_type,
        )
        return ChatResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理请求时出错: {str(e)}")


@router.delete("/chat/{session_id}")
async def delete_conversation(session_id: str):
    """清除指定会话的历史记录"""
    if clear_session(session_id):
        return {"message": f"会话 {session_id} 的历史记录已清除"}
    raise HTTPException(status_code=404, detail="会话不存在")


@router.post("/intent")
async def analyze_intent(request: ChatRequest):
    """意图识别接口"""
    result = intent_recognition(request.question)
    return result


@router.post("/extract")
async def extract_info(request: ChatRequest):
    """信息抽取接口"""
    intent_result = intent_recognition(request.question)
    intent = intent_result.get("intent", "general")
    result = information_extraction(request.question, intent)
    return result


@router.get("/intents")
async def get_intents():
    """获取所有意图类别及推荐问题"""
    return {
        "categories": INTENT_CATEGORIES,
        "quick_replies": INTENT_QUICK_REPLIES,
    }


@router.get("/knowledge")
async def get_knowledge():
    """获取本地知识库内容"""
    try:
        with open("data/campus_knowledge.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        return {"total": len(data), "items": data}
    except Exception as e:
        return {"total": 0, "items": [], "error": str(e)}
