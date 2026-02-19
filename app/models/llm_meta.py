"""LLM 模型元数据（Pydantic 元数据，非数据库表）。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class LLMModel(BaseModel):
    """LLM 基础信息。"""

    model_id: str = Field(description="模型唯一标识")
    provider: str = Field(description="模型提供方")
    display_name: str = Field(description="对外展示名称")
    version: str | None = Field(default=None, description="模型版本")
    context_window: int | None = Field(default=None, description="上下文窗口长度")
    base_url: str | None = Field(default=None, description="API base URL，未设置时使用全局默认")
    api_key: str | None = Field(default=None, description="API Key，未设置时使用全局默认")
