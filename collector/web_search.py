"""
网页搜索采集器
==============

通过搜索引擎采集竞品信息。
"""

from typing import List, Dict, Any, Optional
import asyncio
import logging

from .base import BaseCollector
from utils.cache import CacheManager, make_cache_key
from config.settings import settings

logger = logging.getLogger(__name__)


class WebSearchCollector(BaseCollector):
    """网页搜索采集器"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        engine: str = "google",
        language: str = "zh-cn",
        country: str = "cn"
    ):
        """
        初始化搜索采集器

        Args:
            api_key: SerpAPI密钥
            engine: 搜索引擎 (google/bing/baidu)
            language: 语言
            country: 国家
        """
        super().__init__(name="web_search")
        self.api_key = api_key
        self.engine = engine
        self.language = language
        self.country = country
        self._client = None
        self._cache = CacheManager(redis_url=settings.redis_url, prefix="search")

    def _get_client(self):
        """获取SerpAPI客户端"""
        if self._client is None:
            try:
                from serpapi import GoogleSearch
                self._client = GoogleSearch
            except ImportError:
                raise ImportError("请安装serpapi: pip install serpapi")
        return self._client

    async def collect(
        self,
        target: str,
        num_results: int = 10,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行搜索

        Args:
            target: 搜索关键词
            num_results: 结果数量
            **kwargs: 其他参数

        Returns:
            搜索结果
        """
        if not self.api_key:
            raise ValueError("未配置SerpAPI密钥")

        # 检查缓存
        cache_key = make_cache_key("collect", target, str(num_results))
        cached = self._cache.get(cache_key)
        if cached is not None:
            self.logger.info(f"搜索缓存命中: {target}")
            return cached

        client = self._get_client()

        params = {
            "q": target,
            "api_key": self.api_key,
            "num": num_results,
            "hl": self.language,
            "gl": self.country
        }

        # 添加额外参数
        params.update(kwargs)

        # 在线程池中执行同步调用
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, lambda: client(params).get_dict())

        # 写入缓存（24小时）
        self._cache.set(cache_key, result, ttl=3600 * 24)

        return result

    def parse(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析搜索结果

        Args:
            raw_data: SerpAPI返回的原始数据

        Returns:
            解析后的数据
        """
        results = []

        # 解析有机搜索结果
        for item in raw_data.get("organic_results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "position": item.get("position", 0)
            })

        # 解析知识图谱（如果有）
        knowledge_graph = raw_data.get("knowledge_graph", {})

        return {
            "query": raw_data.get("search_parameters", {}).get("q", ""),
            "results": results,
            "knowledge_graph": {
                "title": knowledge_graph.get("title", ""),
                "type": knowledge_graph.get("type", ""),
                "description": knowledge_graph.get("description", ""),
                "website": knowledge_graph.get("website", ""),
                "attributes": knowledge_graph.get("attributes", {})
            } if knowledge_graph else None,
            "total_results": len(results)
        }

    def clean(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """清洗搜索结果"""
        cleaned_results = []

        for result in data.get("results", []):
            # 过滤空结果
            if not result.get("url"):
                continue

            # 清理标题和摘要
            title = result.get("title", "").strip()
            snippet = result.get("snippet", "").strip()
            url = result.get("url", "").strip()

            if title and url:
                cleaned_results.append({
                    "title": title,
                    "url": url,
                    "snippet": snippet,
                    "position": result.get("position", 0)
                })

        data["results"] = cleaned_results
        data["total_results"] = len(cleaned_results)
        return data

    async def search_competitor(
        self,
        competitor_name: str,
        keywords: Optional[List[str]] = None,
        num_results: int = 10
    ) -> Dict[str, Any]:
        """
        搜索竞品信息

        Args:
            competitor_name: 竞品名称
            keywords: 额外关键词
            num_results: 每个关键词的结果数量

        Returns:
            搜索结果
        """
        all_results = []

        # 基础搜索
        base_queries = [
            f"{competitor_name} 官网",
            f"{competitor_name} 产品",
            f"{competitor_name} 定价",
        ]

        # 添加自定义关键词
        if keywords:
            for keyword in keywords:
                base_queries.append(f"{competitor_name} {keyword}")

        # 执行搜索
        for query in base_queries:
            try:
                result = await self.run(query, num_results=num_results)
                if result["status"] == "success":
                    all_results.extend(result["data"].get("results", []))

                # 避免请求过快
                await asyncio.sleep(1)

            except Exception as e:
                logger.warning(f"搜索失败: {query}, 错误: {e}")
                continue

        # 去重
        seen_urls = set()
        unique_results = []
        for result in all_results:
            url = result.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)

        return {
            "competitor": competitor_name,
            "results": unique_results,
            "total": len(unique_results)
        }

    async def search_multiple(
        self,
        queries: List[str],
        num_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        批量搜索

        Args:
            queries: 查询列表
            num_results: 每个查询的结果数量

        Returns:
            搜索结果列表
        """
        results = []

        for query in queries:
            result = await self.run(query, num_results=num_results)
            results.append(result)
            await asyncio.sleep(1)  # 避免请求过快

        return results
