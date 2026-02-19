"""Orchestration Chat API。"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import get_db
from app.models.orchestration import GpostMessage, GpostSessionAgent
from app.schemas.orchestration import ChatRequest, ChatStopRequest

router = APIRouter(prefix="/chat", tags=["Orchestration-Chat"])


@router.post("/send")
async def send_message(
    request: ChatRequest,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """保存用户消息，并模拟 Orchestrator 生成响应。"""
    # 1. 保存用户消息
    user_msg = GpostMessage(
        session_id=request.session_id,
        role="user",
        content=request.message,
        msg_type="text",
    )
    session.add(user_msg)
    await session.commit()

    # Mock Orchestration Logic
    result = await session.exec(
        select(GpostSessionAgent).where(GpostSessionAgent.session_id == request.session_id)
    )
    session_agents = list(result.all())

    response_content = "I am a simple echo. Configure agents to get real responses."
    agent_id = None
    thought_process = []

    if session_agents:
        active_agent = session_agents[0]
        agent_id = active_agent.original_agent_id or ""
        thought_process = [
            {"step": "plan", "text": f"User asked: '{request.message}'. I should respond."},
            {"step": "retrieve", "text": "Checking memory context..."},
            {"step": "generate", "text": "Drafting response..."},
        ]
        response_content = f" [Simulated Response from Agent] I received: {request.message}"

    # 2. 保存 Assistant 响应
    bot_msg = GpostMessage(
        session_id=request.session_id,
        role="assistant",
        agent_id=agent_id or None,
        content=response_content,
        thought_process=json.dumps(thought_process),
        msg_type="text",
    )
    session.add(bot_msg)
    await session.commit()
    await session.refresh(bot_msg)

    return {"status": "success", "new_message_id": bot_msg.id}


@router.post("/stop")
async def stop_chat(request: ChatStopRequest) -> dict:
    """发送停止信号给 orchestrator。"""
    return {"status": "stopped", "detail": "Signal sent to orchestrator."}
