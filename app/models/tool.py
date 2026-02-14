"""工具数据库模型。"""

from __future__ import annotations

from sqlmodel import Field, SQLModel


class ToolRecord(SQLModel, table=True):
    """工具持久化记录。"""

    __tablename__ = "tools"

    tool_id: str = Field(primary_key=True)
    namespace: str
    name: str
    docstring: str
    version: str | None = None
