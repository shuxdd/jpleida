"""
工具模块 - 提供通用工具函数
"""

from utils.logger import setup_logger, get_logger
from utils.date_utils import format_datetime, get_current_timestamp
from utils.json_utils import json_serialize, json_dumps_pretty
from utils.text_utils import clean_text, split_text
from utils.llm_parser import extract_json_from_llm
from utils.metadata_utils import sanitize_metadata, sanitize_metadatas
from utils.report_helpers import (
    generate_report_header,
    prepare_analysis_data,
    generate_fallback_report,
    REPORT_TYPE_NAMES,
)

__all__ = [
    # 日志
    "setup_logger",
    "get_logger",
    # 日期
    "format_datetime",
    "get_current_timestamp",
    # JSON
    "json_serialize",
    "json_dumps_pretty",
    # 文本
    "clean_text",
    "split_text",
    # LLM 解析
    "extract_json_from_llm",
    # 元数据
    "sanitize_metadata",
    "sanitize_metadatas",
    # 报告
    "generate_report_header",
    "prepare_analysis_data",
    "generate_fallback_report",
    "REPORT_TYPE_NAMES",
]
