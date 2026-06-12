"""
智能问答路由
============

基于知识库的智能问答接口。
"""

import logging
from typing import List, Optional

from fastapi import APIRouter

from api.schemas import QARequest
from agent.llm import create_llm
from knowledge.knowledge_base import KnowledgeBase

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_knowledge_context(question: str, competitors: Optional[List[str]] = None) -> str:
    """从知识库获取上下文"""
    try:
        kb = KnowledgeBase()

        if competitors:
            all_context = []
            for name in competitors:
                results = kb.search_competitors(query=question, top_k=3)
                for r in results:
                    all_context.append(r.get("document", ""))
            return "\n\n".join(all_context[:5])
        else:
            results = kb.search_competitors(query=question, top_k=5)
            return "\n\n".join(r.get("document", "") for r in results)
    except Exception as e:
        logger.warning(f"知识库查询失败: {e}")
        return ""


async def _ask_llm(question: str, context: str) -> str:
    """调用 LLM 回答问题"""
    prompt = f"""基于以下竞品知识库信息，回答用户的问题。如果知识库中没有相关信息，请说明。

知识库信息：
{context if context else "暂无相关信息"}

用户问题：{question}

请用中文回答，简洁准确："""

    llm = create_llm(temperature=0.3, max_tokens=2048)
    response = await llm.ainvoke(prompt)
    return response.content


@router.post("")
async def ask_question(req: QARequest):
    """提交智能问答"""
    context = _get_knowledge_context(req.question, req.competitors)
    answer = await _ask_llm(req.question, context)

    sources = []
    if context:
        sources.append("竞品知识库")
    if not context:
        sources.append("LLM 通用知识")

    logger.info(f"问答完成: {req.question[:50]}...")
    return {
        "code": 200,
        "data": {"answer": answer, "sources": sources},
        "message": "success",
    }
