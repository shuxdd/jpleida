from datetime import datetime

from utils.date_utils import format_datetime
from utils.json_utils import json_serialize


# 报告类型中文映射
REPORT_TYPE_NAMES = {
    "quick": "快速",
    "standard": "标准",
    "deep": "深度",
}


def generate_report_header(
    title: str,
    competitors: list[str],
    report_type: str
) -> str:
    """
    生成报告头部。

    Args:
        title: 报告标题
        competitors: 竞品名称列表
        report_type: 报告类型（quick/standard/deep）

    Returns:
        Markdown 格式的报告头部
    """
    type_name = REPORT_TYPE_NAMES.get(report_type, report_type)
    now = format_datetime()

    header = f"""# {title}

**生成时间**: {now}
**分析类型**: {type_name}
**分析竞品数量**: {len(competitors)}

## 分析竞品

"""
    for i, name in enumerate(competitors, 1):
        header += f"{i}. {name}\n"

    return header


def prepare_analysis_data(analysis_result: dict) -> str:
    """
    准备报告数据，将分析结果转换为 JSON 字符串。

    Args:
        analysis_result: 分析结果字典

    Returns:
        JSON 格式的报告数据
    """
    return json_serialize(analysis_result)


def generate_fallback_report(
    competitor_name: str,
    analysis_data: dict
) -> str:
    """
    生成降级报告（当 LLM 失败时）。

    Args:
        competitor_name: 竞品名称
        analysis_data: 分析数据

    Returns:
        简化的 Markdown 报告
    """
    header = generate_report_header(
        title=f"{competitor_name} 竞品分析报告",
        competitors=[competitor_name],
        report_type="quick"
    )

    sections = [header]

    # 分析摘要
    summary = analysis_data.get("analysis_summary", "")
    if summary:
        sections.append(f"## 分析摘要\n\n{summary}\n")

    # 功能矩阵
    feature_matrix = analysis_data.get("feature_matrix", {})
    features = feature_matrix.get("features", [])[:10]
    if features:
        sections.append("## 主要功能\n")
        for f in features:
            name = f.get("name", "未知功能")
            desc = f.get("description", "")
            sections.append(f"- **{name}**: {desc}")
        sections.append("")

    # 定价对比
    pricing = analysis_data.get("pricing_comparison", {})
    competitors_pricing = pricing.get("competitors", {})
    if competitors_pricing:
        sections.append("## 定价信息\n")
        for comp, info in competitors_pricing.items():
            if isinstance(info, dict):
                price = info.get("price", "未知")
                sections.append(f"- **{comp}**: {price}")
            else:
                sections.append(f"- **{comp}**: {info}")
        sections.append("")

    # SWOT 分析
    swot = analysis_data.get("swot_analysis", {})
    if swot:
        sections.append("## SWOT 分析\n")
        for item in swot.get("strengths", [])[:3]:
            if isinstance(item, str):
                sections.append(f"- 优势: {item}")
        for item in swot.get("weaknesses", [])[:3]:
            if isinstance(item, str):
                sections.append(f"- 劣势: {item}")
        sections.append("")

    # 时间戳
    sections.append(f"\n---\n*报告生成时间: {format_datetime()}*\n")

    return "\n".join(sections)
