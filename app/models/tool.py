"""工具数据库模型。

含 ToolRecord（技能注册表 tools）与 ToolOrchestration（编排 CRUD 表 gpost_tools）。
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel


def _uuid_str() -> str:
    return str(uuid.uuid4())


class ToolRecord(SQLModel, table=True):
    """工具持久化记录（技能注册表）。"""

    __tablename__ = "tools"

    tool_id: str = Field(primary_key=True)
    namespace: str
    name: str
    docstring: str
    version: str | None = None


class ToolOrchestration(SQLModel, table=True):
    """编排层工具记录（GPost Orchestration CRUD）。"""

    __tablename__ = "gpost_tools"

    id: str = Field(primary_key=True, default_factory=_uuid_str)
    name: str
    docstring: str | None = None  # 与 description 语义相同，后端 API 兼容
    schema: str | None = None  # JSON stored as string
    credential_config: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
