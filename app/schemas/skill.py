"""Skill 元数据与规范定义。"""

from __future__ import annotations

from pydantic import BaseModel, Field


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
    """Skill 结构定义。"""

    metadata: SkillMetadata
    body_markdown: str = Field(description="Skill.md 正文内容")
    resources: list[SkillResource] = Field(default_factory=list, description="资源清单")
