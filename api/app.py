"""
FastAPI 应用入口
================

创建和配置 FastAPI 应用实例。
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from api.database import init_db
from api.routers import register_routers
from api.auth import verify_token
from utils.logger import setup_logger

# 初始化日志根记录器（所有模块的日志都会写入 logs/app.log）
root_logger = setup_logger("", level=getattr(logging, settings.log_level))
root_logger.info("日志系统初始化完成")

logger = logging.getLogger(__name__)


class ProgressManager:
    """WebSocket 进度推送管理器"""

    def __init__(self):
        # task_id -> list of WebSocket connections
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, task_id: str, ws: WebSocket):
        await ws.accept()
        if task_id not in self._connections:
            self._connections[task_id] = []
        self._connections[task_id].append(ws)

    def disconnect(self, task_id: str, ws: WebSocket):
        if task_id in self._connections:
            self._connections[task_id].remove(ws)
            if not self._connections[task_id]:
                del self._connections[task_id]

    async def send_progress(self, task_id: str, node: str, progress: int, message: str):
        if task_id not in self._connections:
            return
        data = json.dumps({"node": node, "progress": progress, "message": message})
        disconnected = []
        for ws in self._connections[task_id]:
            try:
                await ws.send_text(data)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.disconnect(task_id, ws)


progress_manager = ProgressManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("正在初始化数据库...")
    await init_db()
    logger.info("数据库初始化完成")
    yield
    logger.info("应用关闭")


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例"""
    app = FastAPI(
        title="智能竞品分析 Agent API",
        description="基于 LLM 的自动化竞品分析系统后端接口",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS 中间件（前后端分离需要）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins.split(",") if settings.cors_origins else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    register_routers(app)

    # WebSocket 进度推送（需 token 认证）
    @app.websocket("/ws/analysis/{task_id}")
    async def ws_analysis_progress(websocket: WebSocket, task_id: str):
        token = websocket.query_params.get("token", "")
        if not token:
            await websocket.close(code=4001, reason="缺少 token")
            return

        user_id = verify_token(token)
        if user_id is None:
            await websocket.close(code=4001, reason="无效或过期 token")
            return

        # 验证 task 属于该用户
        from api.database import AnalysisTaskORM, async_session
        from sqlalchemy import select
        async with async_session() as session:
            result = await session.execute(
                select(AnalysisTaskORM).where(
                    AnalysisTaskORM.id == task_id,
                    AnalysisTaskORM.user_id == user_id,
                )
            )
            task = result.scalar_one_or_none()
            if not task:
                await websocket.close(code=4003, reason="任务不存在或无权限")
                return

        await progress_manager.connect(task_id, websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            progress_manager.disconnect(task_id, websocket)

    # 健康检查
    @app.get("/health")
    async def health():
        return {"status": "ok"}

    # 根路径
    @app.get("/")
    async def root():
        return {"message": "智能竞品分析 Agent API", "version": "0.1.0"}

    # 全局异常处理
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"未处理的异常: {exc}", exc_info=True)
        error_msg = str(exc)
        # 确保错误消息不含非 latin-1 字符，避免 ASGI 编码错误
        try:
            error_msg.encode('latin-1')
        except (UnicodeEncodeError, UnicodeDecodeError):
            error_msg = error_msg.encode('utf-8', errors='replace').decode('latin-1', errors='replace')
        return JSONResponse(
            status_code=500,
            content={"code": 500, "data": None, "message": f"服务器内部错误: {error_msg}"},
        )

    return app


# 应用实例（uvicorn 入口）
app = create_app()
