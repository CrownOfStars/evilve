"""自定义 ModelProvider。

支持自定义 base_url 与 api_key，便于对接兼容 OpenAI 接口的服务。
"""

from __future__ import annotations

from openai import AsyncOpenAI

from agents import ModelProvider, Model, RunConfig
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel

from app.core.config import get_settings


def _create_openai_client() -> AsyncOpenAI:
    """创建 AsyncOpenAI 客户端。"""

    settings = get_settings()
    return AsyncOpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key)


class CustomModelProvider(ModelProvider):
    """自定义 ModelProvider，支持可配置的 base_url/api_key。"""

    def __init__(self, client: AsyncOpenAI | None = None):
        self._client = client or _create_openai_client()

    def get_model(self, model_name: str | None) -> Model:
        """返回指定模型实例。"""

        settings = get_settings()
        resolved_name = model_name or settings.llm_model_name
       
        return OpenAIChatCompletionsModel(
            model=resolved_name,
            openai_client=self._client,
        )


def get_run_config(model_provider: CustomModelProvider | None = None) -> RunConfig:
    """获取默认 RunConfig。"""

    settings = get_settings()
    provider = model_provider or CustomModelProvider()
    return RunConfig(
        model_provider=provider,
        tracing_disabled=settings.llm_tracing_disabled,
    )


def build_run_config_from_model(llm_model: "LLMModel") -> RunConfig:
    """根据 LLMModel 构建专属 RunConfig。"""

    from app.schemas.model import LLMModel  # noqa: F811

    settings = get_settings()
    base_url = llm_model.base_url or settings.llm_base_url
    api_key = llm_model.api_key or settings.llm_api_key

    client = AsyncOpenAI(base_url=base_url, api_key=api_key)
    provider = CustomModelProvider(client=client)
    return RunConfig(
        model_provider=provider,
        tracing_disabled=settings.llm_tracing_disabled,
    )
