"""FR-LLM-01 offline SDK adapter and safe error tests."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from rfp_eval.domain.errors import ConfigError, LLMAuthError, LLMTransportError
from rfp_eval.llm.providers import _retry
from rfp_eval.llm.providers.anthropic_client import AnthropicClient
from rfp_eval.llm.providers.gemini_client import GeminiClient
from rfp_eval.llm.providers.groq_client import GroqClient
from rfp_eval.llm.providers.openai_client import OpenAIClient


class StubError(Exception):
    def __init__(self, status_code: int, message: str = "secret-key") -> None:
        super().__init__(message)
        self.status_code = status_code


def test_fr_llm_01_chat_adapters_send_isolated_messages() -> None:
    captured: list[dict[str, object]] = []

    def create(**kwargs: object) -> SimpleNamespace:
        captured.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok":true}'))],
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=3),
        )

    sdk = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    for adapter in (OpenAIClient, GroqClient):
        reply = adapter(SecretStr("secret-key"), "model", sdk=sdk).complete("system", "user")
        assert reply.text == '{"ok":true}'
        assert reply.input_tokens == 10
    assert all(item["messages"][0]["content"] == "system" for item in captured)
    assert all(item["response_format"] == {"type": "json_object"} for item in captured)


def test_fr_llm_01_anthropic_adapter_with_stub() -> None:
    def create(**kwargs: object) -> SimpleNamespace:
        assert kwargs["system"] == "system"
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text="{}")],
            usage=SimpleNamespace(input_tokens=4, output_tokens=2),
        )

    sdk = SimpleNamespace(messages=SimpleNamespace(create=create))
    reply = AnthropicClient(SecretStr("secret-key"), "model", sdk=sdk).complete("system", "user")
    assert (reply.text, reply.output_tokens) == ("{}", 2)


def test_fr_llm_01_gemini_adapter_with_stub() -> None:
    def generate_content(**kwargs: object) -> SimpleNamespace:
        assert kwargs["model"] == "model"
        assert kwargs["config"].response_mime_type == "application/json"
        return SimpleNamespace(
            text="{}",
            usage_metadata=SimpleNamespace(prompt_token_count=4, candidates_token_count=2),
        )

    sdk = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
    reply = GeminiClient(SecretStr("secret-key"), "model", sdk=sdk).complete("system", "user")
    assert (reply.text, reply.output_tokens) == ("{}", 2)


@pytest.mark.parametrize(
    ("status", "error"),
    [
        (401, LLMAuthError),
        (404, ConfigError),
        (429, LLMTransportError),
    ],
)
def test_fr_llm_01_error_messages_never_echo_secret(
    status: int,
    error: type[Exception],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(_retry.time, "sleep", lambda _: None)

    def fail() -> None:
        raise StubError(status)

    with pytest.raises(error) as caught:
        _retry.request_with_retry("Provider", fail)
    assert "secret-key" not in str(caught.value)


@pytest.mark.parametrize(
    ("status", "expected"),
    [(429, "rate limit"), (503, "service unavailable"), (None, "connection failed")],
)
def test_fr_llm_01_transport_category_is_safe(
    status: int | None, expected: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(_retry.time, "sleep", lambda _: None)

    def fail() -> None:
        if status is None:
            raise ConnectionError("secret-key")
        raise StubError(status)

    with pytest.raises(LLMTransportError, match=expected) as caught:
        _retry.request_with_retry("Provider", fail)
    assert "secret-key" not in str(caught.value)
