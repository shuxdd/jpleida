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

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

# 测试用内存数据库
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
test_async_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    """每个测试前创建表，测试后清理"""
    from api.database import Base
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_session():
    """覆盖数据库依赖"""
    async with test_async_session() as session:
        yield session


@pytest_asyncio.fixture
async def test_app():
    """创建测试用 FastAPI 应用"""
    from api.app import create_app
    from api.database import get_session
    app = create_app()
    app.dependency_overrides[get_session] = override_get_session
    return app


@pytest_asyncio.fixture
async def client(test_app):
    """创建测试客户端"""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


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


# ==================== Schema 测试 ====================

class TestSchemas:
    """API Schema 测试"""

    def test_competitor_response_schema(self):
        """测试竞品响应 Schema"""
        from api.schemas import CompetitorResponse

        data = {
            "id": "test-id",
            "name": "竞品A",
            "website": "https://example.com",
            "industry": "SaaS",
            "tags": ["AI"],
            "notes": None,
            "created_at": "2026-06-12T00:00:00",
            "updated_at": "2026-06-12T00:00:00",
        }
        resp = CompetitorResponse(**data)
        assert resp.id == "test-id"
        assert resp.name == "竞品A"

    def test_analysis_submit_response(self):
        """测试分析提交响应 Schema"""
        from api.schemas import AnalysisSubmitResponse

        resp = AnalysisSubmitResponse(
            task_id="task-123",
            status="pending",
            message="分析任务已提交",
        )
        assert resp.task_id == "task-123"
        assert resp.status == "pending"

    def test_api_response_wrapper(self):
        """测试统一响应包装"""
        from api.schemas import ApiResponse

        resp = ApiResponse(code=200, data={"key": "value"}, message="success")
        assert resp.code == 200
        assert resp.data["key"] == "value"

    def test_qa_request_schema(self):
        """测试问答请求 Schema"""
        from api.schemas import QARequest

        req = QARequest(question="Notion 的定价是什么？")
        assert req.question == "Notion 的定价是什么？"
        assert req.competitors is None

    def test_qa_response_schema(self):
        """测试问答响应 Schema"""
        from api.schemas import QAResponse

        resp = QAResponse(
            answer="Notion 提供免费版和付费版",
            sources=["竞品知识库"],
        )
        assert "Notion" in resp.answer
        assert len(resp.sources) == 1


class TestCompetitorRoutes:
    """竞品路由测试"""

    @pytest.mark.asyncio
    async def test_create_competitor(self, client):
        """测试创建竞品"""
        resp = await client.post("/api/competitors", json={
            "name": "Notion",
            "website": "https://notion.so",
            "industry": "SaaS",
            "tags": ["笔记", "协作"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
        assert data["data"]["name"] == "Notion"

    @pytest.mark.asyncio
    async def test_list_competitors(self, client):
        """测试获取竞品列表"""
        await client.post("/api/competitors", json={"name": "TestComp"})
        resp = await client.get("/api/competitors")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_get_competitor(self, client):
        """测试获取竞品详情"""
        create_resp = await client.post("/api/competitors", json={"name": "DetailComp"})
        comp_id = create_resp.json()["data"]["id"]

        resp = await client.get(f"/api/competitors/{comp_id}")
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "DetailComp"

    @pytest.mark.asyncio
    async def test_get_competitor_not_found(self, client):
        """测试获取不存在的竞品"""
        resp = await client.get("/api/competitors/nonexistent")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_competitor(self, client):
        """测试更新竞品"""
        create_resp = await client.post("/api/competitors", json={"name": "OldName"})
        comp_id = create_resp.json()["data"]["id"]

        resp = await client.put(f"/api/competitors/{comp_id}", json={"name": "NewName"})
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "NewName"

    @pytest.mark.asyncio
    async def test_delete_competitor(self, client):
        """测试删除竞品"""
        create_resp = await client.post("/api/competitors", json={"name": "ToDelete"})
        comp_id = create_resp.json()["data"]["id"]

        resp = await client.delete(f"/api/competitors/{comp_id}")
        assert resp.status_code == 200

        resp = await client.get(f"/api/competitors/{comp_id}")
        assert resp.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
