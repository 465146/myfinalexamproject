"""
意图分类推理脚本
加载微调后的模型，对输入文本进行意图预测
"""
import json
import torch
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForSequenceClassification

LABEL_LIST = ["course", "scholarship", "internship", "academic_affairs", "competition", "campus_life", "general"]
ID2LABEL = {i: label for i, label in enumerate(LABEL_LIST)}
LABEL2ID = {label: i for i, label in enumerate(LABEL_LIST)}


class IntentClassifier:
    """意图分类推理器"""

    def __init__(self, model_dir: str = None):
        if model_dir is None:
            model_dir = Path(__file__).parent / "output" / "best_model"
        else:
            model_dir = Path(model_dir)

        print(f"加载模型: {model_dir}")
        self.tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
        self.model = AutoModelForSequenceClassification.from_pretrained(str(model_dir))
        self.model.eval()

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        print(f"设备: {self.device}")

    def predict(self, text: str) -> dict:
        """
        预测单条文本的意图

        Returns:
            {
                "text": 原文,
                "intent": 意图标签,
                "confidence": 置信度,
                "probabilities": 各类别概率
            }
        """
        encoding = self.tokenizer(
            text,
            max_length=64,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )

        input_ids = encoding["input_ids"].to(self.device)
        attention_mask = encoding["attention_mask"].to(self.device)

        with torch.no_grad():
            outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
            logits = outputs.logits
            probs = torch.softmax(logits, dim=-1).cpu().numpy()[0]

        pred_idx = int(probs.argmax())
        confidence = float(probs[pred_idx])

        prob_dict = {ID2LABEL[i]: round(float(p), 4) for i, p in enumerate(probs)}

        return {
            "text": text,
            "intent": ID2LABEL[pred_idx],
            "confidence": round(confidence, 4),
            "probabilities": prob_dict,
        }

    def predict_batch(self, texts: list[str]) -> list[dict]:
        """批量预测"""
        return [self.predict(text) for text in texts]


def main():
    """交互式测试"""
    classifier = IntentClassifier()

    test_cases = [
        "怎么选课？",
        "奖学金有哪些种类？",
        "学校有招聘会吗？",
        "补考怎么报名？",
        "数学建模竞赛什么时候？",
        "图书馆开放时间？",
        "你好，你是谁？",
        "重修费怎么交？",
        "大创项目怎么申报？",
        "食堂在哪？",
        "转专业条件是什么？",
        "实习学分怎么认定？",
        "退选课程的截止时间",
        "国家奖学金多少钱",
        "VPN怎么用",
    ]

    print("\n" + "=" * 60)
    print("意图分类推理测试")
    print("=" * 60)

    for text in test_cases:
        result = classifier.predict(text)
        prob_str = " | ".join(
            f"{k}: {v:.2%}" for k, v in sorted(
                result["probabilities"].items(),
                key=lambda x: -x[1]
            )[:3]
        )
        print(f"\n输入: {text}")
        print(f"意图: {result['intent']} (置信度: {result['confidence']:.2%})")
        print(f"Top3: {prob_str}")


if __name__ == "__main__":
    main()
