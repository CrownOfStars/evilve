"""Agent 服务测试。"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.agent import AgentRecord
from app.schemas.agent import AgentProfile, AgentStatus
from app.models.llm_meta import LLMModel
from app.schemas.skill import SkillMetadata, SkillSchema
from app.services.agent_service import create_agent, get_agent, list_agents, update_agent_status


@pytest.mark.asyncio
async def test_agent_crud_flow() -> None:
    """创建、读取与更新 Agent 状态。"""

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    profile = AgentProfile(
        agent_id="agent_1",
        name="TestAgent",
        role="tester",
        system_prompt="You are a test agent.",
        tools=["bash"],
        skills=[
            SkillSchema(
                metadata=SkillMetadata(
                    name="topology",
                    description="Topology utilities",
                ),
                body_markdown="Skill body",
            )
        ],
        handsoff=["agent_2"],
        model=LLMModel(
            model_id="gpt-4o-mini",
            provider="openai",
            display_name="GPT-4o mini",
        ),
        status=AgentStatus.TESTING,
    )

    async with async_session() as session:
        created = await create_agent(session, profile)
        assert created.agent_id == profile.agent_id
        assert created.model is not None
        assert created.model.provider == "openai"

        fetched = await get_agent(session, profile.agent_id)
        assert fetched.name == "TestAgent"

        updated = await update_agent_status(session, profile.agent_id, AgentStatus.ARCHIVED.value)
        assert updated.status == AgentStatus.ARCHIVED

        agents = await list_agents(session, status=AgentStatus.ARCHIVED.value)
        assert len(agents) == 1
        assert agents[0].agent_id == profile.agent_id
