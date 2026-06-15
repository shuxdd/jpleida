"""
API 缓存层
==========

为 GET 端点提供 Redis/文件缓存支持，减少数据库查询。
本地无 Redis 时自动降级为文件缓存。
"""

import inspect
import logging
from typing import Any, Optional

from utils.cache import CacheManager
from config.settings import settings

logger = logging.getLogger(__name__)

_cache: Optional[CacheManager] = None


def _get_cache() -> CacheManager:
    global _cache
    if _cache is None:
        _cache = CacheManager(redis_url=settings.redis_url, prefix="api")
    return _cache


async def _cached(key: str, factory, ttl: int) -> Any:
    """带 async 支持的 get_or_set"""
    cache = _get_cache()
    cached = cache.get(key)
    if cached is not None:
        return cached
    value = await factory() if inspect.iscoroutinefunction(factory) else factory()
    cache.set(key, value, ttl)
    return value


async def cached_list(user_id: str, resource: str, factory, ttl: int = 120) -> Any:
    """缓存列表查询结果"""
    return await _cached(f"{user_id}:{resource}:list", factory, ttl)


async def cached_item(user_id: str, resource: str, item_id: str, factory, ttl: int = 300) -> Any:
    """缓存单个资源查询结果"""
    return await _cached(f"{user_id}:{resource}:{item_id}", factory, ttl)


def invalidate_list(user_id: str, resource: str) -> None:
    """使列表缓存失效"""
    _get_cache().delete(f"{user_id}:{resource}:list")


def invalidate_item(user_id: str, resource: str, item_id: str) -> None:
    """使单个资源缓存失效"""
    _get_cache().delete(f"{user_id}:{resource}:{item_id}")
