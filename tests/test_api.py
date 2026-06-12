"""
API 模块测试
============

测试 FastAPI 接口功能。
"""

import pytest
import pytest_asyncio
import asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import Mock, AsyncMock, patch


# ==================== 数据库层测试 ====================

class TestDatabase:
    """数据库模块测试"""

    def test_orm_models_exist(self):
        """测试 ORM 模型定义存在"""
        from api.database import CompetitorORM, AnalysisTaskORM, ReportORM

        assert CompetitorORM.__tablename__ == "competitors"
        assert AnalysisTaskORM.__tablename__ == "analysis_tasks"
        assert ReportORM.__tablename__ == "reports"

    def test_competitor_orm_columns(self):
        """测试竞品表字段"""
        from api.database import CompetitorORM

        columns = {c.name for c in CompetitorORM.__table__.columns}
        expected = {"id", "name", "website", "industry", "tags", "notes", "created_at", "updated_at"}
        assert expected.issubset(columns)

    def test_analysis_task_orm_columns(self):
        """测试分析任务表字段"""
        from api.database import AnalysisTaskORM

        columns = {c.name for c in AnalysisTaskORM.__table__.columns}
        expected = {"id", "competitors", "analysis_type", "dimensions", "my_product",
                    "status", "result", "error_message", "created_at", "completed_at"}
        assert expected.issubset(columns)

    def test_report_orm_columns(self):
        """测试报告表字段"""
        from api.database import ReportORM

        columns = {c.name for c in ReportORM.__table__.columns}
        expected = {"id", "analysis_id", "title", "report_type", "format", "content", "file_path", "created_at"}
        assert expected.issubset(columns)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
