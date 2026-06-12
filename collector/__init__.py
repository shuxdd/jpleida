"""
数据采集模块
============

提供网页搜索、爬取和数据清洗功能。
"""

from .base import BaseCollector, CollectorResult
from .web_search import WebSearchCollector
from .web_scraper import WebScraperCollector
from .cleaner import DataCleaner
from .github_collector import GitHubCollector
from .app_store_collector import AppStoreCollector
from .huawei_collector import HuaweiCollector

__all__ = [
    "BaseCollector",
    "CollectorResult",
    "WebSearchCollector",
    "WebScraperCollector",
    "DataCleaner",
    "GitHubCollector",
    "AppStoreCollector",
    "HuaweiCollector",
]
