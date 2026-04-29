"""RAG 服务 - FastGPT 知识库检索（通过 OpenAI SDK 调用）"""
from app.services.llm_service import fastgpt_client, chat_fastgpt


def rag_chat(messages: list[dict], temperature: float = 0.3) -> str:
    """
    通过 FastGPT 知识库进行 RAG 问答
    FastGPT 兼容 OpenAI 接口，会自动完成 检索+生成 流程
    """
    return chat_fastgpt(messages, temperature)


def is_fastgpt_available() -> bool:
    """检查 FastGPT 是否已配置"""
    return fastgpt_client is not None
