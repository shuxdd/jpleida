"""
缓存工具
========

统一缓存层，支持 Redis 和本地文件两种后端。
Redis 不可用时自动降级为本地文件缓存。
"""

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# 缓存目录
CACHE_DIR = Path("data/cache")

# 默认 TTL
DEFAULT_TTL = 3600 * 24  # 24 小时


class FileCache:
    """本地文件缓存"""

    def __init__(self, cache_dir: Path = CACHE_DIR):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, key: str) -> Path:
        safe_key = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{safe_key}.json"

    def get(self, key: str) -> Optional[Any]:
        path = self._get_path(key)
        if not path.exists():
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                entry = json.load(f)

            # 检查过期
            if entry.get("expires_at", 0) < time.time():
                path.unlink(missing_ok=True)
                return None

            return entry.get("value")

        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"文件缓存读取失败: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = DEFAULT_TTL) -> None:
        path = self._get_path(key)
        entry = {
            "value": value,
            "expires_at": time.time() + ttl,
            "created_at": time.time(),
        }

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(entry, f, ensure_ascii=False)
        except OSError as e:
            logger.warning(f"文件缓存写入失败: {e}")

    def delete(self, key: str) -> None:
        path = self._get_path(key)
        path.unlink(missing_ok=True)

    def clear(self) -> int:
        count = 0
        for f in self.cache_dir.glob("*.json"):
            f.unlink(missing_ok=True)
            count += 1
        return count


class RedisCache:
    """Redis 缓存"""

    def __init__(self, redis_url: str):
        import redis
        self.client = redis.from_url(redis_url, decode_responses=True)
        # 测试连接
        self.client.ping()

    def get(self, key: str) -> Optional[Any]:
        try:
            data = self.client.get(key)
            if data is None:
                return None
            return json.loads(data)
        except Exception as e:
            logger.warning(f"Redis 读取失败: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = DEFAULT_TTL) -> None:
        try:
            self.client.setex(key, ttl, json.dumps(value, ensure_ascii=False))
        except Exception as e:
            logger.warning(f"Redis 写入失败: {e}")

    def delete(self, key: str) -> None:
        try:
            self.client.delete(key)
        except Exception as e:
            logger.warning(f"Redis 删除失败: {e}")

    def clear(self) -> int:
        try:
            return self.client.flushdb()
        except Exception as e:
            logger.warning(f"Redis 清空失败: {e}")
            return 0


class CacheManager:
    """
    缓存管理器

    自动检测 Redis 可用性，不可用时降级为本地文件缓存。
    """

    def __init__(self, redis_url: Optional[str] = None, prefix: str = ""):
        self.prefix = prefix
        self._backend = None
        self._backend_type = None

        # 尝试 Redis
        if redis_url:
            try:
                self._backend = RedisCache(redis_url)
                self._backend_type = "redis"
                logger.info("缓存后端: Redis")
                return
            except Exception as e:
                logger.warning(f"Redis 连接失败，降级为文件缓存: {e}")

        # 降级为文件缓存
        self._backend = FileCache()
        self._backend_type = "file"
        logger.info("缓存后端: 本地文件")

    @property
    def backend_type(self) -> str:
        return self._backend_type

    def _make_key(self, key: str) -> str:
        return f"{self.prefix}:{key}" if self.prefix else key

    def get(self, key: str) -> Optional[Any]:
        return self._backend.get(self._make_key(key))

    def set(self, key: str, value: Any, ttl: int = DEFAULT_TTL) -> None:
        self._backend.set(self._make_key(key), value, ttl)

    def delete(self, key: str) -> None:
        self._backend.delete(self._make_key(key))

    def get_or_set(
        self, key: str, factory: Any, ttl: int = DEFAULT_TTL
    ) -> Any:
        """获取缓存，不存在时通过 factory 生成并缓存"""
        value = self.get(key)
        if value is not None:
            return value

        value = factory()
        self.set(key, value, ttl)
        return value


def make_cache_key(*parts: str) -> str:
    """生成缓存键，对过长的部分取 hash"""
    key_parts = []
    for part in parts:
        if len(part) > 64:
            key_parts.append(hashlib.md5(part.encode()).hexdigest())
        else:
            key_parts.append(part)
    return ":".join(key_parts)
