"""
爬取节点
========

爬取搜索结果中的网页内容。
"""

import logging
from agent.graph_state import AgentState
from collector.web_scraper import WebScraperCollector
from collector.cleaner import DataCleaner
from config.settings import settings
from agent.progress import report_progress

logger = logging.getLogger(__name__)


async def scrape_data(state: AgentState) -> dict:
    """
    爬取节点

    从搜索结果中提取URL，爬取网页内容。
    """
    logger.info("开始爬取网页数据...")

    raw_data = state.get("raw_data", [])
    all_scraped = []
    max_urls_per_competitor = 3  # 每个竞品最多爬取的URL数

    try:
        scraper = WebScraperCollector(
            timeout=settings.scrape_timeout,
            max_retries=settings.max_retries,
            headless=True
        )

        for entry in raw_data:
            if entry.get("source") != "web_search":
                continue

            competitor = entry.get("competitor", "")
            search_results = entry.get("data", {}).get("results", [])

            # 取前N个URL
            urls = [r["url"] for r in search_results[:max_urls_per_competitor] if r.get("url")]

            if not urls:
                logger.info(f"  {competitor}: 无可爬取的URL")
                continue

            logger.info(f"  爬取 {competitor}: {len(urls)} 个页面")

            try:
                scraped_pages = await scraper.scrape_multiple(urls, max_concurrent=2)

                for page in scraped_pages:
                    if page.get("status") == "success":
                        page_data = page.get("data", {})
                        text = page_data.get("text", "")
                        cleaned_text = DataCleaner.clean_text(text)

                        all_scraped.append({
                            "competitor": competitor,
                            "source": "web_scrape",
                            "url": page_data.get("url", page.get("target", "")),
                            "title": page_data.get("title", ""),
                            "text": cleaned_text[:10000],
                            "text_length": len(cleaned_text)
                        })

                logger.info(f"  {competitor}: 成功爬取 {len(scraped_pages)} 个页面")

            except Exception as e:
                logger.warning(f"  爬取 {competitor} 失败: {e}")
                all_scraped.append({
                    "competitor": competitor,
                    "source": "web_scrape",
                    "error": str(e)
                })

        scraper.close()
        logger.info(f"爬取完成，共获取 {len(all_scraped)} 个页面")
        report_progress(state.get("progress_callback"), "scraper")

        return {
            "raw_data": all_scraped,
            "status": "collecting",
            "errors": state.get("errors", [])
        }

    except Exception as e:
        logger.error(f"爬取节点失败: {e}")
        return {
            "raw_data": all_scraped,
            "status": "collecting",
            "errors": state.get("errors", []) + [f"爬取节点错误: {str(e)}"]
        }
