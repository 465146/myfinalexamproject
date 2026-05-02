"""LLM 服务 - 使用 OpenAI SDK 调用 DeepSeek"""
from openai import OpenAI
from app.core.config import get_settings

settings = get_settings()

# DeepSeek 客户端（OpenAI SDK 兼容）
deepseek_client = OpenAI(
    api_key=settings.DEEPSEEK_API_KEY,
    base_url=settings.DEEPSEEK_BASE_URL,
)

# 校园助手系统提示词
CAMPUS_SYSTEM_PROMPT = """你是"校园智能办事助手"，一个专门为高校学生提供校园生活咨询的AI助手。

你的职责范围包括：
1. 课程相关：选课指导、课程信息查询、课表解读
2. 奖学金：奖学金种类、申请条件、申请流程
3. 实习就业：实习信息、就业政策、招聘会信息
4. 教务事务：学籍管理、成绩查询、考试安排、补考重修
5. 竞赛活动：学科竞赛、创新创业、社团活动
6. 校园生活：住宿、食堂、图书馆、校历

回答要求：
- 基于知识库中的真实信息回答，不要编造
- 如果信息不确定，明确告知用户并建议咨询相关部门
- 回答要条理清晰，使用分点列举
- 涉及办事流程时，给出清晰的步骤指引"""

# 意图识别系统提示词
INTENT_SYSTEM_PROMPT = "你是一个意图识别系统，只返回JSON格式结果。"

# 信息抽取系统提示词
EXTRACT_SYSTEM_PROMPT = "你是一个信息抽取系统，只返回JSON格式结果。"


def chat_deepseek(messages: list[dict], temperature: float = 0.7, response_format: dict | None = None) -> str:
    """使用 OpenAI SDK 调用 DeepSeek 进行对话"""
    kwargs = dict(
        model=settings.DEEPSEEK_MODEL,
        messages=messages,
        temperature=temperature,
    )
    if response_format:
        kwargs["response_format"] = response_format
    completion = deepseek_client.chat.completions.create(**kwargs)
    return completion.choices[0].message.content
