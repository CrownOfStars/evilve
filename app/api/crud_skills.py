"""Orchestration Skills CRUD API。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import get_db
from app.models.skill import SkillOrchestration, SkillToolLink
from app.models.tool import ToolOrchestration
from app.schemas.skill import Skill, SkillCreate
from app.schemas.tool import Tool

router = APIRouter(prefix="/skills", tags=["Orchestration-Skills"])


async def _skill_to_response(session: AsyncSession, db_skill: SkillOrchestration) -> Skill:
    """将 SkillOrchestration 转为 Skill，含 tools。"""
    result = await session.exec(
        select(SkillToolLink).where(SkillToolLink.skill_id == db_skill.id)
    )
    tool_ids = [lnk.tool_id for lnk in result.all()]
    tools: list[ToolOrchestration] = []
    if tool_ids:
        tools = list(
            (
                await session.exec(
                    select(ToolOrchestration).where(ToolOrchestration.id.in_(tool_ids))
                )
            ).all()
        )
    return Skill(
        id=db_skill.id,
        created_at=db_skill.created_at,
        name=db_skill.name,
        description=db_skill.description,
        prompt=db_skill.prompt,
        code=db_skill.code,
        tools=[Tool.model_validate(t) for t in tools],
    )


@router.get("", response_model=list[Skill])
async def get_skills(session: AsyncSession = Depends(get_db)) -> list[Skill]:
    result = await session.exec(select(SkillOrchestration))
    return [await _skill_to_response(session, s) for s in result.all()]


@router.post("", response_model=Skill)
async def create_skill(
    skill: SkillCreate,
    session: AsyncSession = Depends(get_db),
) -> Skill:
    data = skill.model_dump(exclude={"tool_ids"})
    db_skill = SkillOrchestration(**data)
    session.add(db_skill)
    await session.flush()

    if skill.tool_ids:
        for tool_id in skill.tool_ids:
            session.add(SkillToolLink(skill_id=db_skill.id, tool_id=tool_id))

    await session.commit()
    await session.refresh(db_skill)
    return await _skill_to_response(session, db_skill)


@router.put("/{skill_id}", response_model=Skill)
async def update_skill(
    skill_id: str,
    skill_update: SkillCreate,
    session: AsyncSession = Depends(get_db),
) -> Skill:
    result = await session.exec(select(SkillOrchestration).where(SkillOrchestration.id == skill_id))
    db_skill = result.first()
    if not db_skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    data = skill_update.model_dump(exclude={"tool_ids"})
    for key, value in data.items():
        setattr(db_skill, key, value)

    if skill_update.tool_ids is not None:
        result = await session.exec(
            select(SkillToolLink).where(SkillToolLink.skill_id == skill_id)
        )
        for lnk in result.all():
            session.delete(lnk)
        for tool_id in skill_update.tool_ids:
            session.add(SkillToolLink(skill_id=skill_id, tool_id=tool_id))

    session.add(db_skill)
    await session.commit()
    await session.refresh(db_skill)
    return await _skill_to_response(session, db_skill)
