"""Skill 加载服务。"""

from __future__ import annotations

import os
from typing import Any

import yaml

import logging
from pathlib import Path
from app.schemas.skill import SkillMetadata, SkillResource, SkillSchema


logger = logging.getLogger(__name__)

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




class SkillManager:
    def __init__(self, skill_dir: str = "skills"):
        self.skill_dir = Path(skill_dir)
        self._skills: dict[str, SkillSchema] = {}
        self.reload_skills()

    def reload_skills(self) -> None:
        """扫描目录并重新加载所有 Skills"""
        self._skills.clear()
        if not self.skill_dir.exists():
            logger.warning(f"Skill directory {self.skill_dir} does not exist.")
            return

        # 遍历 skills 目录下的子目录
        for item in self.skill_dir.iterdir():
            if item.is_dir():
                # 尝试加载 skills/<name>/Skill.md
                skill_file = item / "Skill.md"
                if skill_file.exists():
                    try:
                        # 复用你已有的 load_skill_from_dir 函数
                        skill = load_skill_from_dir(str(item))
                        self._skills[skill.metadata.name] = skill
                        logger.info(f"Loaded skill: {skill.metadata.name}")
                    except Exception as e:
                        logger.error(f"Failed to load skill from {item}: {e}")

    def get_skill(self, name: str) -> SkillSchema | None:
        """根据名称获取特定 Skill"""
        return self._skills.get(name)

    def list_skills(self) -> list[SkillSchema]:
        """获取所有 Skill"""
        return list(self._skills.values())

# 创建一个全局单例供 API 使用
# 假设 skills 目录在项目根目录下
skill_manager = SkillManager(skill_dir="skills")