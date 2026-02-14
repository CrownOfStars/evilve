"""参与者协议定义。

群聊中的所有参与者（Agent、Human 等）均实现此协议，
使 GroupChat 能够统一分发消息，而无需关心参与者的具体类型。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.schemas.runtime import Message


@runtime_checkable
class ParticipantProtocol(Protocol):
    """群聊参与者协议。

    任何实现了 name 属性和 receive_message 方法的类
    均可作为 GroupChat 中的参与者。
    """

    @property
    def name(self) -> str:
        """参与者唯一标识。"""
        ...

    async def receive_message(self, message: Message) -> Message | None:
        """接收一条消息并返回响应。

        Args:
            message: 收到的消息。

        Returns:
            响应消息，如果暂时无法回复（如人类等待输入）则返回 None。
        """
        ...
