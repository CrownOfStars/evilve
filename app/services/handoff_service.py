"""人工接管服务。

提供两种工作模式：
1. 独立模式（内存存储）：通过 API 创建/解决接管请求
2. 运行时联动模式：与 GroupChat 中的 HumanParticipant 打通

当 GroupChat 中存在 HumanParticipant 时，接管请求自动来自
HumanParticipant.pending，解决请求时自动入队到 GroupChat。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import uuid4

from app.core.exceptions import NotFoundError
from app.schemas.handoff import HandoffRequest, HandoffRequestCreate, HandoffResolve, HandoffStatus

if TYPE_CHECKING:
    from app.runtime.groupchat import GroupChat

# ---------------------------------------------------------------------------
# 独立内存存储（无运行时时使用）
# ---------------------------------------------------------------------------

_HANDOFF_STORE: dict[str, HandoffRequest] = {}


async def create_handoff(payload: HandoffRequestCreate) -> HandoffRequest:
    """创建人工接管请求。"""

    request_id = f"handoff_{uuid4().hex[:8]}"
    record = HandoffRequest(
        request_id=request_id,
        agent_id=payload.agent_id,
        message=payload.message,
        context=payload.context,
        status=HandoffStatus.OPEN,
    )
    _HANDOFF_STORE[request_id] = record
    return record


async def list_handoffs(status: str | None = None) -> list[HandoffRequest]:
    """列出人工接管请求。"""

    requests = list(_HANDOFF_STORE.values())
    if status:
        requests = [item for item in requests if item.status == status]
    return requests


async def resolve_handoff(request_id: str, payload: HandoffResolve) -> HandoffRequest:
    """处理人工接管请求。"""

    record = _HANDOFF_STORE.get(request_id)
    if not record:
        raise NotFoundError(f"Handoff not found: {request_id}")
    record.status = HandoffStatus.RESOLVED
    record.human_response = payload.response
    record.resolved_at = datetime.now(timezone.utc)
    _HANDOFF_STORE[request_id] = record
    return record


# ---------------------------------------------------------------------------
# 运行时联动模式
# ---------------------------------------------------------------------------

async def resolve_handoff_in_runtime(
    runtime: "GroupChat",
    human_name: str,
    request_id: str,
    content: str,
) -> None:
    """在运行时中解决人工接管请求。

    将人类回复直接入队到 GroupChat 消息队列，
    实现 API → HumanParticipant → GroupChat 的完整闭环。

    Args:
        runtime: GroupChat 运行时实例。
        human_name: 人类参与者标识。
        request_id: 待处理请求 ID。
        content: 人类回复内容。
    """

    runtime.submit_human_reply(human_name, request_id, content)
