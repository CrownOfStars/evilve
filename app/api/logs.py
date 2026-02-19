"""Orchestration Logs API。"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/logs", tags=["Orchestration-Logs"])


@router.get("/{trace_id}")
async def get_trace_logs(trace_id: str) -> dict:
    """获取 trace 日志（Mock）。"""
    return {
        "trace_id": trace_id,
        "steps": [
            {"timestamp": "2023-10-27T10:00:00Z", "actor": "Router", "action": "Selected Agent A"},
            {"timestamp": "2023-10-27T10:00:01Z", "actor": "Agent A", "input": "Hello", "output": "Hi there"},
        ],
    }
