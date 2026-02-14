"""配置管理。

集中化配置入口，便于后续扩展为多环境与密钥管理。
"""

from __future__ import annotations
import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用运行配置。

    通过环境变量覆盖，避免硬编码常量。
    """

    model_config = SettingsConfigDict(env_prefix="EVILVE_", case_sensitive=False)

    app_name: str = Field(default="evilve", description="应用名称")
    api_v1_prefix: str = Field(default="/api/v1", description="API 前缀")
    environment: str = Field(default="dev", description="运行环境标识")
    log_level: str = Field(default="INFO", description="日志等级")
    database_url: str = Field(
        default="sqlite+aiosqlite:///./evilve.db",
        description="数据库连接串",
    )

    # LLM 配置
    llm_base_url: str = Field(
        default="https://api.siliconflow.cn/v1",
        description="LLM API base URL",
    )
    llm_api_key: str = Field(
        default="",
        description="LLM API Key",
    )
    llm_model_name: str = Field(
        default="Qwen/Qwen3-VL-30B-A3B-Thinking",
        description="默认模型名称",
    )
    llm_tracing_disabled: bool = Field(
        default=False,
        description="是否禁用 SDK tracing",
    )


@lru_cache
def get_settings() -> Settings:
    """获取配置实例，避免重复解析环境变量。"""

    settings = Settings()
    if settings.llm_api_key == "":
        settings.llm_api_key = os.getenv("OPENAI_API_KEY")
    return settings
