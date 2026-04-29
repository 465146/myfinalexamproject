# BERT 意图分类微调

## 概述

基于 `hfl/chinese-roberta-wwm-ext` (约 102M 参数) 微调的校园意图分类模型。

## 意图类别

| 标签 | 含义 |
|------|------|
| course | 课程相关（选课、课表、教学评价） |
| scholarship | 奖学金相关 |
| internship | 实习就业相关 |
| academic_affairs | 教务事务（学籍、成绩、考试） |
| competition | 竞赛活动 |
| campus_life | 校园生活（住宿、食堂、图书馆） |
| general | 一般闲聊 |

## 使用步骤

### 1. 安装依赖

```bash
pip install torch transformers scikit-learn
```

### 2. 生成训练数据

```bash
cd task
python generate_data.py
```

会在 `data/` 目录生成 `train.json`、`val.json`、`test.json`。

### 3. 训练

```bash
python train.py
```

- 默认 10 个 epoch，早停 patience=3
- 支持 GPU (fp16) 和 CPU
- 最佳模型保存在 `output/best_model/`

### 4. 推理测试

```bash
python predict.py
```

## 文件结构

```
task/
├── generate_data.py     # 生成训练数据
├── train.py             # 训练脚本
├── predict.py           # 推理脚本
├── data/                # 训练数据 (运行 generate_data.py 后生成)
│   ├── train.json
│   ├── val.json
│   └── test.json
└── output/              # 训练产出 (运行 train.py 后生成)
    ├── best_model/      # 最佳模型权重 + tokenizer
    ├── checkpoints/     # 训练检查点
    ├── logs/            # 训练日志
    └── classification_report.txt
```
