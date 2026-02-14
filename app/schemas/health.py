"""健康检查响应模型。"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class HealthStatus(BaseModel):
    """对外健康状态。"""

    status: str = Field(default="ok", description="服务状态")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC 时间戳",
    )
