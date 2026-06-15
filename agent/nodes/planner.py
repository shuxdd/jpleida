"""
任务规划节点
============

使用LLM生成数据采集计划。
"""

import json
import logging
from typing import Any
from agent.graph_state import AgentState
from agent.llm import create_llm
from config.prompts import PLANNING_PROMPT
from utils.llm_parser import extract_json_from_llm
from utils.retry import retry_async
from agent.progress import report_progress

logger = logging.getLogger(__name__)


async def plan_analysis(state: AgentState) -> dict:
    """
    任务规划节点

    根据竞品列表和分析维度，使用LLM生成采集计划。
    """
    logger.info("开始任务规划...")

    competitors = state["competitors"]
    analysis_type = state.get("analysis_type", "standard")
    dimensions = state.get("dimensions", ["features", "pricing", "swot"])

    try:
        llm = create_llm(temperature=0.3)

        prompt = PLANNING_PROMPT.format(
            competitors=", ".join(competitors),
            analysis_type=analysis_type,
            dimensions=", ".join(dimensions)
        )

        response = await retry_async(lambda: llm.ainvoke(prompt))
        content = response.content

        # 尝试解析JSON
        try:
            plan = extract_json_from_llm(content)
            if plan is None:
                raise json.JSONDecodeError("无法解析 JSON", content, 0)
        except json.JSONDecodeError:
            # 如果解析失败，生成默认计划
            logger.warning("LLM返回的计划无法解析为JSON，使用默认计划")
            plan = _generate_default_plan(competitors, dimensions)

        # 保留已有的 competitors_meta（如 google_play_id 等）
        existing_meta = state.get("collection_plan", {}).get("competitors_meta", {})
        if existing_meta:
            plan["competitors_meta"] = existing_meta

        logger.info(f"任务规划完成，计划包含 {len(plan.get('competitors', []))} 个竞品")
        report_progress(state.get("progress_callback"), "planner")
        return {
            "collection_plan": plan,
            "status": "planning",
            "errors": []
        }

    except Exception as e:
        logger.error(f"任务规划失败: {e}")
        # 使用默认计划作为降级
        plan = _generate_default_plan(competitors, dimensions)
        # 降级时也保留 competitors_meta
        existing_meta = state.get("collection_plan", {}).get("competitors_meta", {})
        if existing_meta:
            plan["competitors_meta"] = existing_meta
        report_progress(state.get("progress_callback"), "planner")
        return {
            "collection_plan": plan,
            "status": "planning",
            "errors": [f"规划节点警告: {str(e)}，使用默认计划"]
        }


def _generate_default_plan(competitors: list, dimensions: list) -> dict:
    """生成默认采集计划"""
    plan = {
        "competitors": [],
        "analysis_dimensions": dimensions
    }

    for name in competitors:
        competitor_plan = {
            "name": name,
            "search_keywords": [
                f"{name} 官网",
                f"{name} 产品",
                f"{name} 定价",
                f"{name} 功能特点"
            ],
            "target_urls": [],
            "info_types": ["company_info", "products", "pricing", "features"]
        }
        plan["competitors"].append(competitor_plan)

    return plan
