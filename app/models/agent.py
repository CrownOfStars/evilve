"""Agent 数据库模型。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


class AgentRecord(SQLModel, table=True):
    """Agent 持久化记录。"""

    __tablename__ = "agents"

    agent_id: str = Field(primary_key=True)
    name: str
    role: str
    system_prompt: str
    tools: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    skills: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    handsoff: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    model: dict | None = Field(default=None, sa_column=Column(JSON))
    status: str = Field(default="testing")
