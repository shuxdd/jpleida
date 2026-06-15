"""
分析任务路由
============

提供分析任务的提交、查询、取消接口。
"""

import asyncio
import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import AnalysisTaskORM, ReportORM, UserORM, get_session
from api.schemas import AnalysisSubmitRequest
from api.auth import require_user
from api.cache import cached_list, cached_item, invalidate_list, invalidate_item

logger = logging.getLogger(__name__)
router = APIRouter()

# 运行中的任务追踪
_running_tasks: dict[str, asyncio.Task] = {}


def _orm_to_response(orm: AnalysisTaskORM) -> dict:
    """ORM 对象转响应字典"""
    return {
        "id": orm.id,
        "competitors": orm.competitors or [],
        "analysis_type": orm.analysis_type,
        "dimensions": orm.dimensions or [],
        "my_product": orm.my_product,
        "status": orm.status,
        "result": orm.result,
        "error_message": orm.error_message,
        "created_at": orm.created_at.isoformat() if orm.created_at else None,
        "completed_at": orm.completed_at.isoformat() if orm.completed_at else None,
    }


async def _run_analysis(task_id: str, user_id: str):
    """后台执行分析任务"""
    from api.database import async_session, CompetitorORM
    from agent.graph import create_analysis_graph
    from api.app import progress_manager

    def on_progress(node: str, progress: int, message: str):
        """同步回调 -> 异步推送"""
        loop = asyncio.get_event_loop()
        loop.create_task(progress_manager.send_progress(task_id, node, progress, message))

    async with async_session() as session:
        try:
            result = await session.execute(
                select(AnalysisTaskORM).where(AnalysisTaskORM.id == task_id)
            )
            task = result.scalar_one_or_none()
            if not task:
                return

            task.status = "planning"
            await session.commit()

            # 查询竞品详情，构建 competitors_meta
            competitors_meta = {}
            if task.competitors:
                comp_result = await session.execute(
                    select(CompetitorORM).where(
                        CompetitorORM.name.in_(task.competitors),
                        CompetitorORM.user_id == user_id,
                    )
                )
                for comp in comp_result.scalars().all():
                    competitors_meta[comp.name] = {
                        "tags": comp.tags or [],
                        "google_play_id": comp.google_play_id,
                        "app_store_id": comp.app_store_id,
                        "notes": comp.notes,
                    }

            # 如果填写了我的产品，加入竞品队列走完整采集流程
            all_competitors = list(task.competitors)
            if task.my_product and task.my_product not in all_competitors:
                all_competitors.append(task.my_product)

            graph = create_analysis_graph()
            task.status = "collecting"
            await session.commit()

            graph_result = await graph.ainvoke({
                "competitors": all_competitors,
                "analysis_type": task.analysis_type,
                "dimensions": task.dimensions or ["features", "pricing", "swot"],
                "my_product": task.my_product,
                "user_id": user_id,
                "collection_plan": {"competitors_meta": competitors_meta},
                "raw_data": [],
                "extracted_info": [],
                "analysis_results": {},
                "report": "",
                "status": "collecting",
                "errors": [],
                "progress_callback": on_progress,
            })

            errors = graph_result.get("errors", [])
            task.status = "completed"
            task.result = {
                "report": graph_result.get("report", ""),
                "analysis_results": graph_result.get("analysis_results", {}),
                "errors": errors,
            }
            if errors:
                task.error_message = "分析完成，但存在警告：\n" + "\n".join(errors[:5])
            task.completed_at = datetime.now()
            await session.commit()

            # 先保存报告，前端立即可见
            if graph_result.get("report"):
                report_orm = ReportORM(
                    user_id=user_id,
                    analysis_id=task_id,
                    title=f"竞品分析报告 - {', '.join(task.competitors)}",
                    report_type=task.analysis_type,
                    format="markdown",
                    content=graph_result["report"],
                )
                session.add(report_orm)
                await session.commit()

            logger.info(f"分析任务完成: {task_id}")

            # 知识库异步入库，不阻塞响应
            asyncio.create_task(_store_knowledge_async(graph_result, user_id))

        except Exception as e:
            logger.error(f"分析任务失败: {task_id}, 错误: {e}")
            task.status = "failed"
            task.error_message = str(e)
            task.completed_at = datetime.now()
            await session.commit()

        finally:
            _running_tasks.pop(task_id, None)


async def _store_knowledge_async(graph_result: dict, user_id: str):
    """后台执行知识库入库"""
    try:
        extracted_info = graph_result.get("extracted_info", [])
        analysis_results = graph_result.get("analysis_results", {})
        if not extracted_info:
            logger.info("无提取数据，跳过知识库入库")
            return

        from agent.nodes.knowledge_store import store_knowledge
        from agent.graph_state import AgentState

        state: AgentState = {
            "competitors": graph_result.get("competitors", []),
            "analysis_type": "standard",
            "dimensions": [],
            "my_product": None,
            "user_id": user_id,
            "collection_plan": {},
            "raw_data": [],
            "extracted_info": extracted_info,
            "analysis_results": analysis_results,
            "report": "",
            "status": "completed",
            "errors": [],
            "progress_callback": None,
        }
        await store_knowledge(state)
        logger.info("后台知识库入库完成")
    except Exception as e:
        logger.error(f"后台知识库入库失败: {e}")


@router.post("")
async def submit_analysis(
    req: AnalysisSubmitRequest,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_user),
):
    """提交分析任务"""
    orm = AnalysisTaskORM(
        user_id=user.id,
        competitors=req.competitors,
        analysis_type=req.analysis_type,
        dimensions=req.dimensions,
        my_product=req.my_product,
        status="pending",
    )
    session.add(orm)
    await session.commit()
    await session.refresh(orm)

    # 启动后台任务（带 user_id）
    task = asyncio.create_task(_run_analysis(orm.id, user.id))
    _running_tasks[orm.id] = task

    invalidate_list(user.id, "tasks")

    logger.info(f"提交分析任务: {orm.id}, 竞品: {req.competitors}")
    return {
        "code": 200,
        "data": {"task_id": orm.id, "status": "pending", "message": "分析任务已提交"},
        "message": "success",
    }


@router.get("")
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_user),
):
    """获取任务列表"""
    async def _query():
        query = select(AnalysisTaskORM).where(AnalysisTaskORM.user_id == user.id)

        if status:
            query = query.where(AnalysisTaskORM.status == status)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await session.execute(count_query)).scalar() or 0

        query = query.order_by(AnalysisTaskORM.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await session.execute(query)
        tasks = result.scalars().all()

        return {
            "code": 200,
            "data": [_orm_to_response(t) for t in tasks],
            "total": total,
            "page": page,
            "page_size": page_size,
            "message": "success",
        }

    if status:
        return await _query()
    return await cached_list(user.id, "tasks", _query)


@router.get("/{task_id}")
async def get_task(
    task_id: str,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_user),
):
    """获取任务详情"""

    # 运行中的任务不缓存（状态在变化）
    if task_id in _running_tasks:
        result = await session.execute(
            select(AnalysisTaskORM).where(
                AnalysisTaskORM.id == task_id,
                AnalysisTaskORM.user_id == user.id,
            )
        )
        orm = result.scalar_one_or_none()
        if not orm:
            raise HTTPException(status_code=404, detail="任务不存在")
        return {"code": 200, "data": _orm_to_response(orm), "message": "success"}

    async def _query():
        result = await session.execute(
            select(AnalysisTaskORM).where(
                AnalysisTaskORM.id == task_id,
                AnalysisTaskORM.user_id == user.id,
            )
        )
        orm = result.scalar_one_or_none()
        if not orm:
            raise HTTPException(status_code=404, detail="任务不存在")
        return {"code": 200, "data": _orm_to_response(orm), "message": "success"}

    return await cached_item(user.id, "tasks", task_id, _query)


@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_user),
):
    """取消/删除任务"""
    result = await session.execute(
        select(AnalysisTaskORM).where(
            AnalysisTaskORM.id == task_id,
            AnalysisTaskORM.user_id == user.id,
        )
    )
    orm = result.scalar_one_or_none()

    if not orm:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task_id in _running_tasks:
        _running_tasks[task_id].cancel()
        _running_tasks.pop(task_id, None)

    await session.delete(orm)
    await session.commit()

    invalidate_item(user.id, "tasks", task_id)
    invalidate_list(user.id, "tasks")
    logger.info(f"删除任务: {task_id}")
    return {"code": 200, "data": None, "message": "删除成功"}
