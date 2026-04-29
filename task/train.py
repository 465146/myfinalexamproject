"""
BERT 意图分类微调训练脚本
基座模型: hfl/chinese-roberta-wwm-ext (约 102M 参数)
任务: 7 分类 (course, scholarship, internship, academic_affairs, competition, campus_life, general)
"""
import json
import os
import numpy as np
from pathlib import Path

import torch
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
    EarlyStoppingCallback,
)
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    accuracy_score,
    f1_score,
)

# ============ 配置 ============
BASE_MODEL = "BAAI/bge-small-zh-v1.5"  # 也可用 bert-base-chinese
NUM_LABELS = 7
MAX_LEN = 64  # 校园问句一般很短
BATCH_SIZE = 32
LEARNING_RATE = 2e-5
NUM_EPOCHS = 10
WARMUP_RATIO = 0.1
WEIGHT_DECAY = 0.01
SEED = 42

LABEL_LIST = ["course", "scholarship", "internship", "academic_affairs", "competition", "campus_life", "general"]
LABEL2ID = {label: i for i, label in enumerate(LABEL_LIST)}
ID2LABEL = {i: label for i, label in enumerate(LABEL_LIST)}

DATA_DIR = Path(__file__).parent / "data"
OUTPUT_DIR = Path(__file__).parent / "output"


# ============ 数据集 ============
class IntentDataset(Dataset):
    """意图分类数据集"""

    def __init__(self, data_path: str, tokenizer, max_len: int = 64):
        with open(data_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        item = self.data[idx]
        text = item["text"]
        label = LABEL2ID[item["label"]]

        encoding = self.tokenizer(
            text,
            max_length=self.max_len,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )

        return {
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "labels": torch.tensor(label, dtype=torch.long),
        }


# ============ 评估指标 ============
def compute_metrics(eval_pred):
    """计算评估指标"""
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)

    acc = accuracy_score(labels, preds)
    f1_macro = f1_score(labels, preds, average="macro")
    f1_weighted = f1_score(labels, preds, average="weighted")

    return {
        "accuracy": acc,
        "f1_macro": f1_macro,
        "f1_weighted": f1_weighted,
    }


# ============ 训练入口 ============
def train():
    """主训练流程"""
    print(f"基座模型: {BASE_MODEL}")
    print(f"分类数: {NUM_LABELS}")
    print(f"标签映射: {LABEL2ID}")
    print(f"输出目录: {OUTPUT_DIR}")
    print("-" * 50)

    # 1. 加载 tokenizer 和模型
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(
        BASE_MODEL,
        num_labels=NUM_LABELS,
        id2label=ID2LABEL,
        label2id=LABEL2ID,
    )

    # 打印模型参数量
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"总参数量: {total_params:,}")
    print(f"可训练参数量: {trainable_params:,}")
    print("-" * 50)

    # 2. 加载数据
    train_dataset = IntentDataset(DATA_DIR / "train.json", tokenizer, MAX_LEN)
    val_dataset = IntentDataset(DATA_DIR / "val.json", tokenizer, MAX_LEN)
    print(f"训练集: {len(train_dataset)} 条")
    print(f"验证集: {len(val_dataset)} 条")
    print("-" * 50)

    # 3. 训练参数
    training_args = TrainingArguments(
        output_dir=str(OUTPUT_DIR / "checkpoints"),
        num_train_epochs=NUM_EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        per_device_eval_batch_size=BATCH_SIZE,
        learning_rate=LEARNING_RATE,
        weight_decay=WEIGHT_DECAY,
        warmup_ratio=WARMUP_RATIO,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1_macro",
        greater_is_better=True,
        logging_dir=str(OUTPUT_DIR / "logs"),
        logging_steps=10,
        seed=SEED,
        fp16=torch.cuda.is_available(),  # GPU 可用时开启半精度
        dataloader_num_workers=0,
        report_to="none",  # 不上传到 wandb 等
    )

    # 4. Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=3)],
    )

    # 5. 开始训练
    print("开始训练...")
    train_result = trainer.train()

    # 6. 保存最佳模型
    best_model_dir = OUTPUT_DIR / "best_model"
    trainer.save_model(str(best_model_dir))
    tokenizer.save_pretrained(str(best_model_dir))
    print(f"\n最佳模型已保存到: {best_model_dir}")

    # 7. 训练指标
    metrics = train_result.metrics
    trainer.log_metrics("train", metrics)
    trainer.save_metrics("train", metrics)
    trainer.save_state()

    # 8. 在验证集上评估
    print("\n===== 验证集评估 =====")
    eval_metrics = trainer.evaluate()
    trainer.log_metrics("eval", eval_metrics)
    trainer.save_metrics("eval", eval_metrics)

    # 9. 在测试集上评估
    test_dataset = IntentDataset(DATA_DIR / "test.json", tokenizer, MAX_LEN)
    print("\n===== 测试集评估 =====")
    test_metrics = trainer.evaluate(test_dataset)
    trainer.log_metrics("test", test_metrics)
    trainer.save_metrics("test", test_metrics)

    # 10. 详细分类报告
    print("\n===== 详细分类报告 =====")
    predictions = trainer.predict(test_dataset)
    preds = np.argmax(predictions.predictions, axis=-1)
    labels = predictions.label_ids

    report = classification_report(
        labels, preds,
        target_names=LABEL_LIST,
        digits=4,
    )
    print(report)

    # 保存报告
    with open(OUTPUT_DIR / "classification_report.txt", "w", encoding="utf-8") as f:
        f.write(f"基座模型: {BASE_MODEL}\n")
        f.write(f"训练数据量: {len(train_dataset)}\n")
        f.write(f"验证数据量: {len(val_dataset)}\n")
        f.write(f"测试数据量: {len(test_dataset)}\n\n")
        f.write(report)
        f.write(f"\n混淆矩阵:\n")
        cm = confusion_matrix(labels, preds)
        f.write(f"标签: {LABEL_LIST}\n")
        f.write(str(cm))

    print(f"\n分类报告已保存到: {OUTPUT_DIR / 'classification_report.txt'}")
    print("训练完成!")


if __name__ == "__main__":
    train()
