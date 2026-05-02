"""NLP 任务模块
涉及3项自然语言处理典型任务：
1. 意图识别 - 优先使用微调BERT模型，fallback到DeepSeek
2. 信息抽取 - 从用户输入中抽取关键实体
3. 语义检索 - 基于知识库的语义相似度检索（通过 FastGPT RAG 实现）
"""
import json
from pathlib import Path
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

from app.services.llm_service import chat_deepseek, INTENT_SYSTEM_PROMPT, EXTRACT_SYSTEM_PROMPT
from app.core.config import get_settings

settings = get_settings()

# 意图类别定义
INTENT_CATEGORIES = {
    "course": "课程相关（选课、课程信息、课表、教学评价）",
    "scholarship": "奖学金相关（种类、申请条件、流程、评审）",
    "internship": "实习就业相关（实习信息、招聘、就业政策）",
    "academic_affairs": "教务事务（学籍、成绩、考试、补考重修、毕业）",
    "competition": "竞赛活动（学科竞赛、创新创业、社团活动）",
    "campus_life": "校园生活（住宿、食堂、图书馆、校历、交通）",
    "general": "一般闲聊或其他不明确意图",
}

# 意图对应的快捷回复模板
INTENT_QUICK_REPLIES = {
    "course": ["如何选课？", "有哪些通识课推荐？", "怎么查课表？", "课程退选规则是什么？"],
    "scholarship": ["奖学金有哪些种类？", "奖学金申请条件是什么？", "奖学金什么时候评审？", "国家奖学金怎么申请？"],
    "internship": ["如何找实习？", "学校有招聘会吗？", "就业协议怎么签？", "实习学分怎么认定？"],
    "academic_affairs": ["补考怎么报名？", "成绩怎么查询？", "学籍异动怎么办理？", "毕业要求是什么？"],
    "competition": ["有哪些学科竞赛？", "大创项目怎么申报？", "数学建模竞赛什么时候？", "互联网+竞赛怎么参加？"],
    "campus_life": ["图书馆开放时间？", "食堂在哪？", "宿舍怎么调换？", "校历在哪看？"],
    "general": [],
}

# ====== BERT 意图分类器 ======
LABEL_LIST = ["course", "scholarship", "internship", "academic_affairs", "competition", "campus_life", "general"]
ID2LABEL = {i: label for i, label in enumerate(LABEL_LIST)}

BERT_MODEL_DIR = Path(__file__).parent.parent.parent / "task" / "output" / "best_model"
_bert_tokenizer = None
_bert_model = None
_bert_device = None
_bert_loaded = False


def _load_bert_model():
    """懒加载 BERT 模型（仅在首次调用时加载）"""
    global _bert_tokenizer, _bert_model, _bert_device, _bert_loaded

    if _bert_loaded:
        return _bert_tokenizer is not None and _bert_model is not None

    _bert_loaded = True

    if not BERT_MODEL_DIR.exists():
        print(f"[BERT] 模型目录不存在: {BERT_MODEL_DIR}，将使用 DeepSeek fallback")
        return False

    try:
        _bert_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        _bert_tokenizer = AutoTokenizer.from_pretrained(str(BERT_MODEL_DIR), local_files_only=True)
        _bert_model = AutoModelForSequenceClassification.from_pretrained(str(BERT_MODEL_DIR), local_files_only=True)
        _bert_model.to(_bert_device)
        _bert_model.eval()
        print(f"[BERT] 意图分类模型加载成功 (device={_bert_device})")
        return True
    except Exception as e:
        print(f"[BERT] 模型加载失败: {e}，将使用 DeepSeek fallback")
        _bert_tokenizer = None
        _bert_model = None
        return False


def _bert_predict(text: str) -> dict | None:
    """使用 BERT 模型预测意图，返回 None 表示失败"""
    if not _load_bert_model():
        return None

    try:
        encoding = _bert_tokenizer(
            text, max_length=64, padding="max_length",
            truncation=True, return_tensors="pt",
        )
        input_ids = encoding["input_ids"].to(_bert_device)
        attention_mask = encoding["attention_mask"].to(_bert_device)

        with torch.no_grad():
            outputs = _bert_model(input_ids=input_ids, attention_mask=attention_mask)
            probs = torch.softmax(outputs.logits, dim=-1).cpu().numpy()[0]

        pred_idx = int(probs.argmax())
        confidence = float(probs[pred_idx])

        # 构造子意图描述
        sub_intent_map = {
            "course": "课程咨询",
            "scholarship": "奖学金查询",
            "internship": "实习就业咨询",
            "academic_affairs": "教务事务办理",
            "competition": "竞赛活动参与",
            "campus_life": "校园生活服务",
            "general": "一般闲聊",
        }

        return {
            "intent": ID2LABEL[pred_idx],
            "confidence": round(confidence, 4),
            "sub_intent": sub_intent_map.get(ID2LABEL[pred_idx], ""),
        }
    except Exception as e:
        print(f"[BERT] 推理失败: {e}")
        return None


# ====== JSON 响应解析工具 ======
def _parse_json_response(content: str) -> dict:
    """从 LLM 返回内容中解析 JSON（兼容 markdown 代码块包裹）"""
    content = content.strip()
    if content.startswith("```"):
        # 剥离 markdown 代码块 ```json ... ```
        lines = content.split("\n")
        # 去掉首行的 ```json 或 ```
        if lines[0].startswith("```"):
            lines = lines[1:]
        # 去掉末行的 ```
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        content = "\n".join(lines)
    return json.loads(content.strip())


# ====== 意图识别（BERT 优先，DeepSeek fallback） ======
def intent_recognition(query: str) -> dict:
    """
    NLP任务1: 意图识别
    优先使用微调BERT模型，若不可用则降级到DeepSeek大模型
    """
    # 优先尝试 BERT
    result = _bert_predict(query)
    if result is not None:
        result["method"] = "bert"
        return result

    # Fallback: DeepSeek
    print("[意图识别] BERT不可用，使用DeepSeek fallback")
    prompt = f"""请分析以下用户输入的意图，从给定的意图类别中选择最匹配的一个。

意图类别：
{json.dumps(INTENT_CATEGORIES, ensure_ascii=False, indent=2)}

用户输入：{query}

请以JSON格式返回结果，包含以下字段：
- intent: 意图类别key（如course, scholarship等）
- confidence: 置信度(0-1)
- sub_intent: 子意图描述（简短文字）

只返回JSON，不要其他内容。"""

    messages = [
        {"role": "system", "content": INTENT_SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    try:
        content = chat_deepseek(messages, temperature=0.1, response_format={"type": "json_object"})
        result = _parse_json_response(content)
        result["method"] = "deepseek"
        return result
    except Exception as e:
        print(f"意图识别失败: {e}")
        return {"intent": "general", "confidence": 0.5, "sub_intent": "无法识别", "method": "fallback"}


def information_extraction(query: str, intent: str = "") -> dict:
    """
    NLP任务2: 信息抽取
    从用户输入中抽取关键实体和参数
    """
    entity_types = {
        "course": ["课程名称", "教师姓名", "学期", "课程类型", "学分"],
        "scholarship": ["奖学金名称", "金额", "申请条件", "截止日期", "学院"],
        "internship": ["公司名称", "岗位", "薪资范围", "地点", "时间"],
        "academic_affairs": ["事务类型", "学期", "课程名称", "成绩", "日期"],
        "competition": ["竞赛名称", "级别", "报名时间", "参赛要求", "指导老师"],
        "campus_life": ["地点", "时间", "设施名称", "服务类型"],
        "general": ["关键词"],
    }

    types = entity_types.get(intent, entity_types["general"])

    prompt = f"""请从以下用户输入中抽取关键信息实体。

用户输入：{query}
需要抽取的实体类型：{json.dumps(types, ensure_ascii=False)}

请以JSON格式返回结果，格式为 {{"entities": [{{"type": "实体类型", "value": "实体值"}}]}}
只返回JSON，不要其他内容。如果没有找到对应实体，则不返回该类型。"""

    messages = [
        {"role": "system", "content": EXTRACT_SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    try:
        content = chat_deepseek(messages, temperature=0.1, response_format={"type": "json_object"})
        result = _parse_json_response(content)
        return result
    except Exception as e:
        print(f"信息抽取失败: {e}")
        return {"entities": []}
