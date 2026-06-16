"""
智能问答路由
============

支持对话记忆、多源检索（知识库 + 报告 + 分析结果）。
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import (
    QARequest, QAResponse, SourceItem,
    ChatSessionResponse, ChatMessageResponse, ChatSessionCreateRequest,
    ApiResponse,
)
from api.auth import require_user
from api.database import (
    UserORM, CompetitorORM, ReportORM, AnalysisTaskORM,
    ChatSessionORM, ChatMessageORM,
    get_session,
)
from agent.llm import create_llm
from knowledge.knowledge_base import KnowledgeBase

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== 会话管理 ====================


@router.get("/sessions", response_model=ApiResponse)
async def list_sessions(
    user: UserORM = Depends(require_user),
    db: AsyncSession = Depends(get_session),
):
    """获取会话列表"""
    stmt = (
        select(
            ChatSessionORM.id,
            ChatSessionORM.title,
            ChatSessionORM.created_at,
            ChatSessionORM.updated_at,
            func.count(ChatMessageORM.id).label("message_count"),
        )
        .outerjoin(ChatMessageORM, ChatSessionORM.id == ChatMessageORM.session_id)
        .where(ChatSessionORM.user_id == user.id)
        .group_by(ChatSessionORM.id)
        .order_by(desc(ChatSessionORM.updated_at))
    )
    result = await db.execute(stmt)
    sessions = []
    for row in result:
        sessions.append({
            "id": row.id,
            "title": row.title,
            "message_count": row.message_count,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        })
    return {"code": 200, "data": sessions, "message": "success"}


@router.post("/sessions", response_model=ApiResponse)
async def create_session(
    req: ChatSessionCreateRequest,
    user: UserORM = Depends(require_user),
    db: AsyncSession = Depends(get_session),
):
    """创建新会话"""
    session = ChatSessionORM(user_id=user.id, title=req.title)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return {
        "code": 200,
        "data": {
            "id": session.id,
            "title": session.title,
            "created_at": session.created_at.isoformat() if session.created_at else None,
        },
        "message": "success",
    }


@router.delete("/sessions/{session_id}", response_model=ApiResponse)
async def delete_session(
    session_id: str,
    user: UserORM = Depends(require_user),
    db: AsyncSession = Depends(get_session),
):
    """删除会话及其消息"""
    stmt = select(ChatSessionORM).where(
        ChatSessionORM.id == session_id,
        ChatSessionORM.user_id == user.id,
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 删除会话下的所有消息
    await db.execute(
        ChatMessageORM.__table__.delete().where(ChatMessageORM.session_id == session_id)
    )
    await db.delete(session)
    await db.commit()
    return {"code": 200, "data": None, "message": "删除成功"}


@router.get("/sessions/{session_id}/messages", response_model=ApiResponse)
async def list_messages(
    session_id: str,
    user: UserORM = Depends(require_user),
    db: AsyncSession = Depends(get_session),
):
    """获取会话消息列表"""
    # 验证会话归属
    stmt = select(ChatSessionORM).where(
        ChatSessionORM.id == session_id,
        ChatSessionORM.user_id == user.id,
    )
    result = await db.execute(stmt)
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="会话不存在")

    msg_stmt = (
        select(ChatMessageORM)
        .where(ChatMessageORM.session_id == session_id)
        .order_by(ChatMessageORM.created_at)
    )
    msg_result = await db.execute(msg_stmt)
    messages = []
    for msg in msg_result.scalars():
        messages.append({
            "id": msg.id,
            "session_id": msg.session_id,
            "role": msg.role,
            "content": msg.content,
            "sources": msg.sources or [],
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
        })
    return {"code": 200, "data": messages, "message": "success"}


# ==================== 智能问答 ====================


async def _build_conversation_context(
    session_id: str,
    db: AsyncSession,
    max_rounds: int = 5,
) -> str:
    """构建对话历史上下文"""
    stmt = (
        select(ChatMessageORM)
        .where(ChatMessageORM.session_id == session_id)
        .order_by(desc(ChatMessageORM.created_at))
        .limit(max_rounds * 2)
    )
    result = await db.execute(stmt)
    messages = list(result.scalars())
    messages.reverse()

    if not messages:
        return ""

    parts = []
    for msg in messages:
        role = "用户" if msg.role == "user" else "助手"
        parts.append(f"{role}: {msg.content}")
    return "\n".join(parts)


async def _search_knowledge(
    question: str,
    user_id: str,
    db: AsyncSession,
    top_k: int = 5,
) -> tuple[str, List[SourceItem]]:
    """从知识库检索"""
    try:
        kb = KnowledgeBase()
        results = kb.search_competitors(query=question, top_k=top_k, user_id=user_id)

        if not results:
            return "", []

        # 收集 competitor_id -> name 映射
        comp_ids = set()
        for r in results:
            cid = r.get("metadata", {}).get("competitor_id")
            if cid:
                comp_ids.add(cid)

        name_map = {}
        if comp_ids:
            stmt = select(CompetitorORM.id, CompetitorORM.name).where(
                CompetitorORM.id.in_(list(comp_ids)),
                CompetitorORM.user_id == user_id,
            )
            result = await db.execute(stmt)
            for row in result:
                name_map[row.id] = row.name

        context_parts = []
        sources: List[SourceItem] = []
        for r in results:
            meta = r.get("metadata", {})
            cid = meta.get("competitor_id", "")
            comp_name = name_map.get(cid, cid)
            doc = r.get("document", "")
            doc_type = meta.get("type", "web_page")
            doc_type_label = {
                "company_info": "公司信息",
                "product": "产品信息",
                "web_page": "网页内容",
                "user_review": "用户评价",
            }.get(doc_type, doc_type)

            context_parts.append(f"[{comp_name} - {doc_type_label}]\n{doc}")
            sources.append(SourceItem(
                type="knowledge_base",
                competitor=comp_name,
                title=f"{comp_name} - {doc_type_label}",
                snippet=doc[:120],
                relevance=r.get("relevance", None),
            ))

        return "\n\n".join(context_parts), sources
    except Exception as e:
        logger.warning(f"知识库检索失败: {e}")
        return "", []


async def _search_reports(
    question: str,
    user_id: str,
    db: AsyncSession,
    top_k: int = 3,
) -> tuple[str, List[SourceItem]]:
    """从已有报告中检索"""
    try:
        stmt = (
            select(ReportORM)
            .where(ReportORM.user_id == user_id)
            .order_by(desc(ReportORM.created_at))
            .limit(top_k)
        )
        result = await db.execute(stmt)
        reports = list(result.scalars())

        if not reports:
            return "", []

        # 简单关键词匹配（生产环境可用向量检索替代）
        keywords = question.lower().split()
        context_parts = []
        sources: List[SourceItem] = []

        for report in reports:
            content = report.content or ""
            # 找包含关键词的段落
            paragraphs = [p for p in content.split("\n\n") if any(k in p.lower() for k in keywords)]
            snippet = paragraphs[0][:500] if paragraphs else content[:300]
            title = report.title

            context_parts.append(f"[报告: {title}]\n{snippet}")
            sources.append(SourceItem(
                type="report",
                competitor=None,
                title=title,
                snippet=snippet[:200],
            ))

        return "\n\n".join(context_parts), sources
    except Exception as e:
        logger.warning(f"报告检索失败: {e}")
        return "", []


async def _search_analysis(
    question: str,
    user_id: str,
    db: AsyncSession,
    top_k: int = 3,
) -> tuple[str, List[SourceItem]]:
    """从分析结果中检索"""
    try:
        stmt = (
            select(AnalysisTaskORM)
            .where(
                AnalysisTaskORM.user_id == user_id,
                AnalysisTaskORM.status == "completed",
            )
            .order_by(desc(AnalysisTaskORM.completed_at))
            .limit(top_k)
        )
        result = await db.execute(stmt)
        tasks = list(result.scalars())

        if not tasks:
            return "", []

        keywords = question.lower().split()
        context_parts = []
        sources: List[SourceItem] = []

        for task in tasks:
            task_result = task.result or {}
            competitors = task.competitors or []
            result_str = str(task_result)

            if not any(k in result_str.lower() for k in keywords):
                continue

            snippet = result_str[:500]
            comps = ", ".join(competitors[:3])

            context_parts.append(f"[分析任务: {comps}]\n{snippet}")
            sources.append(SourceItem(
                type="analysis",
                competitor=None,
                title=f"竞品分析 - {comps}",
                snippet=snippet[:200],
            ))

        return "\n\n".join(context_parts), sources
    except Exception as e:
        logger.warning(f"分析结果检索失败: {e}")
        return "", []


async def _ask_llm(
    question: str,
    kb_context: str,
    report_context: str,
    analysis_context: str,
    conversation_history: str,
) -> str:
    """调用 LLM 回答问题"""
    context_parts = []
    if kb_context:
        context_parts.append(f"## 知识库信息\n{kb_context}")
    if report_context:
        context_parts.append(f"## 相关报告\n{report_context}")
    if analysis_context:
        context_parts.append(f"## 分析结果\n{analysis_context}")

    all_context = "\n\n".join(context_parts) if context_parts else "暂无相关信息"

    system_prompt = """你是一个专业的竞品分析助手。基于提供的上下文信息回答用户问题。

回答要求：
1. 优先使用知识库和报告中的信息，不要编造数据
2. 如果信息不足，明确说明，不要编造
3. 引用具体的数据和事实，避免泛泛而谈
4. 用中文回答，结构清晰
5. 保持对话连贯性，结合对话历史理解上下文"""

    prompt = f"""{system_prompt}

对话历史：
{conversation_history if conversation_history else "暂无"}

参考信息：
{all_context}

用户问题：{question}

回答："""

    llm = create_llm(temperature=0.3, max_tokens=2048)
    response = await llm.ainvoke(prompt)
    return response.content


@router.post("/ask/{session_id}", response_model=ApiResponse)
async def ask_question_in_session(
    session_id: str,
    req: QARequest,
    user: UserORM = Depends(require_user),
    db: AsyncSession = Depends(get_session),
):
    """在指定会话中提问（支持对话记忆 + 多源检索）"""
    # 验证会话
    stmt = select(ChatSessionORM).where(
        ChatSessionORM.id == session_id,
        ChatSessionORM.user_id == user.id,
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    try:
        # 1. 收集对话历史
        conversation_history = await _build_conversation_context(session_id, db)

        # 2. 多源检索
        kb_context, kb_sources = await _search_knowledge(req.question, user.id, db)
        report_context, report_sources = await _search_reports(req.question, user.id, db)
        analysis_context, analysis_sources = await _search_analysis(req.question, user.id, db)

        # 3. 调用 LLM
        answer = await _ask_llm(
            req.question, kb_context, report_context,
            analysis_context, conversation_history,
        )

        # 4. 合并来源
        all_sources = kb_sources + report_sources + analysis_sources
        source_dicts = [s.model_dump() for s in all_sources]

        # 5. 保存消息
        user_msg = ChatMessageORM(
            session_id=session_id, role="user", content=req.question
        )
        assistant_msg = ChatMessageORM(
            session_id=session_id, role="assistant",
            content=answer, sources=source_dicts,
        )
        db.add(user_msg)
        db.add(assistant_msg)

        # 6. 更新会话标题（首轮对话自动生成标题）
        msg_count = await db.execute(
            select(func.count(ChatMessageORM.id))
            .where(ChatMessageORM.session_id == session_id)
        )
        if msg_count.scalar() <= 2:
            session.title = req.question[:50] + ("..." if len(req.question) > 50 else "")

        session.updated_at = func.now()
        await db.commit()

        return {
            "code": 200,
            "data": QAResponse(answer=answer, sources=all_sources).model_dump(),
            "message": "success",
        }
    except Exception as e:
        logger.error(f"问答失败: {e}")
        raise HTTPException(status_code=500, detail=f"问答处理失败: {str(e)}")


@router.post("", response_model=ApiResponse)
async def ask_question(
    req: QARequest,
    user: UserORM = Depends(require_user),
    db: AsyncSession = Depends(get_session),
):
    """提交智能问答（自动创建新会话）"""
    # 创建新会话
    title = req.question[:50] + ("..." if len(req.question) > 50 else "")
    session = ChatSessionORM(user_id=user.id, title=title)
    db.add(session)
    await db.commit()
    await db.refresh(session)

    # 转发到会话问答
    return await ask_question_in_session(session.id, req, user, db)
