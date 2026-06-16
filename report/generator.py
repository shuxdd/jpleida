"""
报告生成器
==========

生成和导出竞品分析报告。
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from agent.llm import create_llm
from config.settings import settings
from report.templates import ReportTemplates
from utils.report_helpers import (
    generate_report_header,
    prepare_analysis_data,
    generate_fallback_report,
)

logger = logging.getLogger(__name__)


class ReportGenerator:
    """报告生成器"""

    def __init__(self):
        self.output_dir = settings.report_output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    async def generate(
        self,
        analysis_results: Dict[str, Any],
        report_type: str = "standard",
        competitors: Optional[List[str]] = None,
    ) -> str:
        """
        生成报告

        Args:
            analysis_results: 分析结果
            report_type: 报告类型 (quick/standard/deep)
            competitors: 竞品列表

        Returns:
            Markdown格式的报告
        """
        logger.info(f"开始生成{report_type}报告...")

        competitors = competitors or []
        prompt_template = ReportTemplates.get_prompt(report_type)

        try:
            llm = create_llm(temperature=0.3, max_tokens=8192)

            analysis_data = self._prepare_data(analysis_results, competitors)
            sections_text = self._build_sections_text(report_type)
            prompt = prompt_template.format(analysis_data=analysis_data, sections=sections_text)

            response = await llm.ainvoke(prompt)
            report_content = response.content

            header = self._generate_header(competitors, report_type)
            full_report = header + "\n\n" + report_content

            logger.info(f"报告生成完成，长度: {len(full_report)} 字符")
            return full_report

        except Exception as e:
            logger.error(f"LLM报告生成失败: {e}，使用降级方案")
            return self._generate_fallback(analysis_results, competitors, report_type)

    def export_markdown(self, report: str, filename: Optional[str] = None) -> str:
        """
        导出Markdown文件

        Args:
            report: 报告内容
            filename: 文件名（不含扩展名）

        Returns:
            文件路径
        """
        if filename is None:
            filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        filepath = os.path.join(self.output_dir, f"{filename}.md")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report)

        logger.info(f"Markdown报告已导出: {filepath}")
        return filepath

    def _prepare_data(self, analysis_results: Dict, competitors: List[str]) -> str:
        """准备报告数据"""
        data = {
            "competitors": competitors,
            **analysis_results,
        }
        return prepare_analysis_data(data)

    def _build_sections_text(self, report_type: str) -> str:
        """构建报告章节文本"""
        sections = ReportTemplates.get_sections(report_type)
        items = []
        for i, section in enumerate(sections, start=3):
            items.append(f"### {i}. {section}\n- 基于分析数据撰写{section}内容")
        return "\n\n".join(items)

    def _generate_header(self, competitors: List[str], report_type: str) -> str:
        """生成报告头部"""
        return generate_report_header(
            title="竞品分析报告",
            competitors=competitors,
            report_type=report_type,
        )

    def _generate_fallback(
        self, analysis_results: Dict, competitors: List[str], report_type: str
    ) -> str:
        """降级报告生成"""
        competitor_name = "、".join(competitors) if competitors else "未知竞品"
        analysis_data = {
            **analysis_results,
            "analysis_summary": analysis_results.get("summary", ""),
        }
        return generate_fallback_report(competitor_name, analysis_data)
