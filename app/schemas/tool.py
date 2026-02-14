"""工具元数据与规范定义。"""

from __future__ import annotations

from pydantic import BaseModel, Field


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
