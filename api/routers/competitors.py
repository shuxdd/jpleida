"""
竞品管理路由
============

提供竞品的 CRUD 接口。
"""

import re
import asyncio
import logging
from typing import Optional
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import CompetitorORM, get_session
from api.schemas import CompetitorCreateRequest, CompetitorUpdateRequest
from api.auth import require_user
from api.cache import cached_list, cached_item, invalidate_list, invalidate_item
from config.settings import settings
from collector.web_search import WebSearchCollector

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
        "google_play_id": orm.google_play_id,
        "app_store_id": orm.app_store_id,
        "created_at": orm.created_at.isoformat() if orm.created_at else None,
        "updated_at": orm.updated_at.isoformat() if orm.updated_at else None,
    }


async def _auto_detect_store_ids(name: str) -> dict:
    """根据竞品名称自动查找应用商店 ID"""
    result = {"google_play_id": None, "app_store_id": None}

    # 1. App Store - iTunes Search API（公开，无需密钥）
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://itunes.apple.com/search",
                params={"term": name, "entity": "software", "limit": 5, "country": "cn"},
            )
            if resp.status_code == 200:
                apps = resp.json().get("results", [])
                for app in apps:
                    track_name = app.get("trackName", "")
                    if name.lower() in track_name.lower():
                        result["app_store_id"] = str(app["trackId"])
                        logger.info(f"  [自动] App Store 匹配: {track_name} (id={app['trackId']})")
                        break
    except Exception as e:
        logger.warning(f"  [自动] App Store 搜索失败: {e}")

    # 2. Google Play - SerpAPI 搜索
    if settings.serpapi_key:
        try:
            search = WebSearchCollector(api_key=settings.serpapi_key)
            raw = await search.collect(f"{name} Android", num_results=5)
            parsed = search.parse(raw)
            for r in parsed.get("results", []):
                url = r.get("url", "")
                match = re.search(r"play\.google\.com/store/apps/details\?id=([\w.]+)", url)
                if match:
                    pkg = match.group(1)
                    result["google_play_id"] = pkg
                    logger.info(f"  [自动] Google Play 匹配: {pkg}")
                    break
        except Exception as e:
            logger.warning(f"  [自动] Google Play 搜索失败: {e}")

    return result


@router.get("")
async def list_competitors(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    industry: Optional[str] = None,
    keyword: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_user),
):
    """获取竞品列表"""
    async def _query():
        query = select(CompetitorORM).where(CompetitorORM.user_id == user.id)

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

    # 有筛选条件时不缓存
    if industry or keyword:
        return await _query()
    return await cached_list(user.id, "competitors", _query)


@router.post("")
async def create_competitor(
    req: CompetitorCreateRequest,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_user),
):
    """创建竞品（自动检测应用商店 ID）"""
    orm = CompetitorORM(
        user_id=user.id,
        name=req.name,
        website=req.website,
        industry=req.industry,
        tags=req.tags,
        notes=req.notes,
        google_play_id=req.google_play_id,
        app_store_id=req.app_store_id,
    )
    session.add(orm)
    await session.commit()

    # 自动查找缺失的应用商店 ID
    store_ids = {}
    if not req.google_play_id or not req.app_store_id:
        store_ids = await _auto_detect_store_ids(req.name)
    if store_ids.get("google_play_id") and not orm.google_play_id:
        orm.google_play_id = store_ids["google_play_id"]
    if store_ids.get("app_store_id") and not orm.app_store_id:
        orm.app_store_id = store_ids["app_store_id"]
    if store_ids.get("google_play_id") or store_ids.get("app_store_id"):
        orm.updated_at = datetime.now()
        await session.commit()

    await session.refresh(orm)
    invalidate_list(user.id, "competitors")
    logger.info(f"创建竞品: {orm.name} (id={orm.id})")
    return {"code": 200, "data": _orm_to_response(orm), "message": "创建成功"}


@router.get("/{competitor_id}")
async def get_competitor(
    competitor_id: str,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_user),
):
    """获取竞品详情"""
    async def _query():
        result = await session.execute(
            select(CompetitorORM).where(
                CompetitorORM.id == competitor_id,
                CompetitorORM.user_id == user.id,
            )
        )
        orm = result.scalar_one_or_none()
        if not orm:
            raise HTTPException(status_code=404, detail="竞品不存在")
        return {"code": 200, "data": _orm_to_response(orm), "message": "success"}

    return await cached_item(user.id, "competitors", competitor_id, _query)


@router.put("/{competitor_id}")
async def update_competitor(
    competitor_id: str,
    req: CompetitorUpdateRequest,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_user),
):
    """更新竞品"""
    result = await session.execute(
        select(CompetitorORM).where(
            CompetitorORM.id == competitor_id,
            CompetitorORM.user_id == user.id,
        )
    )
    orm = result.scalar_one_or_none()

    if not orm:
        raise HTTPException(status_code=404, detail="竞品不存在")

    update_data = req.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(orm, key, value)
    orm.updated_at = datetime.now()

    # 名称变更时重新检测应用商店 ID
    if "name" in update_data and not req.google_play_id and not req.app_store_id:
        store_ids = await _auto_detect_store_ids(req.name)
        if store_ids.get("google_play_id") and not orm.google_play_id:
            orm.google_play_id = store_ids["google_play_id"]
        if store_ids.get("app_store_id") and not orm.app_store_id:
            orm.app_store_id = store_ids["app_store_id"]

    await session.commit()
    await session.refresh(orm)

    invalidate_item(user.id, "competitors", competitor_id)
    invalidate_list(user.id, "competitors")
    logger.info(f"更新竞品: {orm.id}")
    return {"code": 200, "data": _orm_to_response(orm), "message": "更新成功"}


@router.delete("/{competitor_id}")
async def delete_competitor(
    competitor_id: str,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_user),
):
    """删除竞品"""
    result = await session.execute(
        select(CompetitorORM).where(
            CompetitorORM.id == competitor_id,
            CompetitorORM.user_id == user.id,
        )
    )
    orm = result.scalar_one_or_none()

    if not orm:
        raise HTTPException(status_code=404, detail="竞品不存在")

    # 记录名称用于清理知识库（orm.name 在删除后仍可访问）
    comp_name = orm.name
    await session.delete(orm)
    await session.commit()

    # 清理 Chroma 知识库中的对应向量
    try:
        from knowledge.knowledge_base import KnowledgeBase
        kb = KnowledgeBase()
        kb.delete_competitor(comp_name)
        logger.info(f"知识库已清理: {comp_name}")
    except Exception as e:
        logger.warning(f"知识库清理失败: {e}")

    invalidate_item(user.id, "competitors", competitor_id)
    invalidate_list(user.id, "competitors")
    logger.info(f"删除竞品: {competitor_id}")
    return {"code": 200, "data": None, "message": "删除成功"}
