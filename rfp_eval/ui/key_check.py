"""Small, session-scoped provider connectivity probe."""

from __future__ import annotations

from rfp_eval.domain.errors import ConfigError, LLMAuthError, LLMTransportError
from rfp_eval.llm.base import LLMSettings
from rfp_eval.llm.factory import get_llm_client
from rfp_eval.llm.providers.openai_client import OpenAIClient


def probe_llm(settings: LLMSettings) -> tuple[bool, str]:
    """Make one tiny JSON request and return only a safe connection status."""
    try:
        client = get_llm_client(settings.provider, settings.api_key, settings.model)
        if isinstance(client, OpenAIClient):
            client.sdk = client.sdk.with_options(timeout=8.0, max_retries=0)
        reply = client.complete(
            "Return a JSON object only.",
            'Return {"ok":true}.',
            max_tokens=32,
        )
    except (ConfigError, LLMAuthError, LLMTransportError) as error:
        return False, str(error)
    if not reply.text.strip():
        return False, "Provider returned an empty response."
    return True, "Connection verified."
