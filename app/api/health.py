"""健康检查路由。"""

from __future__ import annotations

from fastapi import APIRouter

from app.schemas.health import HealthStatus
from app.services.health_service import get_health_status

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthStatus)
async def health_check() -> HealthStatus:
    """对外暴露基础健康检查接口。"""

    return await get_health_status()
