"""Orchestration Sessions CRUD 与 Graph API。"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import get_db
from app.models.orchestration import GpostMessage, GpostSession, GpostSessionAgent
from app.schemas.orchestration import (
    Message,
    Session,
    SessionAgent,
    SessionAgentCreate,
    SessionBase,
    SessionCreate,
    SessionDetail,
)

router = APIRouter(prefix="/sessions", tags=["Orchestration-Sessions"])


@router.get("", response_model=list[Session])
async def get_sessions(session: AsyncSession = Depends(get_db)) -> list[GpostSession]:
    result = await session.exec(select(GpostSession))
    return list(result.all())


@router.post("", response_model=Session)
async def create_session(
    session_in: SessionCreate,
    session: AsyncSession = Depends(get_db),
) -> GpostSession:
    db_session = GpostSession(**session_in.model_dump())
    session.add(db_session)
    await session.commit()
    await session.refresh(db_session)
    return db_session


@router.get("/{session_id}", response_model=SessionDetail)
async def get_session_detail(
    session_id: str,
    session: AsyncSession = Depends(get_db),
) -> SessionDetail:
    result = await session.exec(select(GpostSession).where(GpostSession.id == session_id))
    db_session = result.first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = list(
        (await session.exec(select(GpostMessage).where(GpostMessage.session_id == session_id))).all()
    )
    session_agents = list(
        (
            await session.exec(
                select(GpostSessionAgent).where(GpostSessionAgent.session_id == session_id)
            )
        ).all()
    )

    return SessionDetail(
        id=db_session.id,
        created_at=db_session.created_at,
        updated_at=db_session.updated_at,
        title=db_session.title,
        user_id=db_session.user_id,
        status=db_session.status,
        graph_config=db_session.graph_config,
        messages=[Message.model_validate(m) for m in messages],
        session_agents=[SessionAgent.model_validate(sa) for sa in session_agents],
    )


@router.patch("/{session_id}", response_model=Session)
async def update_session(
    session_id: str,
    session_in: SessionBase,
    session: AsyncSession = Depends(get_db),
) -> GpostSession:
    result = await session.exec(select(GpostSession).where(GpostSession.id == session_id))
    db_session = result.first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session_in.title is not None:
        db_session.title = session_in.title
    if session_in.user_id is not None:
        db_session.user_id = session_in.user_id
    if session_in.status is not None:
        db_session.status = session_in.status
    if session_in.graph_config is not None:
        db_session.graph_config = (
            json.dumps(session_in.graph_config)
            if isinstance(session_in.graph_config, dict)
            else session_in.graph_config
        )

    await session.add(db_session)
    await session.commit()
    await session.refresh(db_session)
    return db_session


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    session: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    result = await session.exec(select(GpostSession).where(GpostSession.id == session_id))
    db_session = result.first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    await session.delete(db_session)
    await session.commit()
    return {"ok": True}


# --- Session Agents ---

@router.get("/{session_id}/agents", response_model=list[SessionAgent])
async def get_session_agents(
    session_id: str,
    session: AsyncSession = Depends(get_db),
) -> list[GpostSessionAgent]:
    result = await session.exec(
        select(GpostSessionAgent).where(GpostSessionAgent.session_id == session_id)
    )
    return list(result.all())


@router.post("/{session_id}/agents", response_model=SessionAgent)
async def add_agent_to_session(
    session_id: str,
    agent_data: SessionAgentCreate,
    session: AsyncSession = Depends(get_db),
) -> GpostSessionAgent:
    result = await session.exec(select(GpostSession).where(GpostSession.id == session_id))
    if not result.first():
        raise HTTPException(status_code=404, detail="Session not found")

    db_session_agent = GpostSessionAgent(
        session_id=session_id,
        original_agent_id=agent_data.original_agent_id,
        override_system_prompt=agent_data.override_system_prompt,
        override_model=agent_data.override_model,
    )
    session.add(db_session_agent)
    await session.commit()
    await session.refresh(db_session_agent)
    return db_session_agent


# --- Graph ---

@router.get("/{session_id}/graph")
async def get_session_graph(
    session_id: str,
    session: AsyncSession = Depends(get_db),
) -> dict:
    result = await session.exec(select(GpostSession).where(GpostSession.id == session_id))
    db_session = result.first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")

    if db_session.graph_config:
        return json.loads(db_session.graph_config)
    return {"nodes": [], "edges": []}


@router.put("/{session_id}/graph")
async def update_session_graph(
    session_id: str,
    graph: dict,
    session: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    result = await session.exec(select(GpostSession).where(GpostSession.id == session_id))
    db_session = result.first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")

    db_session.graph_config = json.dumps(graph)
    await session.add(db_session)
    await session.commit()
    return {"ok": True}
