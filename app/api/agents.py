"""Orchestration Agents CRUD API。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import get_db
from app.models.orchestration import GpostAgent, GpostAgentSkillLink, GpostLLM
from app.models.skill import SkillOrchestration, SkillToolLink
from app.models.tool import ToolOrchestration
from app.schemas.orchestration import Agent, AgentCreate
from app.schemas.skill import Skill
from app.schemas.tool import Tool

router = APIRouter(prefix="/agents", tags=["Orchestration-Agents"])


async def _skill_to_response(
    session: AsyncSession,
    db_skill: SkillOrchestration,
) -> Skill:
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


async def _agent_to_response(
    session: AsyncSession,
    db_agent: GpostAgent,
) -> Agent:
    """将 GpostAgent 转为 Agent 响应，含关联的 skills 与 model。"""
    skill_links = await session.exec(
        select(GpostAgentSkillLink).where(GpostAgentSkillLink.agent_id == db_agent.id)
    )
    skill_ids = [lnk.skill_id for lnk in skill_links.all()]
    skills: list[Skill] = []
    if skill_ids:
        result = await session.exec(
            select(SkillOrchestration).where(SkillOrchestration.id.in_(skill_ids))
        )
        for db_skill in result.all():
            skills.append(await _skill_to_response(session, db_skill))

    model = None
    if db_agent.model_id:
        model = await session.get(GpostLLM, db_agent.model_id)

    return Agent(
        id=db_agent.id,
        created_at=db_agent.created_at,
        name=db_agent.name,
        role=db_agent.role,
        avatar=db_agent.avatar,
        description=db_agent.description,
        model_id=db_agent.model_id,
        model_provider=db_agent.model_provider,
        model_name=db_agent.model_name,
        temperature=db_agent.temperature,
        system_prompt=db_agent.system_prompt,
        skills=skills,
        model=model,
    )


@router.get("", response_model=list[Agent])
async def get_agents(session: AsyncSession = Depends(get_db)) -> list[Agent]:
    result = await session.exec(select(GpostAgent))
    agents = list(result.all())
    return [await _agent_to_response(session, a) for a in agents]


@router.post("", response_model=Agent)
async def create_agent(
    agent: AgentCreate,
    session: AsyncSession = Depends(get_db),
) -> Agent:
    data = agent.model_dump(exclude={"skill_ids"})
    db_agent = GpostAgent(**data)
    session.add(db_agent)
    await session.flush()

    if agent.skill_ids:
        for skill_id in agent.skill_ids:
            lnk = GpostAgentSkillLink(agent_id=db_agent.id, skill_id=skill_id)
            session.add(lnk)

    await session.commit()
    await session.refresh(db_agent)
    return await _agent_to_response(session, db_agent)


@router.get("/{agent_id}", response_model=Agent)
async def get_agent(
    agent_id: str,
    session: AsyncSession = Depends(get_db),
) -> Agent:
    result = await session.exec(select(GpostAgent).where(GpostAgent.id == agent_id))
    db_agent = result.first()
    if not db_agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return await _agent_to_response(session, db_agent)


@router.put("/{agent_id}", response_model=Agent)
async def update_agent(
    agent_id: str,
    agent_update: AgentCreate,
    session: AsyncSession = Depends(get_db),
) -> Agent:
    result = await session.exec(select(GpostAgent).where(GpostAgent.id == agent_id))
    db_agent = result.first()
    if not db_agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    data = agent_update.model_dump(exclude={"skill_ids"})
    for key, value in data.items():
        setattr(db_agent, key, value)

    if agent_update.skill_ids is not None:
        result = await session.exec(
            select(GpostAgentSkillLink).where(GpostAgentSkillLink.agent_id == agent_id)
        )
        for lnk in result.all():
            session.delete(lnk)
        for skill_id in agent_update.skill_ids:
            session.add(GpostAgentSkillLink(agent_id=agent_id, skill_id=skill_id))

    session.add(db_agent)
    await session.commit()
    await session.refresh(db_agent)
    return await _agent_to_response(session, db_agent)


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: str,
    session: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    result = await session.exec(select(GpostAgent).where(GpostAgent.id == agent_id))
    db_agent = result.first()
    if not db_agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    session.delete(db_agent)
    await session.commit()
    return {"ok": True}
