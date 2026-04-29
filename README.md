# 校园智能办事助手

基于 **DeepSeek 大模型** + **FastGPT 知识库 RAG** 的校园智能问答系统。

## 功能特性

- **智能问答**：支持 FastGPT 知识库 RAG 问答 和 DeepSeek 直接对话两种模式
- **会话管理**：服务端维护会话历史，支持多轮对话上下文
- **意图识别**：自动识别用户查询意图（课程/奖学金/实习/教务/竞赛/生活）
- **信息抽取**：从用户输入中提取关键实体
- **快捷导航**：分类快捷入口，一键查询
- **分析面板**：实时展示 NLP 分析结果

## 技术栈

- **后端**：FastAPI + Python 3.12
- **大模型**：DeepSeek API（通过 OpenAI SDK 调用）
- **知识库 RAG**：FastGPT API（兼容 OpenAI SDK 接口）
- **前端**：原生 HTML/CSS/JS
- **NLP 任务**：意图识别、信息抽取、语义检索

## 核心设计

参考 OpenAI SDK 统一调用方式：
- **DeepSeek**：`OpenAI(api_key=..., base_url="https://api.deepseek.com")`
- **FastGPT**：`OpenAI(api_key=..., base_url="https://cloud.fastgpt.cn/api/v1")`，用 `APP_ID` 作为 `model` 参数
- **会话历史**：服务端用 `conversation_history` 字典维护，前端只需传 `session_id`

## 快速开始

### 1. 安装依赖

```bash
uv sync
```

### 2. 配置环境变量

编辑 `.env` 文件，填入你的 API Key：

```env
DEEPSEEK_API_KEY=sk-your-deepseek-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

FASTGPT_API_KEY=fastgpt-your-api-key
FASTGPT_BASE_URL=https://cloud.fastgpt.cn/api/v1
FASTGPT_APP_ID=your-app-id
```

### 3. 启动服务

```bash
uv run python main.py
```

访问 http://localhost:8000 即可使用。

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/chat` | POST | 智能问答（`ai_type`: fastgpt/deepseek） |
| `/api/chat/{session_id}` | DELETE | 清除会话历史 |
| `/api/intent` | POST | 意图识别 |
| `/api/extract` | POST | 信息抽取 |
| `/api/intents` | GET | 获取意图类别 |
| `/api/knowledge` | GET | 获取知识库内容 |

### 请求示例

```json
POST /api/chat
{
    "question": "如何选课？",
    "session_id": null,
    "ai_type": "fastgpt"
}
```

```json
响应：
{
    "answer": "选课分为预选、正选和退补选三个阶段...",
    "session_id": "xxxxxxxx",
    "ai_type": "fastgpt",
    "intent": {"intent": "course", "confidence": 0.95, "sub_intent": "选课流程"},
    "entities": [{"type": "事务类型", "value": "选课"}],
    "sources": [{"source": "FastGPT知识库", "content": "..."}],
    "quick_replies": ["如何选课？", "有哪些通识课推荐？"]
}
```

## NLP 任务说明

1. **意图识别**：使用 DeepSeek 对用户输入进行分类，识别为课程、奖学金、实习就业、教务事务、竞赛活动、校园生活等类别
2. **信息抽取**：使用 DeepSeek 从用户输入中提取课程名称、奖学金类型、时间等关键实体
3. **语义检索**：通过 FastGPT 的 Embedding 检索获取知识库中最相关的文档片段（RAG 流程内置）

## 项目结构

```
├── main.py                  # 应用入口
├── .env                     # 环境变量配置
├── app/
│   ├── api/
│   │   └── routes.py        # API 路由
│   ├── core/
│   │   └── config.py        # 配置管理
│   ├── models/
│   │   └── schemas.py       # 数据模型
│   ├── nlp/
│   │   └── tasks.py         # NLP任务（意图识别/信息抽取）
│   └── services/
│       ├── agent_service.py # 智能体调度（会话管理+流程编排）
│       ├── llm_service.py   # LLM服务（OpenAI SDK统一调用）
│       └── rag_service.py   # FastGPT RAG 服务
├── data/
│   └── campus_knowledge.json # 校园知识库数据
├── static/
│   ├── css/style.css        # 样式
│   └── js/app.js            # 交互逻辑
└── templates/
    └── index.html           # 前端页面
```
