"""Agent 实体定义（基于 OpenAI Agents SDK）。

Agent 实现了 ParticipantProtocol：
- receive_message 始终返回 None（所有通信通过消息队列）
- LLM 通过 send_message 工具回复发送者或联系其他参与者（受 handsoff 约束）
- send_message 触发 StopAtTools，Runner 立即结束（干净 handoff）
- final_output 自动转发给 SYSTEM 参与者（日志/审计）
- 异常信息自动转发给 SYSTEM 参与者（错误通知）
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from agents import Agent as SdkAgent, Runner, RunConfig
from agents.agent import StopAtTools
from agents.tool import Tool
from loguru import logger

from app.core.model_provider import get_run_config
from app.runtime.system import SYSTEM_PARTICIPANT_ID
from app.schemas.runtime import Message, Role
from app.services.skill_service import skill_manager

if TYPE_CHECKING:
    pass

# send_message 工具名称（与 runtime_tools.py 中 @function_tool 装饰的函数名一致）
_HANDOFF_TOOL_NAME = "send_message"


class Agent:
    """基于 OpenAI Agents SDK 的 Agent 封装。

    实现 ParticipantProtocol，可被 GroupChat 统一调度。
    所有通信通过消息队列完成，receive_message 始终返回 None。
    """

    def __init__(
        self,
        name: str,
        system_prompt: str,#TODO:replace with instruction
        tools: list[Tool] | None = None,
        skills: list[str] | None = None,
        *,
        handoff: list[str] | None = None,
        model: str | None = None,
        run_config: RunConfig | None = None,
        message_queue: list[tuple[str, str, str | None]] | None = None,
    ):
        """初始化 Agent 实例。

        Args:
            name: Agent 唯一标识。
            system_prompt: 系统提示词。
            tools: 可用工具列表。
            skills: 技能列表。
            handoff: 允许通信的参与者列表。
            model: LLM 模型标识。
            run_config: Runner 配置。
            message_queue: 共享消息队列引用（由 GroupChat 注入）。
        """

        self._name = name
        self.system_prompt = system_prompt
        self.tools = tools or []
        self.skills = skills or []
        self.handoff = handoff or []
        self.model = model
        self.run_config = run_config or get_run_config()
        self.role: str = "assistant"
        self.history: list[Message] = []
        self._message_queue = message_queue

        
        self.system_prompt = self._build_system_prompt()
        self._sdk_agent = self._build_sdk_agent()


    @property
    def name(self) -> str:
        """参与者唯一标识。"""
        return self._name

    def _build_system_prompt(self) -> str:
        """构建包含技能的系统提示词"""
        # 1. 基础提示词 (假设 config 中有 instruction 或 similar)
        base_prompt = getattr(self, "instruction", self.system_prompt)
        
        language_constraint = (
            "\n\n## GLOBAL CONSTRAINT\n"
            "Regardless of the language of the above instructions or tools, "
            "you must ALWAYS think and respond in the language used by the user "
            "(e.g., if User speaks Chinese, you speak Chinese)."
        )
        
        # 2. 加载技能
        skill_prompts = []
        if self.skills:
            skill_prompts.append("\n\n### 加载的能力 (Skills):")
            for skill_name in self.skills:
                
                skill = skill_manager.get_skill(skill_name)
                
                if skill:
                    skill_content = (
                        f"\n#### 【能力: {skill.metadata.name}】\n"
                        f"{skill.body_markdown}\n"
                    )
                    skill_prompts.append(skill_content)
                else:
                    # 可以在这里加日志警告：Skill not found
                    pass
        
        # 3. 拼接
        return base_prompt + "".join(skill_prompts) + language_constraint

    def _enqueue_to_system(self, content: str) -> None:
        """将消息入队发给 SYSTEM 参与者。"""

        if self._message_queue is not None:
            self._message_queue.append(
                (self._name, content, SYSTEM_PARTICIPANT_ID)
            )

    async def receive_message(self, message: Message) -> None:
        """接收消息并通过 LLM 处理。

        始终返回 None：
        - LLM 通过 send_message 工具进行回复（受 handsoff 约束）
        - final_output 自动转发给 SYSTEM（日志/审计）
        - 异常自动转发给 SYSTEM（错误通知）
        """

        self.history.append(message)
        logger.info(
            f"[{self._name}] 收到消息 from {message.sender}: {message.content}"
        )

        # 传入发送者信息，让 LLM 知道该回复谁
        input_text = f"[消息来自: {message.sender}] {message.content}"

        try:
            
            result = await Runner.run(
                self._sdk_agent,
                input_text,
                run_config=self.run_config,
            )
            final_output = str(result.final_output)
            logger.debug(f"[{self._name}] final_output: {final_output}")

            # final_output 转发给 SYSTEM（日志/审计）
            self._enqueue_to_system(final_output)

        except Exception as exc:
            error_msg = f"[ERROR] LLM 调用失败 ({self._name}): {exc}"
            logger.error(error_msg)
            # region agent log
            import json, time
            _lp = "/data/magent/evilve/.cursor/debug.log"
            try:
                _cause = getattr(exc, "__cause__", None)
                _context = getattr(exc, "__context__", None)
                with open(_lp, "a", encoding="utf-8") as _f:
                    _f.write(
                        json.dumps(
                            {
                                "timestamp": int(time.time() * 1000),
                                "location": "agents.py:Agent.receive_message:exception",
                                "message": "Runner.run raised exception",
                                "data": {
                                    "agent": self._name,
                                    "exc_type": type(exc).__name__,
                                    "exc_str": str(exc)[:1200],
                                    "exc_repr": repr(exc)[:1200],
                                    "exc_args": [str(a)[:400] for a in getattr(exc, "args", [])],
                                    "cause_type": type(_cause).__name__ if _cause else None,
                                    "cause_str": str(_cause)[:800] if _cause else None,
                                    "context_type": type(_context).__name__ if _context else None,
                                    "context_str": str(_context)[:800] if _context else None,
                                },
                                "hypothesisId": "H2,H4,H5",
                                "runId": "pre-fix",
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
            except Exception:
                pass
            # endregion

            # 异常转发给 SYSTEM（错误通知）
            self._enqueue_to_system(error_msg)

        return None

    def _build_sdk_agent(self) -> SdkAgent:
        """构建 SDK Agent 实例。

        如果工具列表中包含 send_message，则启用 StopAtTools，
        使 Runner 在 send_message 调用后立即停止（干净 handoff）。
        其他工具（datetime_now、bash、python_exec 等）仍正常多轮执行。
        """

        # 检查是否包含 send_message 工具
        has_send_message = any(
            getattr(t, "name", "") == _HANDOFF_TOOL_NAME
            for t in self.tools
        )

        tool_use_behavior: StopAtTools | str = (
            StopAtTools(stop_at_tool_names=[_HANDOFF_TOOL_NAME])
            if has_send_message
            else "run_llm_again"
        )

        return SdkAgent(
            name=self._name,
            instructions=self.system_prompt,
            tools=self.tools,
            model=self.model,
            tool_use_behavior=tool_use_behavior,
        )

    def rebuild_sdk_agent(self) -> None:
        """在工具或配置变更后重建 SDK Agent。"""

        self._sdk_agent = self._build_sdk_agent()
