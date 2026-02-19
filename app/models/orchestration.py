"""GPost Agent Orchestration 的数据库模型。

合并自 backend/models.py，将 SQLAlchemy 转为 SQLModel 异步模型。
使用 gpost_ 表名前缀以避免与 app 现有 agents/tools 表冲突。
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlmodel import Field, SQLModel

if TYPE_CHECKING:
    pass


def _uuid_str() -> str:
    return str(uuid.uuid4())


# --- Link Tables ---


# GpostSkillToolLink 已合并至 app.models.skill.SkillToolLink


class GpostAgentSkillLink(SQLModel, table=True):
    """Agents <-> Skills 多对多关联表。"""

    __tablename__ = "gpost_agents_skills"

    agent_id: str = Field(foreign_key="gpost_agents.id", primary_key=True)
    skill_id: str = Field(foreign_key="gpost_skills.id", primary_key=True)
    enabled: bool = True


# --- Core Models (GpostTool→tool.ToolOrchestration, GpostSkill→skill.SkillOrchestration) ---


class GpostProvider(SQLModel, table=True):
    """LLM 提供商模型。"""

    __tablename__ = "gpost_providers"

    id: str = Field(primary_key=True, default_factory=_uuid_str)
    name: str
    base_url: str | None = None
    api_key: str | None = None
    is_active: bool = True

    # llms 通过 GpostLLM.provider_id FK 关联


class GpostLLM(SQLModel, table=True):
    """Provider 下的 LLM 模型。"""

    __tablename__ = "gpost_llms"

    id: str = Field(primary_key=True, default_factory=_uuid_str)
    provider_id: str = Field(foreign_key="gpost_providers.id")
    remote_id: str
    is_llm: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # provider 通过 provider_id FK 关联
    # agents 通过 GpostAgent.model_id FK 关联


class GpostAgent(SQLModel, table=True):
    """Orchestration Agent 模型。"""

    __tablename__ = "gpost_agents"

    id: str = Field(primary_key=True, default_factory=_uuid_str)
    name: str
    role: str = "assistant"
    avatar: str | None = None
    description: str | None = None

    model_id: str | None = Field(default=None, foreign_key="gpost_llms.id")
    model_provider: str | None = None
    model_name: str | None = None
    temperature: float = 0.7

    system_prompt: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # model/skills 通过 model_id 和 GpostAgentSkillLink 关联，暂不声明 Relationship


class GpostSession(SQLModel, table=True):
    """会话模型。"""

    __tablename__ = "gpost_sessions"

    id: str = Field(primary_key=True, default_factory=_uuid_str)
    title: str | None = None
    user_id: str = "default_user"
    status: str = "active"
    graph_config: str | None = None  # JSON stored as string
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # messages, session_agents 通过 FK 关联


class GpostSessionAgent(SQLModel, table=True):
    """Session 中的 Agent 实例快照。"""

    __tablename__ = "gpost_session_agents"

    id: str = Field(primary_key=True, default_factory=_uuid_str)
    session_id: str = Field(foreign_key="gpost_sessions.id")
    original_agent_id: str | None = Field(default=None, foreign_key="gpost_agents.id")
    override_system_prompt: str | None = None
    override_model: str | None = None
    memory_context: str | None = None  # JSON

    # session 通过 session_id FK 关联


class GpostMessage(SQLModel, table=True):
    """聊天消息模型。"""

    __tablename__ = "gpost_messages"

    id: str = Field(primary_key=True, default_factory=_uuid_str)
    session_id: str = Field(foreign_key="gpost_sessions.id")
    role: str
    content: str
    agent_id: str | None = Field(default=None, foreign_key="gpost_agents.id")
    thought_process: str | None = None  # JSON
    msg_type: str = "text"
    parent_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # session 通过 session_id FK 关联
