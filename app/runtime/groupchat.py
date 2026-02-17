"""群聊运行时。

GroupChat 是多参与者（Agent + Human + System）的消息调度中心。
所有参与者都实现 ParticipantProtocol，通过统一的 receive_message 接口收发消息。

核心规则：
- 所有 receive_message 返回 None（通信全部通过消息队列）
- Agent 通过 send_message 工具通信（受 handsoff 约束）
- Human 通过外部 submit_reply 通信
- System 只收不发（日志/审计/错误通知 sink）
"""

from __future__ import annotations

import re
from collections.abc import Callable

from agents import RunConfig
from agents.tool import Tool
from loguru import logger

from app.core.model_provider import build_run_config_from_model, get_run_config
from app.runtime.agents import Agent
from app.runtime.human import HumanParticipant
from app.runtime.participant import ParticipantProtocol
from app.runtime.system import SYSTEM_PARTICIPANT_ID, SystemParticipant
from app.schemas.agent import AgentProfile
from app.schemas.runtime import Message, Role

# 默认最大消息处理轮次
DEFAULT_MAX_TURNS = 50


class GroupChat:
    """群聊运行时调度器。

    管理所有参与者（Agent、Human、System），通过消息队列驱动异步交互。

    核心概念：
    - participants: 所有参与者的字典，共享同一协议
    - message_queue: 待处理消息的 FIFO 队列
    - message_history: 已处理消息的完整历史
    - system: 内置的 System 参与者，接收 final_output 和错误
    """

    def __init__(
        self,
        default_run_config: RunConfig | None = None,
        *,
        max_turns: int = DEFAULT_MAX_TURNS,
    ):
        """初始化运行时。

        Args:
            default_run_config: 默认 RunConfig，当 Agent 未指定时使用。
            max_turns: 单次 drain_queue 的最大处理轮次（安全阀）。
        """

        self.participants: dict[str, ParticipantProtocol] = {}
        self.message_history: list[Message] = []
        self.message_queue: list[tuple[str, str, str | None]] = []
        self.default_run_config = default_run_config or get_run_config()
        self.max_turns = max_turns

        # 自动注册 System 参与者
        self.system = SystemParticipant()
        self.participants[SYSTEM_PARTICIPANT_ID] = self.system

    # ------------------------------------------------------------------
    # 参与者管理
    # ------------------------------------------------------------------

    def add_human(
        self, name: str, *, display_name: str | None = None,
    ) -> HumanParticipant:
        """添加人类参与者到群聊。

        Args:
            name: 人类参与者唯一标识。
            display_name: 展示名称。

        Returns:
            创建的 HumanParticipant 实例。
        """

        human = HumanParticipant(name=name, display_name=display_name)
        self.participants[name] = human
        logger.info(f"Added human participant: {name}")
        return human

    def get_human(self, name: str) -> HumanParticipant:
        """获取指定的人类参与者。

        Raises:
            KeyError: 参与者不存在或不是 HumanParticipant。
        """

        participant = self.participants[name]
        if not isinstance(participant, HumanParticipant):
            raise KeyError(f"Participant '{name}' is not a HumanParticipant")
        return participant

    def submit_human_reply(
        self, human_name: str, request_id: str, content: str,
    ) -> None:
        """人类提交回复，自动入队到消息队列。

        Args:
            human_name: 人类参与者标识。
            request_id: 待处理请求的 ID。
            content: 回复内容。
        """

        human = self.get_human(human_name)
        reply = human.submit_reply(request_id, content)
        self.message_history.append(reply)
        # 将回复作为新消息入队，target 为原始发送者
        if reply.target:
            self.message_queue.append((human_name, content, reply.target))

    def list_pending_human_requests(
        self, human_name: str,
    ) -> dict[str, object]:
        """列出指定人类参与者的所有待处理请求。"""

        human = self.get_human(human_name)
        return human.get_pending_requests()

    # ------------------------------------------------------------------
    # Agent 创建（基于 AgentProfile）
    # ------------------------------------------------------------------

    # runtime 命名空间工具映射
    _RUNTIME_TOOL_FACTORIES: dict[str, str] = {
        "runtime.send_message": "make_send_message_tool",
        "runtime.create_agent": "make_create_agent_tool",
        "runtime.list_agents": "make_list_agents_tool",
    }

    def create_agent_from_profile(
        self,
        profile: AgentProfile,
        *,
        extra_tools: list[Tool] | None = None,
    ) -> str:
        """基于 AgentProfile 创建 Agent 并加入群聊。

        工具解析流程：
        1. profile.tools 中 namespace != 'runtime' 的 tool_id 从 ToolRegistry 自动解析
        2. profile.tools 中 namespace == 'runtime' 的 tool_id 由运行时按需注入
        3. extra_tools 手动补充（用于未注册到 Registry 的临时工具）

        Agent 接收：
        - message_queue 引用（用于 final_output/error 自动转发给 SYSTEM）
        - handsoff 列表（注入到 send_message 工具做校验）
        """

        from app.tools.registry import ToolRegistry
        from app.tools.runtime_tools import (
            make_send_message_tool,
            make_create_agent_tool,
            make_list_agents_tool,
        )

        agent_id = profile.agent_id
        handsoff = profile.handsoff

        # 根据 LLMModel 自动构建 RunConfig
        if profile.model:
            run_config = build_run_config_from_model(profile.model)
            model_id = profile.model.model_id
        else:
            run_config = self.default_run_config
            model_id = None

        # 分离 runtime 工具和 registry 工具
        registry_tool_ids: list[str] = []
        runtime_tool_ids: list[str] = []

        for tool_id in profile.tools:
            if tool_id.startswith("runtime."):
                runtime_tool_ids.append(tool_id)
            else:
                registry_tool_ids.append(tool_id)

        # 从 Registry 解析非 runtime 工具
        agent_tools: list[Tool] = ToolRegistry.resolve_tools(registry_tool_ids)

        # 合并额外手动传入的工具
        if extra_tools:
            agent_tools.extend(extra_tools)

        # 按需注入 runtime 命名空间工具（send_message 需要 handsoff 列表）
        factory_map: dict[str, Callable[..., Tool]] = {
            "runtime.send_message": lambda: make_send_message_tool(
                self, agent_id, handsoff,
            ),
            "runtime.create_agent": lambda: make_create_agent_tool(self),
            "runtime.list_agents": lambda: make_list_agents_tool(self),
        }
        for rt_id in runtime_tool_ids:
            factory = factory_map.get(rt_id)
            if factory:
                agent_tools.append(factory())
            else:
                logger.warning(f"Unknown runtime tool: {rt_id}")

        # 从 SkillSchema 中提取技能名称列表，供 Agent 构建系统提示词
        skill_names = [s.metadata.name for s in profile.skills]

        # 创建 Agent，注入 message_queue 引用
        new_agent = Agent(
            name=agent_id,
            system_prompt=profile.system_prompt,
            tools=agent_tools,
            skills=skill_names,
            handoff=handsoff,
            model=model_id,
            run_config=run_config,
            message_queue=self.message_queue,
        )
        new_agent.role = profile.role


        self.participants[agent_id] = new_agent
        logger.info(f"Created agent: {agent_id} (Role: {profile.role})")
        return agent_id

    # ------------------------------------------------------------------
    # 消息处理
    # ------------------------------------------------------------------

    def parse_mentions(self, content: str) -> tuple[str | None, str]:
        """解析 @mentions。"""

        match = re.search(r"@(\w+)\s*(.*)", content, re.DOTALL)
        if match:
            return match.group(1), match.group(2)
        return None, content

    def broadcast_message(self, sender_name: str, content: str) -> None:
        """广播消息给所有其他参与者（不含 SYSTEM）。"""

        message = Message(role=Role.USER, content=content, sender=sender_name, target=None)
        self.message_history.append(message)
        logger.info(f"[Broadcast] {sender_name}: {content}")

        for name in self.participants:
            if name != sender_name and name != SYSTEM_PARTICIPANT_ID:
                self.message_queue.append((sender_name, content, name))

    async def send_message(
        self,
        sender_name: str,
        content: str,
        target: str | None = None,
    ) -> None:
        """发送消息入队并处理。"""

        self.message_queue.append((sender_name, content, target))
        await self.drain_queue()

    async def drain_queue(self) -> None:
        """处理队列中的所有消息。

        受 max_turns 安全阀保护，防止无限循环。
        遇到目标为 Human 且返回 None 的消息时继续处理队列中的后续消息。
        """

        turns = 0

        while self.message_queue and turns < self.max_turns:
            turns += 1
            current_sender, current_content, current_target = self.message_queue.pop(0)
            await self._process_one(current_sender, current_content, current_target)

        if self.message_queue:
            remaining = len(self.message_queue)
            logger.warning(
                f"达到最大轮次 {self.max_turns}，剩余 {remaining} 条消息未处理"
            )

    async def run_once(self) -> None:
        """处理队列中的一条消息。"""

        if not self.message_queue:
            return

        current_sender, current_content, current_target = self.message_queue.pop(0)
        await self._process_one(current_sender, current_content, current_target)

    async def _process_one(
        self,
        sender_name: str,
        content: str,
        target: str | None,
    ) -> None:
        """处理单条消息，统一分发给任意参与者。

        所有 receive_message 返回 None，因此本方法也不返回值。
        """

        if not target:
            target, content = self.parse_mentions(content)

        # 确定发送者 role
        sender_participant = self.participants.get(sender_name)
        if isinstance(sender_participant, HumanParticipant):
            role = Role.HUMAN
        elif sender_name == SYSTEM_PARTICIPANT_ID:
            role = Role.SYSTEM
        else:
            role = Role.USER



        message = Message(
            role=role,
            content=content,
            sender=sender_name,
            target=target,
        )
        self.message_history.append(message)

        if not target:
            self.broadcast_message(sender_name, content)
            return

        if target not in self.participants:
            logger.warning(f"Participant not found: @{target}")
            return

        target_participant = self.participants[target]

        if isinstance(target_participant, HumanParticipant):
            logger.info(f"[Direct] {sender_name} -> {target} (human): {content}")
        elif isinstance(target_participant, SystemParticipant):
            logger.debug(f"[System] {sender_name} -> system: {content[:80]}")
        else:
            logger.info(f"[Direct] {sender_name} -> {target}: {content}")

        await target_participant.receive_message(message)
