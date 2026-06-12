"""
网页爬取采集器
==============

爬取网页内容，提取文本信息。
"""

from typing import List, Dict, Any, Optional
import asyncio
import logging

from .base import BaseCollector
from utils.text_utils import clean_text as utils_clean_text
from utils.cache import CacheManager, make_cache_key
from config.settings import settings

logger = logging.getLogger(__name__)


class WebScraperCollector(BaseCollector):
    """网页爬取采集器"""

    def __init__(
        self,
        timeout: int = 30,
        max_retries: int = 3,
        headless: bool = True,
        user_agent: Optional[str] = None
    ):
        """
        初始化爬取采集器

        Args:
            timeout: 超时时间（秒）
            max_retries: 最大重试次数
            headless: 是否无头模式
            user_agent: 用户代理
        """
        super().__init__(name="web_scraper")
        self.timeout = timeout
        self.max_retries = max_retries
        self.headless = headless
        self.user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        self._driver = None
        self._cache = CacheManager(redis_url=settings.redis_url, prefix="scrape")

    def _get_driver(self):
        """获取Selenium WebDriver"""
        if self._driver is None:
            try:
                from selenium import webdriver
                from selenium.webdriver.chrome.options import Options
                from selenium.webdriver.chrome.service import Service

                options = Options()
                if self.headless:
                    options.add_argument("--headless")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument(f"user-agent={self.user_agent}")
                options.add_argument("--disable-gpu")
                options.add_argument("--window-size=1920,1080")

                self._driver = webdriver.Chrome(options=options)
                self._driver.set_page_load_timeout(self.timeout)

            except ImportError:
                raise ImportError("请安装selenium: pip install selenium")
            except Exception as e:
                logger.error(f"初始化WebDriver失败: {e}")
                raise

        return self._driver

    async def collect(
        self,
        target: str,
        wait_for: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        爬取网页

        Args:
            target: 网页URL
            wait_for: 等待元素选择器
            **kwargs: 其他参数

        Returns:
            网页内容
        """
        # 检查缓存
        cache_key = make_cache_key("page", target)
        cached = self._cache.get(cache_key)
        if cached is not None:
            self.logger.info(f"网页缓存命中: {target}")
            return cached

        driver = self._get_driver()

        for attempt in range(self.max_retries):
            try:
                # 加载页面
                driver.get(target)

                # 等待页面加载
                if wait_for:
                    from selenium.webdriver.support.ui import WebDriverWait
                    from selenium.webdriver.support import expected_conditions as EC
                    from selenium.webdriver.common.by import By

                    WebDriverWait(driver, self.timeout).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, wait_for))
                    )
                else:
                    # 默认等待body加载
                    await asyncio.sleep(2)

                # 获取页面内容
                page_source = driver.page_source
                current_url = driver.current_url
                title = driver.title

                result = {
                    "url": target,
                    "current_url": current_url,
                    "title": title,
                    "html": page_source,
                    "status": "success"
                }

                # 写入缓存（7天）
                self._cache.set(cache_key, result, ttl=3600 * 24 * 7)

                return result

            except Exception as e:
                logger.warning(f"爬取失败 (尝试 {attempt + 1}/{self.max_retries}): {target}, 错误: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2)
                else:
                    return {
                        "url": target,
                        "error": str(e),
                        "status": "error"
                    }

    def parse(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析网页内容

        Args:
            raw_data: 原始网页数据

        Returns:
            解析后的数据
        """
        if raw_data.get("status") == "error":
            return raw_data

        try:
            from bs4 import BeautifulSoup

            html = raw_data.get("html", "")
            soup = BeautifulSoup(html, "html.parser")

            # 移除脚本和样式
            for element in soup(["script", "style", "nav", "footer", "header"]):
                element.decompose()

            # 提取文本
            text = soup.get_text(separator="\n", strip=True)

            # 清理文本
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            clean_text = "\n".join(lines)

            # 提取链接
            links = []
            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                text = link.get_text(strip=True)
                if href and text:
                    links.append({"url": href, "text": text})

            # 提取图片
            images = []
            for img in soup.find_all("img", src=True):
                src = img.get("src", "")
                alt = img.get("alt", "")
                if src:
                    images.append({"src": src, "alt": alt})

            # 提取meta信息
            meta_info = {}
            for meta in soup.find_all("meta"):
                name = meta.get("name", meta.get("property", ""))
                content = meta.get("content", "")
                if name and content:
                    meta_info[name] = content

            return {
                "url": raw_data.get("url", ""),
                "current_url": raw_data.get("current_url", ""),
                "title": raw_data.get("title", ""),
                "text": clean_text[:10000],  # 限制长度
                "links": links[:100],  # 限制数量
                "images": images[:50],
                "meta": meta_info,
                "text_length": len(clean_text),
                "status": "success"
            }

        except ImportError:
            logger.warning("未安装beautifulsoup4，返回原始HTML")
            return {
                "url": raw_data.get("url", ""),
                "title": raw_data.get("title", ""),
                "html": raw_data.get("html", "")[:5000],
                "status": "success"
            }
        except Exception as e:
            logger.error(f"解析失败: {e}")
            return {
                "url": raw_data.get("url", ""),
                "error": str(e),
                "status": "error"
            }

    def clean(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """清洗网页内容"""
        if data.get("status") == "error":
            return data

        text = data.get("text", "")
        text = utils_clean_text(text)

        data["text"] = text
        data["text_length"] = len(data["text"])

        return data

    async def scrape_multiple(
        self,
        urls: List[str],
        max_concurrent: int = 3
    ) -> List[Dict[str, Any]]:
        """
        批量爬取

        Args:
            urls: URL列表
            max_concurrent: 最大并发数

        Returns:
            爬取结果列表
        """
        results = []
        semaphore = asyncio.Semaphore(max_concurrent)

        async def scrape_with_semaphore(url):
            async with semaphore:
                return await self.run(url)

        tasks = [scrape_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "status": "error",
                    "url": urls[i],
                    "error": str(result)
                })
            else:
                processed_results.append(result)

        return processed_results

    async def scrape_competitor_website(
        self,
        website_url: str,
        pages: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        爬取竞品网站

        Args:
            website_url: 网站URL
            pages: 要爬取的页面路径列表

        Returns:
            爬取结果
        """
        if pages is None:
            pages = ["/", "/about", "/products", "/pricing"]

        results = {}

        for page in pages:
            url = f"{website_url.rstrip('/')}{page}"
            result = await self.run(url)
            results[page] = result
            await asyncio.sleep(1)  # 避免请求过快

        return {
            "website": website_url,
            "pages": results,
            "total_pages": len(pages),
            "success_count": sum(1 for r in results.values() if r.get("status") == "success")
        }

    def close(self):
        """关闭WebDriver"""
        if self._driver:
            try:
                self._driver.quit()
            except Exception:
                pass
            self._driver = None

    def __del__(self):
        """析构函数"""
        self.close()
