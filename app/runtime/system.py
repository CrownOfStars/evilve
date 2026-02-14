"""System 参与者实体定义。

SystemParticipant 是一个只读的消息 sink，
负责记录 Agent 的 final_output、错误和警告信息。

设计原则：
- 只接收，从不发起对话（receive_message 始终返回 None）
- 所有消息持久化到 history（未来写入数据库）
- 错误和警告通过 loguru 输出（未来推送到前端）
"""

from __future__ import annotations

from loguru import logger

from app.schemas.runtime import Message


# 预留的 System 参与者固定标识
SYSTEM_PARTICIPANT_ID = "system"


class SystemParticipant:
    """系统参与者 — 只读消息 sink。

    职责：
    1. 接收 Agent 的 final_output（作为对话日志/审计记录）
    2. 接收 Agent 的错误和异常信息
    3. 未来：将消息持久化到数据库、推送到前端 WebSocket

    不在任何 Agent 的 handsoff 列表中 —— Agent 不通过 send_message 联系它，
    而是由 Agent.receive_message 内部自动路由。
    """

    def __init__(self) -> None:
        """初始化 System 参与者。"""

        self._name = SYSTEM_PARTICIPANT_ID
        self.history: list[Message] = []

    @property
    def name(self) -> str:
        """参与者唯一标识。"""
        return self._name

    async def receive_message(self, message: Message) -> Message | None:
        """接收消息并记录，始终返回 None。

        根据消息内容的前缀区分类型并使用不同的日志级别：
        - [ERROR] 前缀 → logger.error
        - [WARN] 前缀 → logger.warning
        - 其他 → logger.info（Agent 的 final_output）
        """

        self.history.append(message)

        content = message.content
        sender = message.sender

        if content.startswith("[ERROR]"):
            logger.error(f"[SYSTEM] from {sender}: {content}")
        elif content.startswith("[WARN]"):
            logger.warning(f"[SYSTEM] from {sender}: {content}")
        else:
            logger.info(f"[SYSTEM] from {sender}: {content}")

        return None

    def get_history(self) -> list[Message]:
        """获取所有接收到的消息历史。"""

        return list(self.history)

    def get_errors(self) -> list[Message]:
        """获取所有错误消息。"""

        return [m for m in self.history if m.content.startswith("[ERROR]")]
