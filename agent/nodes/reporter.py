"""
报告生成节点
============

使用LLM生成竞品分析报告，带质量反思机制。
"""

import re
import logging
from agent.graph_state import AgentState
from agent.llm import create_llm
from config.prompts import REPORT_PROMPT
from report.templates import ReportTemplates
from utils.retry import retry_async
from utils.report_helpers import (
    generate_report_header,
    generate_fallback_report,
    prepare_analysis_data,
)
from agent.progress import report_progress

logger = logging.getLogger(__name__)


async def generate_report(state: AgentState) -> dict:
    """
    报告生成节点

    根据分析结果生成Markdown格式的竞品分析报告。
    生成后自动检查质量，不达标时反馈给LLM重生成一次。
    """
    logger.info("开始生成报告...")

    analysis_results = state.get("analysis_results", {})
    competitors = state.get("competitors", [])
    my_product = state.get("my_product")
    dimensions = state.get("dimensions", ["features", "pricing", "swot"])

    # 提取用户填写的竞品补充信息
    competitors_meta = state.get("collection_plan", {}).get("competitors_meta", {})
    competitor_notes = {}
    for name, meta in competitors_meta.items():
        if meta.get("notes"):
            competitor_notes[name] = meta["notes"]

    # 根据勾选的维度动态生成章节
    dimension_sections = {
        "features": "### 3. 功能对比\n- 功能矩阵表格（功能 vs 竞品，打勾/打叉）\n- 关键差异点分析",
        "pricing": "### 4. 定价分析\n- 定价模式对比表格\n- 性价比分析",
        "swot": "### 5. SWOT对比\n- 每个竞品的SWOT要点\n- 横向对比总结",
        "reviews": "### 6. 用户评价\n- 各竞品评分对比\n- 用户评价关键词和趋势",
    }
    section_order = ["features", "pricing", "swot", "reviews"]
    selected_sections = [dimension_sections[d] for d in section_order if d in dimensions]
    if not selected_sections:
        selected_sections = [dimension_sections[d] for d in section_order]

    try:
        llm = create_llm(temperature=0.3, max_tokens=8192)

        # 根据是否有我方产品选择模板
        report_type = "comparison" if my_product else "standard"
        template_label = "对比分析" if my_product else "标准分析"
        logger.info(f"使用{template_label}模板，维度: {', '.join(dimensions)}")

        analysis_data = _prepare_analysis_data(analysis_results, competitors, my_product, competitor_notes)
        base_prompt = ReportTemplates.get_prompt(report_type).format(
            analysis_data=analysis_data,
            sections="\n\n".join(selected_sections),
        )

        # 生成 + 质量反思循环（最多 2 次）
        report = ""
        prompt = base_prompt

        for attempt in range(2):
            response = await retry_async(lambda: llm.ainvoke(prompt))
            report = response.content

            if attempt == 0:
                issues = _check_report_quality(report, competitors)
                if not issues:
                    logger.info("报告质量检查通过")
                    break
                logger.warning(f"报告质量检查发现问题，重新生成: {issues}")
                prompt = base_prompt + (
                    "\n\n[质量反馈] 上次生成的报告存在以下问题，请修改完善：\n"
                    + "\n".join(f"- {issue}" for issue in issues)
                )
            else:
                logger.info("二次生成完成")

        # 添加报告头部
        header = _generate_header(competitors)
        full_report = header + "\n\n" + report

        logger.info(f"报告生成完成，长度: {len(full_report)} 字符")
        report_progress(state.get("progress_callback"), "reporter")
        return {
            "report": full_report,
            "status": "completed",
            "errors": state.get("errors", [])
        }

    except Exception as e:
        logger.error(f"报告生成失败: {e}")
        # 降级：生成简单报告
        simple_report = _generate_simple_report(analysis_results, competitors)
        return {
            "report": simple_report,
            "status": "completed",
            "errors": state.get("errors", []) + [f"报告生成警告: {str(e)}，已生成简化报告"]
        }


def _check_report_quality(report: str, competitors: list) -> list:
    """
    报告质量检查（规则驱动，不额外调用 LLM）

    检查项：
    - 长度是否过短（少于 300 字说明 LLM 偷懒了）
    - 是否有 Markdown 章节结构
    - 是否提到了竞品名称
    """
    issues = []

    # 1. 长度检查
    if len(report) < 300:
        issues.append("报告内容过短（少于300字），请展开每个章节，补充具体数据和分析")

    # 2. 章节结构检查
    section_count = len(re.findall(r'^##\s+\S', report, re.MULTILINE))
    if section_count < 2:
        issues.append("缺少必要的 Markdown 章节（##），请按要求的格式分章节生成")

    # 3. 竞品名称检查（至少覆盖一半）
    matched = sum(1 for c in competitors if c in report)
    if competitors and matched < max(1, len(competitors) // 2):
        names = "、".join(competitors)
        issues.append(f"报告未充分覆盖所有竞品（{names}），请确保每个竞品都有独立分析")

    return issues


def _prepare_analysis_data(analysis_results: dict, competitors: list, my_product: str = None, competitor_notes: dict = None) -> str:
    """准备报告所需的分析数据，只包含实际完成的维度"""
    dimension_keys = ["feature_matrix", "pricing_comparison", "swot_analysis", "review_analysis"]
    data = {
        "competitors": competitors,
        "competitor_notes": competitor_notes or {},
        "analysis_summary": analysis_results.get("summary", ""),
    }
    if my_product:
        data["my_product"] = my_product
    for key in dimension_keys:
        val = analysis_results.get(key)
        if val:
            data[key] = val

    return prepare_analysis_data(data)


def _generate_header(competitors: list) -> str:
    """生成报告头部，委托给 utils.report_helpers"""
    return generate_report_header(
        title="竞品分析报告",
        competitors=competitors,
        report_type="standard",
    )


def _generate_simple_report(analysis_results: dict, competitors: list) -> str:
    """生成简化报告（降级方案），委托给 utils.report_helpers"""
    analysis_data = {
        "analysis_summary": analysis_results.get("summary", ""),
        "feature_matrix": analysis_results.get("feature_matrix", {}),
        "pricing_comparison": analysis_results.get("pricing_comparison", {}),
        "swot_analysis": analysis_results.get("swot_analysis", {}),
    }

    reports = []
    for competitor in competitors:
        reports.append(generate_fallback_report(competitor, analysis_data))

    return "\n\n".join(reports)
