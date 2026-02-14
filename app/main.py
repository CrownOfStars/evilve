"""FastAPI 应用入口。

保持与业务逻辑解耦，便于未来替换或扩展 HTTP 层。
"""

from __future__ import annotations

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    """应用工厂，便于测试与多实例部署。"""

    settings = get_settings()
    configure_logging()

    app = FastAPI(title=settings.app_name)
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
