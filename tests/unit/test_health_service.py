"""健康检查服务测试。"""

from __future__ import annotations

import pytest

from app.schemas.health import HealthStatus
from app.services.health_service import get_health_status


@pytest.mark.asyncio
async def test_get_health_status_returns_ok() -> None:
    """服务应返回 ok 状态与时间戳。"""

    result = await get_health_status()

    assert isinstance(result, HealthStatus)
    assert result.status == "ok"
    assert result.timestamp is not None
