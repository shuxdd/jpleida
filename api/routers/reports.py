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

from api.database import AnalysisTaskORM, ReportORM, get_session

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
):
    """获取报告列表"""
    query = select(ReportORM)

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


@router.get("/{report_id}")
async def get_report(
    report_id: str,
    session: AsyncSession = Depends(get_session),
):
    """获取报告详情"""
    result = await session.execute(
        select(ReportORM).where(ReportORM.id == report_id)
    )
    orm = result.scalar_one_or_none()

    if not orm:
        raise HTTPException(status_code=404, detail="报告不存在")

    return {"code": 200, "data": _orm_to_response(orm), "message": "success"}


@router.get("/{report_id}/chart-data")
async def get_report_chart_data(
    report_id: str,
    session: AsyncSession = Depends(get_session),
):
    """获取报告对应的分析结果数据（用于图表渲染）"""
    result = await session.execute(
        select(ReportORM).where(ReportORM.id == report_id)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")

    # 获取关联的分析任务
    task_result = await session.execute(
        select(AnalysisTaskORM).where(AnalysisTaskORM.id == report.analysis_id)
    )
    task = task_result.scalar_one_or_none()

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
    format: str = Query("markdown", pattern="^(markdown|html|pdf)$"),
    session: AsyncSession = Depends(get_session),
):
    """导出报告文件"""
    result = await session.execute(
        select(ReportORM).where(ReportORM.id == report_id)
    )
    orm = result.scalar_one_or_none()

    if not orm:
        raise HTTPException(status_code=404, detail="报告不存在")

    content = orm.content
    filename = orm.title

    if format == "pdf":
        from report.generator import ReportGenerator
        generator = ReportGenerator()
        pdf_bytes = generator.export_pdf_bytes(content)
        buffer = BytesIO(pdf_bytes)
        media_type = "application/pdf"
        filename = f"{filename}.pdf"
    elif format == "html":
        from report.generator import ReportGenerator
        generator = ReportGenerator()
        html_content = generator._markdown_to_html(content)
        buffer = BytesIO(html_content.encode("utf-8"))
        media_type = "text/html"
        filename = f"{filename}.html"
    else:
        buffer = BytesIO(content.encode("utf-8"))
        media_type = "text/markdown"
        filename = f"{filename}.md"

    return StreamingResponse(
        buffer,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{report_id}")
async def delete_report(
    report_id: str,
    session: AsyncSession = Depends(get_session),
):
    """删除报告"""
    result = await session.execute(
        select(ReportORM).where(ReportORM.id == report_id)
    )
    orm = result.scalar_one_or_none()

    if not orm:
        raise HTTPException(status_code=404, detail="报告不存在")

    await session.delete(orm)
    await session.commit()

    logger.info(f"删除报告: {report_id}")
    return {"code": 200, "data": None, "message": "删除成功"}
