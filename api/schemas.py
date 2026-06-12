"""
API Schema
==========

定义 API 请求/响应的 Pydantic 模型。
复用 models/ 中已有模型，添加 API 专用的包装模型。
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


# ==================== 通用响应 ====================

class ApiResponse(BaseModel):
    """统一 API 响应格式"""
    code: int = 200
    data: Any = None
    message: str = "success"


class PaginatedResponse(BaseModel):
    """分页响应"""
    code: int = 200
    data: List[Any] = []
    total: int = 0
    page: int = 1
    page_size: int = 20
    message: str = "success"


# ==================== 竞品 ====================

class CompetitorCreateRequest(BaseModel):
    """创建竞品请求"""
    name: str
    website: Optional[str] = None
    industry: Optional[str] = None
    tags: List[str] = []
    notes: Optional[str] = None


class CompetitorUpdateRequest(BaseModel):
    """更新竞品请求"""
    name: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None


class CompetitorResponse(BaseModel):
    """竞品响应"""
    id: str
    name: str
    website: Optional[str] = None
    industry: Optional[str] = None
    tags: List[str] = []
    notes: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# ==================== 分析任务 ====================

class AnalysisSubmitRequest(BaseModel):
    """提交分析任务请求"""
    competitors: List[str]
    analysis_type: str = "standard"
    dimensions: List[str] = ["features", "pricing", "swot"]
    my_product: Optional[str] = None


class AnalysisSubmitResponse(BaseModel):
    """分析任务提交响应"""
    task_id: str
    status: str
    message: str


class AnalysisTaskResponse(BaseModel):
    """分析任务详情响应"""
    id: str
    competitors: List[str]
    analysis_type: str
    dimensions: List[str]
    my_product: Optional[str] = None
    status: str
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


# ==================== 报告 ====================

class ReportResponse(BaseModel):
    """报告响应"""
    id: str
    analysis_id: str
    title: str
    report_type: str
    format: str
    content: str
    file_path: Optional[str] = None
    created_at: Optional[str] = None


# ==================== 智能问答 ====================

class QARequest(BaseModel):
    """问答请求"""
    question: str = Field(..., min_length=1, description="问题内容，不能为空")
    competitors: Optional[List[str]] = None


class QAResponse(BaseModel):
    """问答响应"""
    answer: str
    sources: List[str] = []
