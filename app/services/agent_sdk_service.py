"""OpenAI Agents SDK 的 Agent 管理服务。"""

from __future__ import annotations

from agents import Agent as SdkAgent, RunConfig
from agents.tool import Tool
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.model_provider import get_run_config
from app.schemas.agent import AgentProfile
from app.services.agent_service import create_agent, get_agent, update_agent_profile
from app.tools.registry import ToolRegistry


def _resolve_tools(tool_ids: list[str]) -> list[Tool]:
    """根据 tool_id 列表解析工具函数。

    注意：runtime.* 命名空间的工具需要运行时上下文，
    此处跳过，应通过 GroupChat.create_agent_from_profile 注入。
    """

    resolved: list[Tool] = []
    for tool_id in tool_ids:
        if tool_id.startswith("runtime."):
            continue
        try:
            resolved.append(ToolRegistry.get_callable(tool_id))
        except KeyError as exc:
            raise NotFoundError(f"Tool not found: {tool_id}") from exc
    return resolved


def create_sdk_agent(
    profile: AgentProfile,
    run_config: RunConfig | None = None,
) -> SdkAgent:
    """基于 AgentProfile 构建 SDK Agent。"""

    tools = _resolve_tools(profile.tools)
    model = profile.model.model_id if profile.model else None
    return SdkAgent(
        name=profile.name,
        instructions=profile.system_prompt,
        tools=tools,
        model=model,
    )


async def create_agent_with_sdk(
    session: AsyncSession,
    profile: AgentProfile,
) -> SdkAgent:
    """创建 Agent 记录并返回 SDK Agent。"""

    saved = await create_agent(session, profile)
    return create_sdk_agent(saved)


async def load_agent_with_sdk(
    session: AsyncSession,
    agent_id: str,
) -> SdkAgent:
    """加载 Agent 记录并返回 SDK Agent。"""

    profile = await get_agent(session, agent_id)
    return create_sdk_agent(profile)


async def update_agent_with_sdk(
    session: AsyncSession,
    profile: AgentProfile,
) -> SdkAgent:
    """更新 Agent 记录并返回 SDK Agent。"""

    saved = await update_agent_profile(session, profile)
    return create_sdk_agent(saved)
