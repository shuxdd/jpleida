"""
竞品管理路由
============

提供竞品的 CRUD 接口。
"""

import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import CompetitorORM, get_session
from api.schemas import (
    ApiResponse,
    CompetitorCreateRequest,
    CompetitorUpdateRequest,
    CompetitorResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _orm_to_response(orm: CompetitorORM) -> dict:
    """ORM 对象转响应字典"""
    return {
        "id": orm.id,
        "name": orm.name,
        "website": orm.website,
        "industry": orm.industry,
        "tags": orm.tags or [],
        "notes": orm.notes,
        "created_at": orm.created_at.isoformat() if orm.created_at else None,
        "updated_at": orm.updated_at.isoformat() if orm.updated_at else None,
    }


@router.get("")
async def list_competitors(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    industry: Optional[str] = None,
    keyword: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    """获取竞品列表"""
    query = select(CompetitorORM)

    if industry:
        query = query.where(CompetitorORM.industry == industry)
    if keyword:
        query = query.where(CompetitorORM.name.contains(keyword))

    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    competitors = result.scalars().all()

    return {
        "code": 200,
        "data": [_orm_to_response(c) for c in competitors],
        "total": total,
        "page": page,
        "page_size": page_size,
        "message": "success",
    }


@router.post("")
async def create_competitor(
    req: CompetitorCreateRequest,
    session: AsyncSession = Depends(get_session),
):
    """创建竞品"""
    orm = CompetitorORM(
        name=req.name,
        website=req.website,
        industry=req.industry,
        tags=req.tags,
        notes=req.notes,
    )
    session.add(orm)
    await session.commit()
    await session.refresh(orm)

    logger.info(f"创建竞品: {orm.name} (id={orm.id})")
    return {"code": 200, "data": _orm_to_response(orm), "message": "创建成功"}


@router.get("/{competitor_id}")
async def get_competitor(
    competitor_id: str,
    session: AsyncSession = Depends(get_session),
):
    """获取竞品详情"""
    result = await session.execute(
        select(CompetitorORM).where(CompetitorORM.id == competitor_id)
    )
    orm = result.scalar_one_or_none()

    if not orm:
        raise HTTPException(status_code=404, detail="竞品不存在")

    return {"code": 200, "data": _orm_to_response(orm), "message": "success"}


@router.put("/{competitor_id}")
async def update_competitor(
    competitor_id: str,
    req: CompetitorUpdateRequest,
    session: AsyncSession = Depends(get_session),
):
    """更新竞品"""
    result = await session.execute(
        select(CompetitorORM).where(CompetitorORM.id == competitor_id)
    )
    orm = result.scalar_one_or_none()

    if not orm:
        raise HTTPException(status_code=404, detail="竞品不存在")

    update_data = req.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(orm, key, value)
    orm.updated_at = datetime.now()

    await session.commit()
    await session.refresh(orm)

    logger.info(f"更新竞品: {orm.id}")
    return {"code": 200, "data": _orm_to_response(orm), "message": "更新成功"}


@router.delete("/{competitor_id}")
async def delete_competitor(
    competitor_id: str,
    session: AsyncSession = Depends(get_session),
):
    """删除竞品"""
    result = await session.execute(
        select(CompetitorORM).where(CompetitorORM.id == competitor_id)
    )
    orm = result.scalar_one_or_none()

    if not orm:
        raise HTTPException(status_code=404, detail="竞品不存在")

    await session.delete(orm)
    await session.commit()

    logger.info(f"删除竞品: {competitor_id}")
    return {"code": 200, "data": None, "message": "删除成功"}
