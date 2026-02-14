"""运行时消息与工具返回模型。"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Role(str, Enum):
    """消息角色枚举。"""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    HUMAN = "human"


class Message(BaseModel):
    """运行时消息传输对象。"""

    role: Role
    content: str
    sender: str
    summary: str | None = Field(
        default=None,
        description="消息摘要，用于后续检索与上下文压缩",
    )
    target: str | None = Field(default=None, description="定向接收者")


class ToolResult(BaseModel):
    """工具执行结果。"""

    output: str
    error: str | None = None
    success: bool = True
