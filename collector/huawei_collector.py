"""
华为应用市场数据采集器
======================

通过 AppGallery Connect API 采集华为应用市场的评分和评论数据。
认证方式：JWT 签名换取 access_token。
"""

from typing import List, Dict, Any, Optional
import asyncio
import json
import time
import logging
import os

import httpx

from .base import BaseCollector
from utils.cache import CacheManager, make_cache_key
from config.settings import settings

logger = logging.getLogger(__name__)

TOKEN_URL = "https://oauth-login.cloud.huawei.com/oauth2/v3/token"
REVIEWS_URL = "https://connect-api.cloud.huawei.com/api/reviews/v1/manage/reviews"


class HuaweiCollector(BaseCollector):
    """华为应用市场数据采集器"""

    def __init__(self, key_file_path: Optional[str] = None):
        super().__init__(name="huawei")
        self.key_file_path = key_file_path or settings.huawei_key_file
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0
        self._cache = CacheManager(redis_url=settings.redis_url, prefix="huawei")

    def _load_key_file(self) -> dict:
        """加载密钥文件"""
        if not self.key_file_path or not os.path.exists(self.key_file_path):
            raise FileNotFoundError(f"华为密钥文件不存在: {self.key_file_path}")

        with open(self.key_file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _create_jwt(self) -> str:
        """创建签名 JWT"""
        import jwt

        key_data = self._load_key_file()
        now = int(time.time())

        payload = {
            "iss": key_data["sub_account"],
            "sub": key_data["sub_account"],
            "aud": "https://oauth-login.cloud.huawei.com",
            "iat": now,
            "exp": now + 3600,
            "jti": f"{now}",
        }

        headers = {
            "kid": key_data["key_id"],
            "alg": "RS256",
        }

        token = jwt.encode(
            payload,
            key_data["private_key"],
            algorithm="RS256",
            headers=headers,
        )
        return token

    async def _get_access_token(self) -> str:
        """获取 access_token（JWT 换取）"""
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token

        jwt_token = self._create_jwt()

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
                    "client_assertion": jwt_token,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        self._access_token = data["access_token"]
        self._token_expires_at = time.time() + data.get("expires_in", 3600) - 60
        self.logger.info("华为 access_token 获取成功")
        return self._access_token

    async def collect(self, target: str, max_size: int = 100, **kwargs) -> Dict[str, Any]:
        """
        采集华为应用市场评论

        Args:
            target: 应用包名，如 com.alibaba.android.rimet
            max_size: 获取评论数量
        """
        cache_key = make_cache_key("huawei", target, str(max_size))
        cached = self._cache.get(cache_key)
        if cached is not None:
            self.logger.info(f"华为缓存命中: {target}")
            return cached

        try:
            token = await self._get_access_token()
        except Exception as e:
            self.logger.error(f"华为认证失败: {e}")
            return {"package_name": target, "error": str(e), "status": "error"}

        all_reviews = []
        start = 0
        page_size = min(max_size, 100)

        async with httpx.AsyncClient(timeout=15) as client:
            while len(all_reviews) < max_size:
                try:
                    resp = await client.get(
                        REVIEWS_URL,
                        params={
                            "package_name": target,
                            "start": start,
                            "maxSize": page_size,
                        },
                        headers={
                            "Authorization": f"Bearer {token}",
                            "client_id": self._load_key_file()["sub_account"],
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()

                    reviews = data.get("list", [])
                    if not reviews:
                        break

                    all_reviews.extend(reviews)
                    start += len(reviews)

                    if len(reviews) < page_size:
                        break

                except Exception as e:
                    self.logger.warning(f"华为评论获取失败: {e}")
                    break

        raw_data = {
            "package_name": target,
            "source": "huawei",
            "reviews": all_reviews[:max_size],
            "total_fetched": len(all_reviews[:max_size]),
        }

        self._cache.set(cache_key, raw_data, ttl=3600 * 6)
        return raw_data

    def parse(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """解析华为评论数据"""
        if raw_data.get("status") == "error":
            return raw_data

        reviews = raw_data.get("reviews", [])
        parsed_reviews = [self._parse_review(r) for r in reviews]

        ratings = [r["rating"] for r in parsed_reviews if r["rating"] > 0]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0

        return {
            "app_name": raw_data.get("package_name", ""),
            "store": "huawei",
            "package_name": raw_data.get("package_name", ""),
            "rating": round(avg_rating, 1),
            "ratings_count": len(parsed_reviews),
            "reviews": parsed_reviews,
        }

    def _parse_review(self, raw_review: Dict[str, Any]) -> Dict[str, Any]:
        """解析单条评论"""
        return {
            "review_id": raw_review.get("reviewId", ""),
            "user": raw_review.get("userName", ""),
            "text": raw_review.get("reviewContent", ""),
            "rating": raw_review.get("rating", 0),
            "date": raw_review.get("lastUpdated", ""),
            "device": raw_review.get("device", ""),
            "reply": raw_review.get("reply", ""),
        }

    def clean(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """清洗数据"""
        cleaned = {k: v for k, v in data.items() if v is not None and v != ""}
        # 清洗评论列表中的空评论
        if "reviews" in cleaned:
            cleaned["reviews"] = [
                r for r in cleaned["reviews"]
                if r.get("text") or r.get("rating", 0) > 0
            ]
        return cleaned

    async def get_app_reviews(self, package_name: str, max_size: int = 50) -> Dict[str, Any]:
        """获取应用评论的便捷方法"""
        return await self.run(package_name, max_size=max_size)
