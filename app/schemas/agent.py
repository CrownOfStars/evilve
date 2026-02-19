"""Agent 元数据与状态模型。"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from app.models.llm_meta import LLMModel
from app.schemas.skill import SkillSchema


class AgentStatus(str, Enum):
    """Agent 可用性状态。"""

    TESTING = "testing"
    ARCHIVED = "archived"


class AgentProfile(BaseModel):
    """Agent 配置与能力描述。"""

    agent_id: str = Field(description="Agent 唯一标识")
    name: str = Field(description="Agent 展示名称")
    role: str = Field(description="Agent 角色标识")
    system_prompt: str = Field(description="创建时的系统提示词")
    tools: list[str] = Field(default_factory=list, description="工具列表")
    skills: list[SkillSchema] = Field(default_factory=list, description="技能列表")
    handsoff: list[str] = Field(
        default_factory=list,
        description="允许通信的 agent_id 列表",
    )
    model: LLMModel | None = Field(default=None, description="运行时使用的 LLM")
    status: AgentStatus = Field(default=AgentStatus.TESTING, description="可用性状态")#用于标记是否通过可用性测试，一旦通过可用性测试，就可以在后续项目中复用
