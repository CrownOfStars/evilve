"""FastAPI 应用入口。

保持与业务逻辑解耦，便于未来替换或扩展 HTTP 层。
合并自 backend/main.py：CORS 中间件与 GPost Orchestration API。
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router, orchestration_router
from app.core.config import get_settings
from app.core.db import init_db
from app.core.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库。"""
    await init_db()
    yield


def create_app() -> FastAPI:
    """应用工厂，便于测试与多实例部署。"""

    settings = get_settings()
    configure_logging()

    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    app.include_router(orchestration_router, prefix="/api")
    return app


app = create_app()
