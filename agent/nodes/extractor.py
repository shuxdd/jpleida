"""
信息提取节点
============

使用LLM从爬取的网页中提取结构化竞品信息。
按竞品合并网页文本后批量提取，减少LLM调用次数。
"""

import logging
from typing import Dict, List, Any
from collections import defaultdict

from agent.graph_state import AgentState
from agent.llm import create_llm
from config.prompts import EXTRACTION_PROMPT
from utils.llm_parser import extract_json_from_llm
from utils.retry import retry_async
from agent.progress import report_progress

logger = logging.getLogger(__name__)

# 每个竞品合并文本的最大字符数
MAX_CHARS_PER_COMPETITOR = 8000


async def extract_info(state: AgentState) -> dict:
    """
    信息提取节点

    按竞品合并所有爬取的网页内容，每个竞品调一次LLM提取结构化信息。
    """
    logger.info("开始信息提取...")

    raw_data = state.get("raw_data", [])
    extracted = []

    try:
        llm = create_llm(temperature=0.1)

        # 按竞品分组收集所有爬取文本
        comp_pages: Dict[str, List[Dict]] = defaultdict(list)
        for entry in raw_data:
            if entry.get("source") != "web_scrape":
                continue
            text = entry.get("text", "")
            if not text or len(text) < 50:
                continue
            comp_pages[entry["competitor"]].append({
                "url": entry.get("url", ""),
                "title": entry.get("title", ""),
                "text": text,
            })

        if not comp_pages:
            logger.info("  无可用爬取数据")
            report_progress(state.get("progress_callback"), "extractor")
            return {
                "extracted_info": extracted,
                "status": "extracting",
                "errors": state.get("errors", [])
            }

        # 每个竞品合并文本后调一次LLM
        for competitor, pages in comp_pages.items():
            logger.info(f"  提取: {competitor}（{len(pages)} 个页面合并）")

            # 构建合并文本，带上来源标记
            merged_parts = []
            for p in pages:
                label = f"=== 来源: {p['url']} ==="
                merged_parts.append(f"{label}\n{p['text']}")
            merged_text = "\n\n".join(merged_parts)

            # 截断
            merged_text = merged_text[:MAX_CHARS_PER_COMPETITOR]

            try:
                prompt = EXTRACTION_PROMPT.format(content=merged_text)
                response = await retry_async(lambda: llm.ainvoke(prompt))
                content = response.content

                info = extract_json_from_llm(content)
                if info is None:
                    info = {"raw_response": content}

                extracted.append({
                    "competitor": competitor,
                    "source_url": "|".join(p["url"] for p in pages[:3]),
                    "pages_count": len(pages),
                    "extracted_info": info,
                })

                logger.info(f"    {competitor} 提取成功")

            except Exception as e:
                logger.warning(f"    {competitor} 提取失败: {e}")
                extracted.append({
                    "competitor": competitor,
                    "source_url": "",
                    "extracted_info": {},
                    "error": str(e),
                })

        logger.info(f"信息提取完成，共处理 {len(extracted)} 个竞品")
        report_progress(state.get("progress_callback"), "extractor")
        return {
            "extracted_info": extracted,
            "status": "extracting",
            "errors": state.get("errors", [])
        }

    except Exception as e:
        logger.error(f"信息提取节点失败: {e}")
        return {
            "extracted_info": extracted,
            "status": "extracting",
            "errors": state.get("errors", []) + [f"提取节点错误: {str(e)}"]
        }
