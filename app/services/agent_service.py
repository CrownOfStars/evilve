"""Agent 数据读写服务。"""

from __future__ import annotations

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.agent import AgentRecord
from app.schemas.agent import AgentProfile


def _profile_to_record(profile: AgentProfile) -> AgentRecord:
    """将 AgentProfile 转为数据库记录。"""

    return AgentRecord(
        agent_id=profile.agent_id,
        name=profile.name,
        role=profile.role,
        system_prompt=profile.system_prompt,
        tools=profile.tools,
        skills=[skill.model_dump() for skill in profile.skills],
        handsoff=profile.handsoff,
        model=profile.model.model_dump() if profile.model else None,
        status=profile.status.value,
    )


def _record_to_profile(record: AgentRecord) -> AgentProfile:
    """将数据库记录转为 AgentProfile。"""

    payload = record.model_dump()
    model_data = payload.pop("model", None)
    skill_data = payload.pop("skills", [])
    return AgentProfile(
        **payload,
        skills=skill_data,
        model=model_data,
    )


async def create_agent(session: AsyncSession, profile: AgentProfile) -> AgentProfile:
    """创建 Agent 记录。"""

    record = _profile_to_record(profile)
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return _record_to_profile(record)


async def get_agent(session: AsyncSession, agent_id: str) -> AgentProfile:
    """获取单个 Agent。"""

    record = await session.get(AgentRecord, agent_id)
    if not record:
        raise NotFoundError(f"Agent not found: {agent_id}")
    return _record_to_profile(record)


async def list_agents(session: AsyncSession, status: str | None = None) -> list[AgentProfile]:
    """列出 Agent。"""

    stmt = select(AgentRecord)
    if status:
        stmt = stmt.where(AgentRecord.status == status)
    result = await session.exec(stmt)
    records = result.all()
    return [_record_to_profile(record) for record in records]


async def update_agent_status(
    session: AsyncSession,
    agent_id: str,
    status: str,
) -> AgentProfile:
    """更新 Agent 状态。"""

    record = await session.get(AgentRecord, agent_id)
    if not record:
        raise NotFoundError(f"Agent not found: {agent_id}")
    record.status = status
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return _record_to_profile(record)


async def update_agent_profile(session: AsyncSession, profile: AgentProfile) -> AgentProfile:
    """更新 Agent 全量配置。"""

    record = await session.get(AgentRecord, profile.agent_id)
    if not record:
        raise NotFoundError(f"Agent not found: {profile.agent_id}")

    record.name = profile.name
    record.role = profile.role
    record.system_prompt = profile.system_prompt
    record.tools = profile.tools
    record.skills = [skill.model_dump() for skill in profile.skills]
    record.handsoff = profile.handsoff
    record.model = profile.model.model_dump() if profile.model else None
    record.status = profile.status.value

    session.add(record)
    await session.commit()
    await session.refresh(record)
    return _record_to_profile(record)
