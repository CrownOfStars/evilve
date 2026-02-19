"""工具元数据与规范定义。

含 ToolSchema（技能注册）、ToolBase/ToolCreate/Tool（编排 CRUD API）。
docstring 与 description 语义相同，API 使用 description 以兼容后端。
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ToolSchema(BaseModel):
    """工具定义。

    说明：tools 必须包含 docstring 以便描述用途与调用方式。
    tool_id 使用 namespace.name 格式，如 math.add、runtime.send_message。
    """

    tool_id: str = Field(description="工具唯一标识，格式 namespace.name")
    namespace: str = Field(description="工具命名空间")
    name: str = Field(description="工具名称")
    docstring: str = Field(description="工具说明文档")
    version: str | None = Field(default=None, description="工具版本")


class ToolBase(BaseModel):
    """Tool 基础字段（编排 API）。docstring 与 description 语义相同。"""

    name: str
    docstring: str | None = Field(
        None,
        description="工具说明，与 description 语义相同",
        validation_alias="description",
        serialization_alias="description",
    )
    schema: dict[str, Any] | None = None
    credential_config: dict[str, Any] | None = None


class ToolCreate(ToolBase):
    """创建 Tool 请求。"""

    pass


class Tool(ToolBase):
    """Tool 响应模型（编排 API）。"""

    id: str
    created_at: datetime

    @field_validator("schema", mode="before")
    @classmethod
    def parse_schema(cls, v: str | dict | None) -> dict | None:
        if isinstance(v, str) and v:
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return None
        return v

    @field_validator("credential_config", mode="before")
    @classmethod
    def parse_credential_config(cls, v: str | dict | None) -> dict | None:
        if isinstance(v, str) and v:
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return None
        return v

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)