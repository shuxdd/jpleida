"""
报告质量评估节点
================

LLM-as-Judge：对生成的报告进行多维度质量评估。
"""

import json
import logging
from typing import Dict, Any

from agent.graph_state import AgentState
from agent.llm import create_llm
from config.prompts import EVALUATION_PROMPT
from utils.llm_parser import extract_json_from_llm
from utils.retry import retry_async
from agent.progress import report_progress

logger = logging.getLogger(__name__)


async def evaluate_report(state: AgentState) -> dict:
    """
    评估报告质量（LLM-as-Judge）

    对 reporter 生成的报告进行 4 维度评分并给出改进建议。
    """
    logger.info("开始评估报告质量...")

    report = state.get("report", "")
    competitors = state.get("competitors", [])
    dimensions = state.get("dimensions", [])

    if not report:
        logger.warning("报告为空，跳过评估")
        return {
            "evaluation": _empty_result("报告为空，无法评估"),
            "status": state.get("status"),
            "errors": state.get("errors", []) + ["评估跳过: 报告为空"],
        }

    try:
        result = await _llm_evaluate(report, competitors, dimensions)

        # 确保必填字段
        for dim in ["coverage", "depth", "structure", "actionability"]:
            if dim in result:
                score = result[dim].get("score", 3)
                result[dim]["score"] = max(1, min(5, int(score)))
            else:
                result[dim] = {"score": 3, "reasoning": "未评估"}

        result["overall_score"] = max(1, min(5, int(result.get("overall_score", 3))))

        # 自动诊断：低分维度映射到需要改进的节点
        result["diagnosis"] = _generate_diagnosis(result)

        logger.info(f"报告评估完成，总分: {result['overall_score']}/5")
        report_progress(state.get("progress_callback"), "evaluator")
        return {
            "evaluation": result,
            "status": state.get("status"),
            "errors": state.get("errors", []),
        }

    except Exception as e:
        logger.error(f"报告评估失败: {e}")
        return {
            "evaluation": _empty_result(f"评估过程出错: {str(e)}"),
            "status": state.get("status"),
            "errors": state.get("errors", []) + [f"评估节点错误: {str(e)}"],
        }


async def _llm_evaluate(report: str, competitors: list, dimensions: list) -> Dict[str, Any]:
    """调用 LLM 进行报告质量评估"""
    llm = create_llm(temperature=0.2)

    prompt = EVALUATION_PROMPT.format(
        report_content=report[:8000],
        competitors="、".join(competitors),
        dimensions="、".join(dimensions),
    )

    response = await retry_async(lambda: llm.ainvoke(prompt))
    content = response.content

    result = extract_json_from_llm(content)
    if result is None:
        logger.warning("评估结果解析失败，使用默认值")
        return _empty_result("LLM 返回格式异常")

    return result


def _generate_diagnosis(evaluation: Dict[str, Any]) -> list:
    """根据评分生成节点改进诊断"""
    diagnosis = []

    score_map = {
        "coverage": ("searcher/scraper", "采集阶段可能不足，建议补充搜索关键词或数据源"),
        "depth": ("extractor/analyzer", "分析深度不够，建议检查提取粒度或分析 Prompt"),
        "structure": ("reporter", "报告结构需改进，建议检查章节组织和 Markdown 格式"),
        "actionability": ("analyzer/reporter", "战略建议太泛，Prompt 需强调具体可执行场景"),
    }

    for dim, (node, suggestion) in score_map.items():
        score = evaluation.get(dim, {}).get("score", 0)
        if score < 3:
            diagnosis.append(f"[{node}] {suggestion}")
        elif score < 4:
            diagnosis.append(f"[{node}] 表现尚可，仍有提升空间")

    return diagnosis


def _empty_result(reason: str) -> dict:
    """返回空评估结果"""
    return {
        "coverage": {"score": 0, "reasoning": reason},
        "depth": {"score": 0, "reasoning": reason},
        "structure": {"score": 0, "reasoning": reason},
        "actionability": {"score": 0, "reasoning": reason},
        "overall_score": 0,
        "overall_summary": reason,
        "key_improvements": [],
        "diagnosis": [],
    }
