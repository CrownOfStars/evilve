"""Orchestration LLMs API。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import get_db
from app.models.orchestration import GpostLLM
from app.schemas.orchestration import LLM

router = APIRouter(prefix="/llms", tags=["Orchestration-LLMs"])


@router.get("", response_model=list[LLM])
async def get_all_llms(
    provider_id: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
) -> list[GpostLLM]:
    """获取所有 LLM，可按 provider_id 过滤。"""
    stmt = select(GpostLLM)
    if provider_id:
        stmt = stmt.where(GpostLLM.provider_id == provider_id)
    result = await session.exec(stmt)
    return list(result.all())
