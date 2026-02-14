"""人工接管接口。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.exceptions import NotFoundError
from app.schemas.handoff import HandoffRequest, HandoffRequestCreate, HandoffResolve
from app.services.handoff_service import create_handoff, list_handoffs, resolve_handoff

router = APIRouter(tags=["handoff"])


@router.post("/handoff/requests", response_model=HandoffRequest)
async def create_handoff_request(payload: HandoffRequestCreate) -> HandoffRequest:
    """创建人工接管请求。"""

    return await create_handoff(payload)


@router.get("/handoff/requests", response_model=list[HandoffRequest])
async def list_handoff_requests(status: str | None = None) -> list[HandoffRequest]:
    """列出人工接管请求。"""

    return await list_handoffs(status=status)


@router.post("/handoff/requests/{request_id}/resolve", response_model=HandoffRequest)
async def resolve_handoff_request(
    request_id: str, payload: HandoffResolve
) -> HandoffRequest:
    """处理人工接管请求。"""

    try:
        return await resolve_handoff(request_id, payload)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
