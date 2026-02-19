"""GPost Agent Orchestration API 的 Pydantic 模型。

合并自 backend/schemas.py，用于 Agent/Skill/Tool/Provider/Session 等 CRUD 接口。
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


# --- Common Helpers ---


class JSONField(str):
    """Helper to treat strings as JSON in Pydantic."""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v: str | dict | list) -> str:
        if isinstance(v, (dict, list)):
            return json.dumps(v)
        return str(v)


# --- Tool Schemas (复用 app.schemas.tool) ---

from app.schemas.tool import Tool, ToolCreate, ToolBase  # noqa: F401

# --- Skill Schemas (复用 app.schemas.skill) ---

from app.schemas.skill import Skill, SkillCreate, SkillBase  # noqa: F401

# --- Agent Schemas ---


class AgentBase(BaseModel):
    """Agent 基础字段。"""

    name: str
    role: str = "assistant"
    avatar: str | None = None
    description: str | None = None
    model_id: str | None = None
    model_provider: str | None = None
    model_name: str | None = None
    temperature: float = 0.7
    system_prompt: str | None = None


class AgentCreate(AgentBase):
    """创建 Agent 请求。"""

    skill_ids: list[str] = Field(default_factory=list)


class Agent(AgentBase):
    """Agent 响应模型。"""

    id: str
    created_at: datetime
    skills: list[Skill] = Field(default_factory=list)
    model: LLM | None = None

    model_config = ConfigDict(from_attributes=True)


# --- LLM Schemas ---


class LLMBase(BaseModel):
    """LLM 基础字段。"""

    provider_id: str
    remote_id: str
    is_llm: bool = True


class LLM(LLMBase):
    """LLM 响应模型。"""

    id: str

    model_config = ConfigDict(from_attributes=True)


# --- Provider Schemas ---


class ProviderBase(BaseModel):
    """Provider 基础字段。"""

    name: str
    base_url: str | None = None
    api_key: str | None = None
    is_active: bool = True


class ProviderCreate(ProviderBase):
    """创建 Provider 请求。"""

    pass


class Provider(ProviderBase):
    """Provider 响应模型。"""

    id: str

    model_config = ConfigDict(from_attributes=True)


# --- Session Schemas ---


class SessionAgentBase(BaseModel):
    """SessionAgent 基础字段。"""

    original_agent_id: str
    override_system_prompt: str | None = None
    override_model: str | None = None


class SessionAgentCreate(SessionAgentBase):
    """创建 SessionAgent 请求。"""

    pass


class SessionAgent(SessionAgentBase):
    """SessionAgent 响应模型。"""

    id: str
    session_id: str
    memory_context: str | dict | None = None

    model_config = ConfigDict(from_attributes=True)


class MessageBase(BaseModel):
    """Message 基础字段。"""

    role: str
    content: str
    agent_id: str | None = None
    thought_process: str | list[dict] | None = None
    msg_type: str = "text"
    parent_id: str | None = None


class MessageCreate(MessageBase):
    """创建 Message 请求。"""

    pass


class Message(MessageBase):
    """Message 响应模型。"""

    id: str
    session_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SessionBase(BaseModel):
    """Session 基础字段。"""

    title: str | None = None
    user_id: str = "default_user"
    status: str = "active"
    graph_config: str | dict | None = None


class SessionCreate(SessionBase):
    """创建 Session 请求。"""

    pass


class Session(SessionBase):
    """Session 响应模型。"""

    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SessionDetail(Session):
    """Session 详情（含 messages 与 session_agents）。"""

    messages: list[Message] = Field(default_factory=list)
    session_agents: list[SessionAgent] = Field(default_factory=list)


# --- Chat Request Schemas ---


class ChatRequest(BaseModel):
    """Chat 发送消息请求。"""

    session_id: str
    message: str
    target_agent_id: str | None = None


class ChatStopRequest(BaseModel):
    """Chat 停止请求。"""

    session_id: str


# 解决 Agent.model -> LLM 的前向引用
Agent.model_rebuild()
