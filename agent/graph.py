"""
LangGraph状态图
===============

组装竞品分析Agent的状态图。
"""

import logging
from langgraph.graph import StateGraph, START, END

from agent.graph_state import AgentState
from agent.nodes.planner import plan_analysis
from agent.nodes.searcher import search_competitors
from agent.nodes.scraper import scrape_data
from agent.nodes.extractor import extract_info
from agent.nodes.analyzer import analyze_competitors
from agent.nodes.reporter import generate_report
from agent.nodes.evaluator import evaluate_report

logger = logging.getLogger(__name__)


def create_analysis_graph():
    """
    创建竞品分析状态图

    流程: planner -> searcher -> scraper -> extractor -> analyzer -> reporter
    knowledge_store 在后端单独异步执行，不阻塞报告展示

    Returns:
        编译后的状态图
    """
    logger.info("创建竞品分析状态图...")

    graph = StateGraph(AgentState)

    # 注册节点
    graph.add_node("planner", plan_analysis)
    graph.add_node("searcher", search_competitors)
    graph.add_node("scraper", scrape_data)
    graph.add_node("extractor", extract_info)
    graph.add_node("analyzer", analyze_competitors)
    graph.add_node("reporter", generate_report)
    graph.add_node("evaluator", evaluate_report)

    # 直线流程（知识库入库单独异步执行）
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "searcher")
    graph.add_edge("searcher", "scraper")
    graph.add_edge("scraper", "extractor")
    graph.add_edge("extractor", "analyzer")
    graph.add_edge("analyzer", "reporter")
    graph.add_edge("reporter", "evaluator")
    graph.add_edge("evaluator", END)

    logger.info("状态图创建完成")
    return graph.compile()
