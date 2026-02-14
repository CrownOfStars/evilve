"""人工接管请求模型。"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class HandoffStatus(str):
    """人工接管状态枚举。"""

    OPEN = "open"
    RESOLVED = "resolved"


class HandoffRequestCreate(BaseModel):
    """创建人工接管请求。"""

    agent_id: str = Field(description="触发接管的 agent_id")
    message: str = Field(description="需要人工处理的消息")
    context: dict[str, str] | None = Field(default=None, description="可选上下文信息")


class HandoffRequest(BaseModel):
    """人工接管请求记录。"""

    request_id: str = Field(description="请求唯一标识")
    agent_id: str
    message: str
    context: dict[str, str] | None = None
    status: str = Field(default=HandoffStatus.OPEN, description="处理状态")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: datetime | None = None
    human_response: str | None = None


class HandoffResolve(BaseModel):
    """人工接管处理结果。"""

    response: str = Field(description="人工处理的回复内容")
