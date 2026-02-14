"""运行时相关工具工厂（基于闭包绑定 runtime 上下文）。

这些工具通过闭包捕获 GroupChat 实例、sender_id 和 handsoff 列表，
在 Agent 调用时自动操作正确的运行时上下文。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from agents import function_tool
from agents.tool import Tool

from app.runtime.human import HumanParticipant

if TYPE_CHECKING:
    from app.runtime.groupchat import GroupChat


def make_send_message_tool(
    runtime: "GroupChat",
    sender_id: str,
    handsoff: list[str],
) -> Tool:
    """创建绑定了 runtime、sender_id 和 handsoff 的 send_message 工具。

    Args:
        runtime: GroupChat 运行时实例。
        sender_id: 发送者 Agent 标识。
        handsoff: 允许通信的参与者 ID 列表。
    """

    # 构建允许目标描述，注入到工具 docstring 让 LLM 知道
    allowed_targets = ", ".join(handsoff) if handsoff else "(none)"

    @function_tool
    def send_message(to: str, content: str) -> str:
        f"""Send a message to another participant. Allowed targets: {allowed_targets}.

        IMPORTANT: Your direct text output will NOT be sent to anyone.
        You MUST use this tool to communicate with other participants.
        Only send to participants in your allowed list.

        Args:
            to: Target participant id. Must be one of: {allowed_targets}.
            content: Message content to send.
        """
        # handsoff 校验
        if handsoff and to not in handsoff:
            return (
                f"REJECTED: You are not allowed to send messages to '{to}'. "
                f"Allowed targets: {allowed_targets}"
            )

        if to not in runtime.participants:
            return f"REJECTED: Participant '{to}' does not exist in this runtime."

        print(f"🔧 [send_message] {sender_id} -> {to}: {content}")
        runtime.message_queue.append((sender_id, content, to))
        return f"[HANDOFF] Message delivered: {sender_id} -> {to}"

    return send_message


def make_create_agent_tool(runtime: "GroupChat") -> Tool:
    """创建绑定了 runtime 的 create_agent 工具。"""

    @function_tool
    def create_agent(role: str, guidance: str = "") -> str:
        """Create a new sub-agent with the given role and system prompt."""

        agent_id = runtime.create_agent(role=role, system_prompt=guidance)
        return f"Agent created: {agent_id}"

    return create_agent


def make_list_agents_tool(runtime: "GroupChat") -> Tool:
    """创建绑定了 runtime 的 list_participants 工具。"""

    @function_tool
    def list_participants() -> str:
        """List all participants (agents and humans) in the current runtime."""

        info_parts: list[str] = []
        for name, participant in runtime.participants.items():
            if isinstance(participant, HumanParticipant):
                info_parts.append(f"{name} (type=human)")
            else:
                role = getattr(participant, "role", "unknown")
                info_parts.append(f"{name} (type=agent, role={role})")
        return ", ".join(info_parts) if info_parts else "No participants"

    return list_participants
