"""校园智能办事助手 - 主入口"""
from pathlib import Path
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from app.api.routes import router
from app.core.config import get_settings

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    print("[校园智能办事助手] 启动中...")
    print(f"DeepSeek API: {settings.DEEPSEEK_BASE_URL}")
    print(f"FastGPT API: {settings.FASTGPT_BASE_URL}")
    yield
    print("[校园智能办事助手] 已关闭")

app = FastAPI(
    title="校园智能办事助手",
    description="基于 DeepSeek + FastGPT 的校园智能问答系统，集成意图识别、信息抽取、语义检索等NLP能力",
    version="1.0.0",
    lifespan=lifespan,
)

# 静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

# 注册API路由
app.include_router(router, prefix="/api")


@app.get("/", response_class=HTMLResponse)
async def home():
    """首页"""
    html_path = Path(__file__).parent / "templates" / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
