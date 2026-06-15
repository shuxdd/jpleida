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

    # Embedding配置（默认通义千问 text-embedding-v4）
    embedding_api_key: str = ""           # 为空则用 openai_api_key
    embedding_api_base: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    embedding_model: str = "text-embedding-v4"
    embedding_dimensions: int = 1024       # 向量维度

    # 数据库配置
    database_url: str = "sqlite+aiosqlite:///./data/app.db"

    # 向量数据库配置
    chroma_persist_dir: str = "./data/chroma"
    chroma_collection_name: str = "competitors"

    # Redis配置
    redis_url: str = "redis://localhost:6379/0"

    # SerpAPI配置
    serpapi_key: str = ""

    # GitHub配置
    github_token: str = ""

    # Apify配置
    apify_api_token: str = ""

    # 爬虫配置
    scrape_timeout: int = 30
    max_retries: int = 3
    request_delay: float = 1.0

    # 报告配置
    report_output_dir: str = "./data/reports"

    # 安全配置
    secret_key: str = "your-secret-key-change-in-production"
    jwt_expire_hours: int = 24

    # CORS 配置（生产环境改为具体域名，多个用逗号分隔）
    cors_origins: str = ""

    # 日志配置
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 创建全局配置实例
settings = Settings()
