"""FR-LLM-01/03 client selection and secret handling."""

from __future__ import annotations

import pytest
from pydantic import SecretStr

from rfp_eval.domain.enums import Provider
from rfp_eval.domain.errors import ConfigError
from rfp_eval.llm.factory import get_llm_client, resolve_settings


@pytest.mark.parametrize("provider", list(Provider))
def test_fr_llm_01_four_provider_adapters(provider: Provider) -> None:
    client = get_llm_client(provider, SecretStr("test-secret"))
    assert client.provider == provider
    assert client.model


def test_fr_llm_03_demo_settings_require_secret() -> None:
    with pytest.raises(ConfigError, match="not configured"):
        resolve_settings(True, None, None, {})
    settings = resolve_settings(
        True, None, None, {"DEFAULT_LLM_PROVIDER": "openai", "DEFAULT_LLM_API_KEY": "private-key"}
    )
    assert settings.is_demo
    assert "private-key" not in repr(settings)
