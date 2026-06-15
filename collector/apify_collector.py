"""
Apify 应用商店评论采集器
======================

通过 Apify 平台采集 Google Play 和 App Store 的评论数据。
"""

from typing import List, Dict, Any, Optional
import asyncio
import logging

from .base import BaseCollector
from utils.cache import CacheManager, make_cache_key
from config.settings import settings

logger = logging.getLogger(__name__)

# Actor ID 配置
GOOGLE_PLAY_ACTOR = "neatrat/google-play-store-reviews-scraper"
APP_STORE_ACTOR = "thewolves/appstore-reviews-scraper"


class ApifyCollector(BaseCollector):
    """Apify 应用商店评论采集器"""

    def __init__(self, api_token: Optional[str] = None):
        super().__init__(name="apify")
        self.api_token = api_token or settings.apify_api_token
        self._cache = CacheManager(redis_url=settings.redis_url, prefix="apify")

    async def collect(self, target: str, **kwargs) -> Dict[str, Any]:
        """
        采集应用评论

        Args:
            target: 应用 ID（包名或 App Store ID）
            **kwargs:
                store: 商店类型 "google" 或 "apple"
                max_reviews: 最大评论数
                lang: 语言
                country: 国家/地区
                min_score: 最低评分筛选（仅 Google Play）
                sort: 排序方式
        """
        store = kwargs.get("store", "google")
        max_reviews = kwargs.get("max_reviews", 3)
        lang = kwargs.get("lang", "zh")
        country = kwargs.get("country", "cn")
        min_score = kwargs.get("min_score")
        sort = kwargs.get("sort")

        cache_key = make_cache_key("apify", store, target, str(max_reviews))
        cached = self._cache.get(cache_key)
        if cached is not None:
            self.logger.info(f"Apify 缓存命中: {target}")
            return cached

        try:
            from apify_client import ApifyClient as ApifySyncClient

            client = ApifySyncClient(self.api_token)

            if store == "google":
                actor_id = GOOGLE_PLAY_ACTOR
                run_input: Dict[str, Any] = {
                    "appIdOrUrl": target,
                    "maxReviews": max_reviews,
                    "lang": lang,
                    "country": country,
                }
                if min_score is not None:
                    run_input["minScore"] = min_score
                if sort:
                    run_input["sort"] = sort
            else:
                actor_id = APP_STORE_ACTOR
                run_input: Dict[str, Any] = {
                    "appId": target,
                    "maxReviews": max_reviews,
                    "lang": lang,
                    "country": country,
                }
                if sort:
                    run_input["sort"] = sort

            # 在 executor 中运行同步调用
            loop = asyncio.get_event_loop()
            run = await loop.run_in_executor(
                None,
                lambda: client.actor(actor_id).call(run_input=run_input)
            )

            # 兼容 dict 和 Run object 两种返回值
            dataset_id = run.get("defaultDatasetId") if isinstance(run, dict) else run.default_dataset_id
            if not dataset_id:
                raise ValueError(f"无法获取 dataset ID，返回: {run}")

            # 获取结果
            dataset_items = list(
                client.dataset(dataset_id).iterate_items()
            )

            raw_data = {
                "app_id": target,
                "store": store,
                "source": "apify",
                "reviews": dataset_items,
                "total_fetched": len(dataset_items),
            }

            self._cache.set(cache_key, raw_data, ttl=3600 * 12)
            return raw_data

        except ImportError:
            self.logger.error("缺少 apify-client 依赖: pip install apify-client")
            return {"app_id": target, "store": store, "error": "缺少 apify-client 依赖", "status": "error"}
        except Exception as e:
            self.logger.error(f"Apify 采集失败: {target}, 错误: {e}")
            return {"app_id": target, "store": store, "error": str(e), "status": "error"}

    def parse(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """解析 Apify 返回的数据"""
        if raw_data.get("status") == "error":
            return raw_data

        store = raw_data.get("store", "unknown")
        reviews = raw_data.get("reviews", [])

        if store == "google":
            return self._parse_google_play(raw_data, reviews)
        else:
            return self._parse_app_store(raw_data, reviews)

    def _parse_google_play(self, raw_data: Dict[str, Any], reviews: List[Dict]) -> Dict[str, Any]:
        """解析 Google Play 数据"""
        parsed_reviews = []
        for r in reviews:
            parsed_reviews.append({
                "user": r.get("userName", ""),
                "text": r.get("text", r.get("content", "")),
                "rating": r.get("score", r.get("rating", 0)),
                "date": r.get("at", r.get("date", "")),
                "version": r.get("version", ""),
            })

        ratings = [r["rating"] for r in parsed_reviews if r["rating"] > 0]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0

        return {
            "app_name": raw_data.get("app_name", raw_data.get("app_id", "")),
            "store": "google_play",
            "app_id": raw_data.get("app_id", ""),
            "rating": round(avg_rating, 1),
            "ratings_count": len(parsed_reviews),
            "reviews": parsed_reviews,
        }

    def _parse_app_store(self, raw_data: Dict[str, Any], reviews: List[Dict]) -> Dict[str, Any]:
        """解析 App Store 数据"""
        parsed_reviews = []
        for r in reviews:
            parsed_reviews.append({
                "user": r.get("userName", ""),
                "text": r.get("text", r.get("content", "")),
                "rating": r.get("score", r.get("rating", 0)),
                "date": r.get("date", ""),
                "version": r.get("version", ""),
            })

        ratings = [r["rating"] for r in parsed_reviews if r["rating"] > 0]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0

        return {
            "app_name": raw_data.get("app_name", raw_data.get("app_id", "")),
            "store": "app_store",
            "app_id": raw_data.get("app_id", ""),
            "rating": round(avg_rating, 1),
            "ratings_count": len(parsed_reviews),
            "reviews": parsed_reviews,
        }

    def clean(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """清洗数据，移除空值和无用评价"""
        cleaned = {k: v for k, v in data.items() if v is not None and v != ""}
        if "reviews" in cleaned:
            cleaned["reviews"] = [
                r for r in cleaned["reviews"]
                if r.get("text") or r.get("rating", 0) > 0
            ]
        return cleaned
