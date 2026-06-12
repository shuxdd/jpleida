"""
配置设置
========

管理全局配置和环境变量。
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """应用配置"""

    # LLM配置（MIMO - OpenAI兼容格式）
    openai_api_key: str = ""
    openai_api_base: str = "https://api.xiaomimimo.com/v1"
    default_model: str = "mimo-v2-omni"

    # 向量数据库配置
    chroma_persist_dir: str = "./data/chroma"
    chroma_collection_name: str = "competitors"

    # Redis配置
    redis_url: str = "redis://localhost:6379/0"

    # SerpAPI配置
    serpapi_key: str = ""

    # GitHub配置
    github_token: str = ""

    # 华为应用市场配置
    huawei_key_file: str = ""

    # 爬虫配置
    scrape_timeout: int = 30
    max_retries: int = 3
    request_delay: float = 1.0

    # 报告配置
    report_output_dir: str = "./data/reports"

    # 安全配置
    secret_key: str = "your-secret-key-change-in-production"
    jwt_expire_hours: int = 24

    # 日志配置
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 创建全局配置实例
settings = Settings()
