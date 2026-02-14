"""人类参与者实体定义。

HumanParticipant 实现了 ParticipantProtocol，
收到消息后不走 LLM，而是挂起等待外部（API / WebSocket / 测试代码）提交回复。
"""

from __future__ import annotations

import uuid

from app.schemas.runtime import Message, Role


class PendingHumanRequest:
    """一条等待人类处理的消息请求。"""

    def __init__(self, request_id: str, message: Message):
        self.request_id = request_id
        self.message = message

    def __repr__(self) -> str:
        return (
            f"PendingHumanRequest(id={self.request_id!r}, "
            f"from={self.message.sender!r}, content={self.message.content!r})"
        )


class HumanParticipant:
    """人类参与者。

    与 Agent 共享同一套消息协议（ParticipantProtocol），
    但 I/O 路径完全不同：
    - Agent: receive_message → LLM Runner → 立即返回响应
    - Human: receive_message → 存入 pending → 返回 None → 等待外部 submit_reply

    使用流程：
        1. Agent 通过 send_message 工具给 Human 发消息
        2. GroupChat._process_one 调用 human.receive_message → 返回 None
        3. 外部系统（API / 测试）调用 human.submit_reply 提交回复
        4. 回复以 Message 形式返回，由调用方入队到 GroupChat.message_queue
    """

    def __init__(self, name: str, *, display_name: str | None = None):
        """初始化人类参与者。

        Args:
            name: 参与者唯一标识（同 agent_id 语义）。
            display_name: 展示名称。
        """

        self._name = name
        self.display_name = display_name or name
        self.history: list[Message] = []
        self._pending: dict[str, PendingHumanRequest] = {}

    @property
    def name(self) -> str:
        """参与者唯一标识。"""
        return self._name

    async def receive_message(self, message: Message) -> Message | None:
        """接收消息，创建待处理请求，不阻塞。

        消息被存入 pending 队列，等待外部通过 submit_reply 提交回复。

        Returns:
            始终返回 None — 人类不立即回复。
        """

        self.history.append(message)
        request_id = f"hr_{uuid.uuid4().hex[:8]}"
        self._pending[request_id] = PendingHumanRequest(
            request_id=request_id, message=message,
        )
        print(
            f"👤 [{self._name}] 收到来自 {message.sender} 的消息，"
            f"等待人工处理 (request_id={request_id})"
        )
        return None

    def submit_reply(self, request_id: str, content: str) -> Message:
        """人类提交回复。

        Args:
            request_id: 待处理请求的 ID。
            content: 人类回复的内容。

        Returns:
            构造好的 Message，caller 负责将其入队到 GroupChat。

        Raises:
            KeyError: 指定的 request_id 不存在。
        """

        request = self._pending.pop(request_id)
        reply = Message(
            role=Role.HUMAN,
            content=content,
            sender=self._name,
            target=request.message.sender,
        )
        self.history.append(reply)
        print(f"👤 [{self._name}] 回复 -> {request.message.sender}: {content}")
        return reply

    def get_pending_requests(self) -> dict[str, PendingHumanRequest]:
        """获取所有待处理请求的快照。"""

        return dict(self._pending)

    @property
    def has_pending(self) -> bool:
        """是否有待处理请求。"""

        return bool(self._pending)
