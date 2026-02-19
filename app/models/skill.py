"""Skill 数据库模型。

含 SkillOrchestration（编排 CRUD 表 gpost_skills）及 SkillToolLink（多对多关联表）。
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel


def _uuid_str() -> str:
    return str(uuid.uuid4())


class SkillToolLink(SQLModel, table=True):
    """Skills <-> Tools 多对多关联表。"""

    __tablename__ = "gpost_skills_tools"

    skill_id: str = Field(foreign_key="gpost_skills.id", primary_key=True)
    tool_id: str = Field(foreign_key="gpost_tools.id", primary_key=True)
    config: str | None = None


class SkillOrchestration(SQLModel, table=True):
    """编排层 Skill 记录（GPost Orchestration CRUD）。"""

    __tablename__ = "gpost_skills"

    id: str = Field(primary_key=True, default_factory=_uuid_str)
    name: str
    description: str | None = None
    prompt: str | None = None
    code: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # tools/agents 通过 SkillToolLink、GpostAgentSkillLink 关联
