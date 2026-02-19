"""Orchestration Providers 与 LLMs API。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from openai import OpenAI

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import get_db
from app.models.orchestration import GpostLLM, GpostProvider
from app.schemas.orchestration import LLM, Provider, ProviderCreate

router = APIRouter(prefix="/providers", tags=["Orchestration-Providers"])


def _fetch_llms_from_provider(db_provider: GpostProvider) -> list[dict]:
    """从远程 Provider API 获取 LLM 列表。"""
    client = OpenAI(
        api_key=db_provider.api_key or "",
        base_url=db_provider.base_url or "",
    )
    llm_models = []
    remote_models = client.models.list()
    for model in remote_models:
        model_id = model.id
        try:
            client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": "say 1"}],
                max_tokens=1,
                timeout=5,
            )
            llm_models.append({"remote_id": model_id, "is_llm": True})
        except Exception:
            continue
    return llm_models


@router.get("", response_model=list[Provider])
async def get_providers(session: AsyncSession = Depends(get_db)) -> list[GpostProvider]:
    result = await session.exec(select(GpostProvider))
    return list(result.all())


@router.post("", response_model=Provider)
async def create_provider(
    provider: ProviderCreate,
    session: AsyncSession = Depends(get_db),
) -> GpostProvider:
    db_provider = GpostProvider(**provider.model_dump())
    session.add(db_provider)
    await session.commit()
    await session.refresh(db_provider)
    return db_provider


@router.put("/{provider_id}", response_model=Provider)
async def update_provider(
    provider_id: str,
    provider: ProviderCreate,
    session: AsyncSession = Depends(get_db),
) -> GpostProvider:
    result = await session.exec(select(GpostProvider).where(GpostProvider.id == provider_id))
    db_provider = result.first()
    if not db_provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    for key, value in provider.model_dump().items():
        setattr(db_provider, key, value)

    session.add(db_provider)
    await session.commit()
    await session.refresh(db_provider)
    return db_provider


@router.delete("/{provider_id}")
async def delete_provider(
    provider_id: str,
    session: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    result = await session.exec(select(GpostProvider).where(GpostProvider.id == provider_id))
    db_provider = result.first()
    if not db_provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    session.delete(db_provider)
    await session.commit()
    return {"ok": True}


@router.get("/{provider_id}/models", response_model=list[LLM])
async def get_provider_models(
    provider_id: str,
    session: AsyncSession = Depends(get_db),
) -> list[GpostLLM]:
    result = await session.exec(select(GpostProvider).where(GpostProvider.id == provider_id))
    if not result.first():
        raise HTTPException(status_code=404, detail="Provider not found")

    result = await session.exec(select(GpostLLM).where(GpostLLM.provider_id == provider_id))
    return list(result.all())


@router.post("/{provider_id}/models/refresh")
async def refresh_provider_models(
    provider_id: str,
    session: AsyncSession = Depends(get_db),
) -> dict:
    result = await session.exec(select(GpostProvider).where(GpostProvider.id == provider_id))
    db_provider = result.first()
    if not db_provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    if not db_provider.api_key:
        raise HTTPException(status_code=400, detail="Provider has no API key configured")

    try:
        llm_list = _fetch_llms_from_provider(db_provider)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch models from provider: {str(e)}",
        )

    # 删除该 provider 下现有 LLMs，插入新的
    result = await session.exec(select(GpostLLM).where(GpostLLM.provider_id == provider_id))
    for llm in result.all():
        session.delete(llm)

    for item in llm_list:
        db_llm = GpostLLM(
            provider_id=provider_id,
            remote_id=item["remote_id"],
            is_llm=item.get("is_llm", True),
        )
        session.add(db_llm)

    await session.commit()

    result = await session.exec(select(GpostLLM).where(GpostLLM.provider_id == provider_id))
    models_list = list(result.all())
    return {
        "provider_id": provider_id,
        "total_count": len(llm_list),
        "models": [
            {"id": m.id, "remote_id": m.remote_id, "provider_id": m.provider_id}
            for m in models_list
        ],
    }
