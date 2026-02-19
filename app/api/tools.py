"""Orchestration Tools CRUD API。"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import get_db
from app.models.tool import ToolOrchestration
from app.schemas.tool import Tool, ToolCreate

router = APIRouter(prefix="/tools", tags=["Orchestration-Tools"])


@router.get("", response_model=list[Tool])
async def get_tools(session: AsyncSession = Depends(get_db)) -> list[ToolOrchestration]:
    result = await session.exec(select(ToolOrchestration))
    return list(result.all())


@router.post("", response_model=Tool)
async def create_tool(
    tool: ToolCreate,
    session: AsyncSession = Depends(get_db),
) -> ToolOrchestration:
    data = tool.model_dump(by_alias=False)
    if data.get("schema") is not None:
        data["schema"] = json.dumps(data["schema"])
    if data.get("credential_config") is not None:
        data["credential_config"] = json.dumps(data["credential_config"])

    db_tool = ToolOrchestration(**data)
    session.add(db_tool)
    await session.commit()
    await session.refresh(db_tool)
    return db_tool


@router.put("/{tool_id}", response_model=Tool)
async def update_tool(
    tool_id: str,
    tool: ToolCreate,
    session: AsyncSession = Depends(get_db),
) -> ToolOrchestration:
    result = await session.exec(select(ToolOrchestration).where(ToolOrchestration.id == tool_id))
    db_tool = result.first()
    if not db_tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    data = tool.model_dump(by_alias=False)
    if data.get("schema") is not None:
        data["schema"] = json.dumps(data["schema"])
    if data.get("credential_config") is not None:
        data["credential_config"] = json.dumps(data["credential_config"])

    for key, value in data.items():
        setattr(db_tool, key, value)

    await session.add(db_tool)
    await session.commit()
    await session.refresh(db_tool)
    return db_tool


@router.delete("/{tool_id}")
async def delete_tool(
    tool_id: str,
    session: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    result = await session.exec(select(ToolOrchestration).where(ToolOrchestration.id == tool_id))
    db_tool = result.first()
    if not db_tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    await session.delete(db_tool)
    await session.commit()
    return {"ok": True}
