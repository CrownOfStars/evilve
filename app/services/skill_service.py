"""Skill 加载服务。"""

from __future__ import annotations

import os
from typing import Any

import yaml

from app.schemas.skill import SkillMetadata, SkillResource, SkillSchema


def _parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """解析 Skill.md 的 YAML frontmatter 与正文。"""

    if not content.startswith("---"):
        raise ValueError("Skill.md missing YAML frontmatter")

    parts = content.split("---", 2)
    if len(parts) < 3:
        raise ValueError("Invalid YAML frontmatter format")

    metadata_raw = yaml.safe_load(parts[1]) or {}
    body_markdown = parts[2].lstrip("\n")
    return metadata_raw, body_markdown


def load_skill_from_file(file_path: str) -> SkillSchema:
    """从 Skill.md 文件加载 Skill。"""

    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()

    metadata_raw, body_markdown = _parse_frontmatter(content)
    metadata = SkillMetadata(**metadata_raw)
    return SkillSchema(metadata=metadata, body_markdown=body_markdown)


def load_skill_from_dir(skill_dir: str) -> SkillSchema:
    """从 Skill 目录加载 Skill，并收集资源清单。"""

    skill_md_path = os.path.join(skill_dir, "Skill.md")
    skill = load_skill_from_file(skill_md_path)

    resources: list[SkillResource] = []
    for root, _, files in os.walk(skill_dir):
        for filename in files:
            if filename == "Skill.md":
                continue
            relative_path = os.path.relpath(os.path.join(root, filename), skill_dir)
            resources.append(SkillResource(path=relative_path))

    return skill.model_copy(update={"resources": resources})
