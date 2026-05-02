"""校园智能办事助手 - 主入口"""
from pathlib import Path
from contextlib import asynccontextmanager
import threading

import uvicorn
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from app.api.routes import router
from app.core.config import get_settings
from app.db.session import init_db

settings = get_settings()

def _preload_nlp_models():
    """在后台线程预加载 NLP 模型"""
    try:
        from app.nlp.tasks import _load_bert_model
        print("[后台任务] 开始预加载 BERT 模型...")
        _load_bert_model()
        print("[后台任务] BERT 模型加载完成")
    except Exception as e:
        print(f"[后台任务] BERT 模型加载失败: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    print("[校园智能办事助手] 启动中...")
    print(f"DeepSeek API: {settings.DEEPSEEK_BASE_URL}")
    print(f"Database: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")

    # 初始化数据库
    init_db()
    print("[数据库] 表结构初始化完成")

    # 在后台线程预加载 NLP 模型（不阻塞启动）
    nlp_thread = threading.Thread(target=_preload_nlp_models, daemon=True)
    nlp_thread.start()
    print("[NLP] BERT 模型正在后台加载...")

    # 初始化本地 RAG 知识库（仅加载文档，模型首次使用时懒加载）
    from app.services.rag_service import get_rag_service
    rag = get_rag_service()
    doc_count = rag.load_knowledge_bases()
    print(f"[RAG] 已加载 {doc_count} 篇知识库文档（模型将在首次查询时加载）")

    yield
    print("[校园智能办事助手] 已关闭")

app = FastAPI(
    title="校园智能办事助手",
    description="基于 DeepSeek + 本地 RAG 的校园智能问答系统，集成意图识别、信息抽取、语义检索等NLP能力",
    version="1.0.0",
    lifespan=lifespan,
)

# 静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

# 注册API路由
app.include_router(router, prefix="/api")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """首页 - 需要登录"""
    # 检查是否有 token（从 cookie）
    token = request.cookies.get("access_token")

    if not token:
        # 未登录，重定向到登录页面
        return RedirectResponse(url="/login", status_code=302)

    # 验证 token 是否有效（检查是否在黑名单中）
    try:
        from app.utils.auth import decode_access_token
        payload = decode_access_token(token)
        if not payload:
            # Token 无效或已在黑名单中，清除 cookie 并重定向到登录页
            response = RedirectResponse(url="/login", status_code=302)
            response.delete_cookie(key="access_token", path="/")
            return response
    except Exception:
        # Token 验证出错，清除 cookie 并重定向到登录页
        response = RedirectResponse(url="/login", status_code=302)
        response.delete_cookie(key="access_token", path="/")
        return response

    # 已登录且 token 有效，显示主页
    html_path = Path(__file__).parent / "templates" / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """登录页面 - 如果已登录则跳转到主页"""
    # 检查是否有有效的 token
    token = request.cookies.get("access_token")
    if token:
        try:
            from app.utils.auth import decode_access_token
            payload = decode_access_token(token)
            if payload:
                # 已登录，直接跳转到主页
                return RedirectResponse(url="/", status_code=302)
        except Exception:
            pass

    # 未登录或 token 无效，显示登录页面
    html_path = Path(__file__).parent / "templates" / "login.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
