"""Skill 元数据与规范定义。

含 SkillMetadata/SkillResource/SkillSchema（技能文件结构）与 SkillBase/SkillCreate/Skill（编排 CRUD API）。
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from app.schemas.tool import Tool


class SkillMetadata(BaseModel):
    """Skill 必填/可选元数据。"""

    name: str = Field(description="Skill 名称")
    description: str = Field(description="Skill 描述")
    version: str | None = Field(default=None, description="Skill 版本")
    dependencies: list[str] = Field(
        default_factory=list,
        description="依赖列表（可选）",
    )


class SkillResource(BaseModel):
    """Skill 附加资源。"""

    path: str = Field(description="资源路径")
    description: str | None = Field(default=None, description="资源说明")


class SkillSchema(BaseModel):
    """Skill 结构定义（技能文件）。"""

    metadata: SkillMetadata
    body_markdown: str = Field(description="Skill.md 正文内容")
    resources: list[SkillResource] = Field(default_factory=list, description="资源清单")


# --- 编排 CRUD API ---


class SkillBase(BaseModel):
    """Skill 基础字段（编排 API）。"""

    name: str
    description: str | None = None
    prompt: str | None = None
    code: str | None = None


class SkillCreate(SkillBase):
    """创建 Skill 请求。"""

    tool_ids: list[str] = Field(default_factory=list)


class Skill(SkillBase):
    """Skill 响应模型（编排 API）。"""

    id: str
    created_at: datetime
    tools: list["Tool"] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# 解决 tools: list[Tool] 前向引用
from app.schemas.tool import Tool

Skill.model_rebuild()
