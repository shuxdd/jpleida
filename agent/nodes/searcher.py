"""
搜索节点
========

使用搜索引擎、GitHub、应用商店等多数据源采集竞品信息。
"""

import logging
from agent.graph_state import AgentState
from collector.web_search import WebSearchCollector
from collector.github_collector import GitHubCollector
from collector.app_store_collector import AppStoreCollector
from collector.huawei_collector import HuaweiCollector
from config.settings import settings
from utils.retry import retry_async
from agent.progress import report_progress

logger = logging.getLogger(__name__)

# 竞品名称到 GitHub 仓库的映射
GITHUB_REPOS = {
    "notion": "makenotion/notion-sdk-js",
    "obsidian": "obsidianmd/obsidian-releases",
}

# 竞品名称到 Google Play 应用 ID 的映射
GOOGLE_PLAY_APPS = {
    "notion": "notion.id",
    "obsidian": "md.obsidian",
    "钉钉": "com.alibaba.android.rimet",
    "企业微信": "com.tencent.wework",
    "飞书文档": "com.ss.android.lark",
}

# 竞品名称到华为应用市场包名的映射
HUAWEI_APPS = {
    "钉钉": "com.alibaba.android.rimet",
    "企业微信": "com.tencent.wework",
    "飞书文档": "com.ss.android.lark",
    "文心一言": "com.baidu.baiduapp",
    "通义千问": "com.aliyun.tongyi",
    "小红书": "com.xingin.xhs",
    "知乎": "com.zhihu.android",
    "B站": "tv.danmaku.bili",
    "有赞": "com.youzan.shop",
}

# 标签到数据源的映射
TAG_DATA_SOURCES = {
    "开源": ["github"],
    "开发者工具": ["github"],
    "GitHub": ["github"],
    "App": ["app_store"],
    "移动": ["app_store"],
    "C端": ["app_store"],
}


def _get_extra_sources(competitor_name: str, plan: dict) -> list:
    """根据竞品标签决定额外数据源"""
    sources = []
    competitors_meta = plan.get("competitors_meta", {})
    tags = competitors_meta.get(competitor_name, {}).get("tags", [])

    for tag in tags:
        if tag in TAG_DATA_SOURCES:
            sources.extend(TAG_DATA_SOURCES[tag])

    return list(set(sources))


async def search_competitors(state: AgentState) -> dict:
    """
    搜索节点

    根据采集计划，从多个数据源采集竞品信息：
    - 网页搜索（始终执行）
    - GitHub（按标签或映射表）
    - 应用商店（按标签或映射表）
    """
    logger.info("开始搜索竞品信息...")

    plan = state.get("collection_plan", {})
    competitors = plan.get("competitors", state["competitors"])
    all_results = []

    # 初始化采集器
    search_collector = WebSearchCollector(api_key=settings.serpapi_key)
    github_collector = GitHubCollector(token=settings.github_token)
    app_store_collector = AppStoreCollector()
    huawei_collector = HuaweiCollector()

    for comp in competitors:
        name = comp if isinstance(comp, str) else comp.get("name", "")
        keywords = [] if isinstance(comp, str) else comp.get("search_keywords", [])
        name_lower = name.lower()

        # 1. 网页搜索（始终执行）
        logger.info(f"搜索竞品: {name}")
        try:
            result = await retry_async(
                lambda: search_collector.search_competitor(
                    name,
                    keywords=keywords if keywords else None,
                    num_results=5
                )
            )
            all_results.append({
                "competitor": name,
                "source": "web_search",
                "data": result
            })
            logger.info(f"  搜索完成，找到 {result.get('total_results', 0)} 条结果")
        except Exception as e:
            logger.warning(f"  搜索 {name} 失败: {e}")
            all_results.append({
                "competitor": name,
                "source": "web_search",
                "data": {"results": [], "total_results": 0},
                "error": str(e)
            })

        # 2. GitHub 采集（按需）
        extra_sources = _get_extra_sources(name, plan)
        if "github" in extra_sources or name_lower in GITHUB_REPOS:
            repo_name = GITHUB_REPOS.get(name_lower)
            if repo_name:
                logger.info(f"  采集 GitHub: {repo_name}")
                try:
                    gh_result = await github_collector.run(repo_name)
                    all_results.append({
                        "competitor": name,
                        "source": "github",
                        "data": gh_result.get("data", {})
                    })
                    logger.info(f"  GitHub 完成: ⭐{gh_result.get('data', {}).get('stars', 0)}")
                except Exception as e:
                    logger.warning(f"  GitHub {name} 失败: {e}")

        # 3. 应用商店采集（按需）
        if "app_store" in extra_sources or name_lower in GOOGLE_PLAY_APPS:
            app_id = GOOGLE_PLAY_APPS.get(name_lower)
            if app_id:
                logger.info(f"  采集应用商店: {app_id}")
                try:
                    app_result = await app_store_collector.run(app_id, store="google")
                    all_results.append({
                        "competitor": name,
                        "source": "app_store",
                        "data": app_result.get("data", {})
                    })
                    logger.info(f"  应用商店完成: ⭐{app_result.get('data', {}).get('rating', 0)}")
                except Exception as e:
                    logger.warning(f"  应用商店 {name} 失败: {e}")

        # 4. 华为应用市场采集（按需，有密钥文件时启用）
        if name_lower in HUAWEI_APPS and settings.huawei_key_file:
            pkg_name = HUAWEI_APPS[name_lower]
            logger.info(f"  采集华为应用市场: {pkg_name}")
            try:
                hw_result = await huawei_collector.run(pkg_name, max_size=30)
                all_results.append({
                    "competitor": name,
                    "source": "huawei",
                    "data": hw_result.get("data", {})
                })
                logger.info(f"  华为完成: ⭐{hw_result.get('data', {}).get('rating', 0)}")
            except Exception as e:
                logger.warning(f"  华为 {name} 失败: {e}")

    logger.info(f"搜索完成，共处理 {len(competitors)} 个竞品")
    report_progress(state.get("progress_callback"), "searcher")
    return {
        "raw_data": all_results,
        "status": "collecting",
        "errors": state.get("errors", [])
    }
