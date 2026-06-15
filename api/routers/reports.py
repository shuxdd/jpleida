"""
报告管理路由
============

提供报告的查询、导出、删除接口。
"""

import logging
from typing import Optional
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import AnalysisTaskORM, ReportORM, EvaluationORM, get_session
from api.auth import require_user
from api.cache import cached_list, cached_item, invalidate_list

logger = logging.getLogger(__name__)
router = APIRouter()


def _orm_to_response(orm: ReportORM) -> dict:
    """ORM 对象转响应字典"""
    return {
        "id": orm.id,
        "analysis_id": orm.analysis_id,
        "title": orm.title,
        "report_type": orm.report_type,
        "format": orm.format,
        "content": orm.content,
        "file_path": orm.file_path,
        "created_at": orm.created_at.isoformat() if orm.created_at else None,
    }


@router.get("")
async def list_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    analysis_id: Optional[str] = None,
    report_type: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_user),
):
    """获取报告列表"""
    async def _query():
        query = select(ReportORM).where(ReportORM.user_id == user.id)

        if analysis_id:
            query = query.where(ReportORM.analysis_id == analysis_id)
        if report_type:
            query = query.where(ReportORM.report_type == report_type)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await session.execute(count_query)).scalar() or 0

        query = query.order_by(ReportORM.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await session.execute(query)
        reports = result.scalars().all()

        return {
            "code": 200,
            "data": [_orm_to_response(r) for r in reports],
            "total": total,
            "page": page,
            "page_size": page_size,
            "message": "success",
        }

    if analysis_id or report_type:
        return await _query()
    return await cached_list(user.id, "reports", _query)


async def _get_user_report(
    report_id: str, user_id: str, session: AsyncSession
) -> ReportORM:
    """获取用户自己的报告"""
    result = await session.execute(
        select(ReportORM).where(
            ReportORM.id == report_id,
            ReportORM.user_id == user_id,
        )
    )
    orm = result.scalar_one_or_none()
    if not orm:
        raise HTTPException(status_code=404, detail="报告不存在")
    return orm


@router.get("/{report_id}")
async def get_report(
    report_id: str,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_user),
):
    """获取报告详情"""
    orm = await _get_user_report(report_id, user.id, session)
    return {"code": 200, "data": _orm_to_response(orm), "message": "success"}


@router.get("/{report_id}/chart-data")
async def get_report_chart_data(
    report_id: str,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_user),
):
    """获取报告对应的分析结果数据（用于图表渲染）"""
    await _get_user_report(report_id, user.id, session)

    # 获取关联的分析任务（也在用户的范围内）
    result = await session.execute(
        select(AnalysisTaskORM).where(
            AnalysisTaskORM.id == select(ReportORM.analysis_id).where(
                ReportORM.id == report_id, ReportORM.user_id == user.id
            ).scalar_subquery(),
            AnalysisTaskORM.user_id == user.id,
        )
    )
    task = result.scalar_one_or_none()

    if not task or not task.result:
        return {"code": 200, "data": None, "message": "无分析数据"}

    analysis = task.result.get("analysis_results", {})

    return {
        "code": 200,
        "data": {
            "competitors": task.competitors,
            "analysis_type": task.analysis_type,
            "dimensions": task.dimensions,
            "feature_matrix": analysis.get("feature_matrix", {}),
            "pricing_comparison": analysis.get("pricing_comparison", {}),
            "swot_analysis": analysis.get("swot_analysis", {}),
            "competitors_data": analysis.get("competitors_data", {}),
        },
        "message": "success",
    }


@router.get("/{report_id}/export")
async def export_report(
    report_id: str,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_user),
):
    """导出报告文件（Markdown）"""
    orm = await _get_user_report(report_id, user.id, session)

    content = orm.content
    filename = f"{orm.title}.md"
    buffer = BytesIO(content.encode("utf-8"))

    # RFC 5987: 文件名含非 ASCII 字符时使用 filename* 编码
    from urllib.parse import quote
    ascii_filename = filename.encode('ascii', errors='ignore').decode('ascii')
    encoded_filename = quote(filename, safe='')
    disposition = f"attachment; filename=\"{ascii_filename}\"; filename*=UTF-8''{encoded_filename}"

    return StreamingResponse(
        buffer,
        media_type="text/markdown",
        headers={"Content-Disposition": disposition},
    )


@router.get("/{report_id}/evaluation")
async def get_evaluation(
    report_id: str,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_user),
):
    """获取报告质量评估结果"""
    result = await session.execute(
        select(EvaluationORM).where(
            EvaluationORM.report_id == report_id,
            EvaluationORM.user_id == user.id,
        )
    )
    orm = result.scalar_one_or_none()

    if not orm:
        return {
            "code": 200,
            "data": None,
            "message": "暂无评估数据（评估可能还在进行中）",
        }

    return {
        "code": 200,
        "data": {
            "id": orm.id,
            "analysis_id": orm.analysis_id,
            "report_id": orm.report_id,
            "coverage": {"score": orm.coverage_score, "reasoning": orm.coverage_reasoning},
            "depth": {"score": orm.depth_score, "reasoning": orm.depth_reasoning},
            "structure": {"score": orm.structure_score, "reasoning": orm.structure_reasoning},
            "actionability": {"score": orm.actionability_score, "reasoning": orm.actionability_reasoning},
            "overall_score": orm.overall_score,
            "overall_summary": orm.overall_summary,
            "key_improvements": orm.key_improvements or [],
            "diagnosis": orm.diagnosis or [],
            "created_at": orm.created_at.isoformat() if orm.created_at else None,
        },
        "message": "success",
    }


@router.delete("/{report_id}")
async def delete_report(
    report_id: str,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_user),
):
    """删除报告"""
    orm = await _get_user_report(report_id, user.id, session)
    await session.delete(orm)
    await session.commit()

    invalidate_list(user.id, "reports")
    logger.info(f"删除报告: {report_id}")
    return {"code": 200, "data": None, "message": "删除成功"}
