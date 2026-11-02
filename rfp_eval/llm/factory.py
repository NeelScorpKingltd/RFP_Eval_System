"""Resolve provider settings and construct SDK adapters."""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import SecretStr

from rfp_eval.config import DEFAULT_MODELS
from rfp_eval.domain.enums import Provider
from rfp_eval.domain.errors import ConfigError
from rfp_eval.llm.base import LLMClient, LLMSettings
from rfp_eval.llm.providers.anthropic_client import AnthropicClient
from rfp_eval.llm.providers.gemini_client import GeminiClient
from rfp_eval.llm.providers.groq_client import GroqClient
from rfp_eval.llm.providers.openai_client import OpenAIClient


def get_llm_client(provider: Provider, api_key: SecretStr, model: str | None = None) -> LLMClient:
    """Build the selected provider adapter using a caller-supplied secret."""
    selected = model or DEFAULT_MODELS[provider.value]
    if provider is Provider.OPENAI:
        return OpenAIClient(api_key, selected)
    if provider is Provider.GEMINI:
        return GeminiClient(api_key, selected)
    if provider is Provider.ANTHROPIC:
        return AnthropicClient(api_key, selected)
    if provider is Provider.GROQ:
        return GroqClient(api_key, selected)
    raise ConfigError("Unsupported LLM provider")


def resolve_settings(
    use_demo: bool,
    provider: Provider | None,
    api_key: str | None,
    secrets: Mapping[str, str],
) -> LLMSettings:
    """Choose BYOK or configured demo settings without importing Streamlit."""
    if use_demo:
        demo_provider = secrets.get("DEFAULT_LLM_PROVIDER")
        demo_key = secrets.get("DEFAULT_LLM_API_KEY")
        if not demo_provider or not demo_key:
            raise ConfigError("Demo model is not configured.")
        try:
            selected = Provider(demo_provider)
        except ValueError as exc:
            raise ConfigError("Demo provider is not supported.") from exc
        return LLMSettings(
            provider=selected,
            model=DEFAULT_MODELS[selected.value],
            api_key=SecretStr(demo_key),
            is_demo=True,
        )
    if provider is None or not api_key:
        raise ConfigError("Select a provider and enter an API key.")
    return LLMSettings(
        provider=provider, model=DEFAULT_MODELS[provider.value], api_key=SecretStr(api_key)
    )
