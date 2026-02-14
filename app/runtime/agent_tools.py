"""Agent 可用工具集。"""

from __future__ import annotations

import json
import os
import subprocess
import time
from typing import TYPE_CHECKING

from app.schemas.runtime import ToolResult

if TYPE_CHECKING:
    from app.runtime.groupchat import GroupChat


class AgentTools:
    """基于实例的工具集。

    每个 Agent 拥有一个实例，从而持有上下文（runtime + agent_id）。
    """

    def __init__(self, runtime: "GroupChat", agent_id: str):
        """初始化工具集实例。"""

        self.runtime = runtime
        self.agent_id = agent_id

    def create(self, role: str, guidance: str = "") -> ToolResult:
        """创建子 Agent。"""

        try:
            new_agent_id = self.runtime.create_agent(role=role, system_prompt=guidance)
            return ToolResult(output=json.dumps({"agentId": new_agent_id}))
        except Exception as exc:
            return ToolResult(output="", error=str(exc), success=False)

    def self(self) -> ToolResult:
        """返回当前 Agent 身份信息。"""

        return ToolResult(
            output=json.dumps(
                {
                    "agent_id": self.agent_id,
                    "workspace_id": "default",
                    "role": getattr(self.runtime.participants.get(self.agent_id), "role", "unknown"),
                }
            )
        )

    def list_agents(self) -> ToolResult:
        """列出当前运行时所有 Agent。"""

        agents_info = []
        for name, agent in self.runtime.participants.items():
            agents_info.append(
                {
                    "id": name,
                    "role": getattr(agent, "role", "assistant"),
                }
            )
        return ToolResult(output=json.dumps(agents_info, indent=2))

    def get_skill(self, skill_name: str) -> ToolResult:
        """读取指定技能文档内容。"""

        skill_paths = [f"skills/{skill_name}.md"]
        for path in skill_paths:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as file:
                        return ToolResult(output=file.read())
                except Exception as exc:
                    return ToolResult(output="", error=str(exc), success=False)
        return ToolResult(output="", error=f"Skill '{skill_name}' not found.", success=False)

    def send(self, to: str, content: str) -> ToolResult:
        """发送点对点消息。"""

        self.runtime.send_message(sender_name=self.agent_id, content=content, target=to)
        return ToolResult(output=f"Message sent to {to}")

    def list_groups(self) -> ToolResult:
        """列出群组。"""

        return ToolResult(output=json.dumps([{"id": "general", "name": "General Chat"}]))

    def list_group_members(self, groupId: str) -> ToolResult:
        """列出群组成员。"""

        if groupId == "general":
            agents = list(self.runtime.participants.keys())
            return ToolResult(output=json.dumps(agents))
        return ToolResult(output="[]")

    def create_group(self, memberIds: list[str], name: str = "") -> ToolResult:
        """创建群组。"""

        return ToolResult(
            output=json.dumps({"groupId": f"group_{int(time.time())}", "name": name})
        )

    def send_group_message(self, groupId: str, content: str, contentType: str = "text") -> ToolResult:
        """发送群组消息。"""

        if groupId == "general":
            self.runtime.broadcast_message(
                sender_name=self.agent_id,
                content=f"[Group {groupId}] {content}",
            )
            return ToolResult(output="Message broadcasted to general group")
        return ToolResult(output="Message sent (Mock)")

    def send_direct_message(self, toAgentId: str, content: str, contentType: str = "text") -> ToolResult:
        """发送私信。"""

        return self.send(to=toAgentId, content=content)

    def get_group_messages(self, groupId: str) -> ToolResult:
        """获取群组消息历史。"""

        history = [f"{m.sender}: {m.content}" for m in self.runtime.message_history]
        return ToolResult(output="\n".join(history))

    def bash(
        self,
        command: str,
        cwd: str | None = None,
        timeoutMs: int = 120000,
        maxOutputKB: int = 1024,
    ) -> ToolResult:
        """执行 shell 命令。"""

        work_dir = cwd if cwd else os.getcwd()
        try:
            timeout_sec = timeoutMs / 1000.0
            print(f"Executing (by {self.agent_id}): {command}")

            result = subprocess.run(
                command,
                shell=True,
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )

            output_json = {
                "stdout": result.stdout[: maxOutputKB * 1024],
                "stderr": result.stderr[: maxOutputKB * 1024],
                "exitCode": result.returncode,
            }
            return ToolResult(output=json.dumps(output_json), success=(result.returncode == 0))
        except Exception as exc:
            return ToolResult(output="", error=str(exc), success=False)
