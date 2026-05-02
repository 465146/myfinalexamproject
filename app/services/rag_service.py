"""本地 RAG 服务 - TF-IDF 向量检索 + DeepSeek 生成"""
from __future__ import annotations

import json
import threading
from pathlib import Path

from app.core.config import get_settings
from app.services.llm_service import chat_deepseek

settings = get_settings()

# 项目根目录（rag_service.py → services → app → 项目根）
PROJECT_ROOT = Path(__file__).parent.parent.parent

# RAG 系统提示词模板（{context} 会被检索结果替换）
RAG_SYSTEM_PROMPT = """你是"校园智能办事助手"，一个专门为高校学生提供校园生活咨询的AI助手。

以下是与用户问题相关的校园知识库参考资料：

{context}

请严格根据以上参考资料回答用户的问题。回答要求：
- 优先使用参考资料中的真实信息回答，并引用具体的资料标题
- 如果参考资料中包含相关信息，请直接引用，不要编造
- 如果参考资料不足以完全回答问题，可以结合你的通用知识补充，但需说明哪些是资料中的信息
- 回答要条理清晰，使用分点列举
- 涉及办事流程时，给出清晰的步骤指引
- 在回答末尾以"📚 参考资料："开头，列出本次引用的资料标题"""


class LocalRAGService:
    """本地 RAG 服务：TF-IDF 向量化 + FAISS 检索 + DeepSeek 生成"""

    def __init__(self):
        self._vectorizer = None
        self.index = None
        self.documents: list[dict] = []
        self._is_ready: bool = False
        self._loading_lock = threading.Lock()
        self._loading_started: bool = False

    @property
    def is_ready(self) -> bool:
        return self._is_ready

    # ----- 知识库加载 -----

    def load_knowledge_bases(self) -> int:
        """加载所有知识库 JSON 文件，返回文档总数"""
        docs = []

        # 1. 校园知识库
        campus_path = PROJECT_ROOT / "data" / "campus_knowledge.json"
        if campus_path.exists():
            campus_data = json.loads(campus_path.read_text(encoding="utf-8"))
            for entry in campus_data:
                tags_str = "、".join(entry.get("tags", []))
                text = (
                    f"标题：{entry['title']}\n"
                    f"分类：{entry['category']}\n"
                    f"内容：{entry['content']}\n"
                    f"标签：{tags_str}"
                )
                docs.append({
                    "id": entry["id"],
                    "title": entry["title"],
                    "category": entry["category"],
                    "text": text,
                    "source": "校园知识库",
                })

        # 2. 竞赛知识库
        contest_path = PROJECT_ROOT / "crawler" / "output" / "竞赛知识库.txt"
        if contest_path.exists():
            contest_data = json.loads(contest_path.read_text(encoding="utf-8"))
            for i, entry in enumerate(contest_data):
                knowledge_text = entry.get("knowledge_text", "")
                if not knowledge_text:
                    continue
                docs.append({
                    "id": f"comp_{i}",
                    "title": entry.get("name", "未知竞赛"),
                    "category": "competition",
                    "text": knowledge_text.strip(),
                    "source": entry.get("source", "竞赛库"),
                })

        self.documents = docs
        return len(self.documents)

    # ----- TF-IDF 向量化 + FAISS 索引 -----

    def build_index(self):
        """TF-IDF 向量化所有文档并构建 FAISS 索引"""
        import faiss
        import numpy as np
        from sklearn.feature_extraction.text import TfidfVectorizer

        if not self.documents:
            raise RuntimeError("没有知识库文档，请先调用 load_knowledge_bases()")

        print(f"[RAG] 正在使用 TF-IDF 向量化 {len(self.documents)} 篇文档...")

        # TF-IDF: char n-grams (1~3 chars) 适合中文
        self._vectorizer = TfidfVectorizer(
            analyzer="char",
            ngram_range=(1, 3),
            max_features=5000,
        )
        texts = [doc["text"] for doc in self.documents]
        embeddings = self._vectorizer.fit_transform(texts)
        # 转为 dense array（稀疏 TF-IDF → dense FAISS 索引）
        embeddings_dense = embeddings.toarray().astype(np.float32)

        # L2 归一化后可计算余弦相似度
        norms = np.linalg.norm(embeddings_dense, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        embeddings_dense = embeddings_dense / norms

        dim = embeddings_dense.shape[1]
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(embeddings_dense)
        self._is_ready = True
        print(f"[RAG] TF-IDF + FAISS 索引构建完成，维度={dim}，文档数={len(self.documents)}")

    # ----- 检索 -----

    def retrieve(self, query: str, top_k: int | None = None) -> list[dict]:
        """检索与 query 最相关的 top_k 篇文档，返回带 score 字段的文档列表"""
        import numpy as np

        self._ensure_ready()

        if top_k is None:
            top_k = settings.RETRIEVAL_TOP_K

        q_vec = self._vectorizer.transform([query]).toarray().astype(np.float32)
        # L2 归一化
        q_norm = np.linalg.norm(q_vec)
        if q_norm > 0:
            q_vec = q_vec / q_norm

        scores, indices = self.index.search(q_vec, top_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.documents):
                continue
            doc = self.documents[idx].copy()
            doc["score"] = float(score)
            results.append(doc)

        return results

    # ----- RAG 对话 -----

    def rag_chat(self, messages: list[dict], temperature: float = 0.3) -> tuple[str, list[dict]]:
        """
        RAG 对话：检索 → 构建增强 Prompt → DeepSeek 生成
        返回 (answer, sources)
        """
        self._ensure_ready()

        # 从消息历史中提取最后一个用户问题
        question = ""
        for msg in reversed(messages):
            if msg["role"] == "user":
                question = msg["content"]
                break

        if not question:
            return "抱歉，无法识别你的问题。", []

        retrieved = self.retrieve(question)

        if not retrieved or retrieved[0]["score"] < settings.RETRIEVAL_MIN_SCORE:
            max_score = retrieved[0]["score"] if retrieved else 0
            print(f"[RAG] 检索质量不足 (max_score={max_score:.4f})，使用纯 DeepSeek 对话")
            sources = [{"source": "DeepSeek 直接回答", "content": "未匹配到相关知识库内容"}]
            answer = chat_deepseek(messages, temperature=temperature)
            return answer, sources

        context = self._format_context(retrieved)
        system_msg = RAG_SYSTEM_PROMPT.format(context=context)
        augmented_messages = [{"role": "system", "content": system_msg}] + messages

        answer = chat_deepseek(augmented_messages, temperature=temperature)

        sources = [
            {"source": doc["title"], "content": doc["text"][:200]}
            for doc in retrieved
        ]

        return answer, sources

    # ----- 内部方法 -----

    def _ensure_ready(self):
        """懒加载：首次调用时构建 TF-IDF 索引（无需 torch，秒级完成）"""
        if self._is_ready:
            return

        with self._loading_lock:
            if self._is_ready:
                return
            if not self._loading_started:
                self._loading_started = True
                print("[RAG] 首次使用，正在构建 TF-IDF + FAISS 索引...")
                self.build_index()
                print("[RAG] 本地 RAG 系统就绪")

    def _format_context(self, docs: list[dict]) -> str:
        """格式化检索文档为编号的上下文块"""
        parts = []
        for i, doc in enumerate(docs, 1):
            parts.append(
                f"[资料{i}] {doc['title']}\n"
                f"来源：{doc.get('source', '未知')} | 分类：{doc.get('category', '未知')}\n"
                f"{doc['text']}"
            )
        return "\n\n---\n\n".join(parts)


# ===== 模块级单例 =====

_rag_service: LocalRAGService | None = None


def get_rag_service() -> LocalRAGService:
    """获取或创建 RAG 服务单例"""
    global _rag_service
    if _rag_service is None:
        _rag_service = LocalRAGService()
    return _rag_service


def rag_chat(messages: list[dict], temperature: float = 0.3) -> tuple[str, list[dict]]:
    """便捷函数：使用本地 RAG 进行知识库问答，返回 (answer, sources)"""
    service = get_rag_service()
    return service.rag_chat(messages, temperature)
