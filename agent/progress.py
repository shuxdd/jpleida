"""
进度上报
========

节点进度回调工具。
"""

import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# 节点进度映射
NODE_PROGRESS = {
    "planner": (10, "任务规划完成"),
    "searcher": (25, "搜索完成"),
    "scraper": (45, "爬取完成"),
    "extractor": (65, "信息提取完成"),
    "analyzer": (85, "分析完成"),
    "reporter": (90, "报告生成完成"),
    "evaluator": (100, "评估报告质量完成"),
    "knowledge_store": (100, "知识库存储完成"),
}


def report_progress(
    callback: Optional[Callable],
    node_name: str,
    message: str = "",
):
    """
    上报节点进度

    Args:
        callback: 进度回调函数 (node_name, progress, message)
        node_name: 节点名称
        message: 自定义消息（为空时使用默认消息）
    """
    if callback is None:
        return

    progress, default_msg = NODE_PROGRESS.get(node_name, (0, ""))
    msg = message or default_msg

    try:
        callback(node_name, progress, msg)
    except Exception as e:
        logger.warning(f"进度回调失败: {e}")
