"""健康检查服务。"""

from __future__ import annotations

from app.schemas.health import HealthStatus


async def get_health_status() -> HealthStatus:
    """返回基础健康状态。"""

    return HealthStatus()
