"""
数据库模块
==========

异步 SQLAlchemy 引擎、Session 和 ORM 模型定义。
"""

import uuid
from datetime import datetime
from typing import AsyncGenerator

from sqlalchemy import Column, String, Text, DateTime, JSON
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config.settings import settings


# 异步引擎（默认使用 SQLite）
DATABASE_URL = f"sqlite+aiosqlite:///{settings.chroma_persist_dir}/../app.db"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def generate_uuid() -> str:
    return str(uuid.uuid4())


class CompetitorORM(Base):
    """竞品 ORM 模型"""
    __tablename__ = "competitors"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    website = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    tags = Column(JSON, default=list)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class AnalysisTaskORM(Base):
    """分析任务 ORM 模型"""
    __tablename__ = "analysis_tasks"

    id = Column(String, primary_key=True, default=generate_uuid)
    competitors = Column(JSON, nullable=False)
    analysis_type = Column(String, default="standard")
    dimensions = Column(JSON, default=list)
    my_product = Column(String, nullable=True)
    status = Column(String, default="pending")
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime, nullable=True)


class ReportORM(Base):
    """报告 ORM 模型"""
    __tablename__ = "reports"

    id = Column(String, primary_key=True, default=generate_uuid)
    analysis_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    report_type = Column(String, default="standard")
    format = Column(String, default="markdown")
    content = Column(Text, nullable=False)
    file_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)


async def init_db():
    """初始化数据库（创建表）"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """依赖注入：获取数据库 session"""
    async with async_session() as session:
        yield session
