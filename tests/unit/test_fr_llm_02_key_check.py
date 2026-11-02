"""FR-LLM-02 minimal provider connection check."""

from __future__ import annotations

from pydantic import SecretStr

from rfp_eval.domain.enums import Provider
from rfp_eval.domain.errors import LLMAuthError
from rfp_eval.llm.base import LLMReply, LLMSettings
from rfp_eval.ui import key_check


class ProbeClient:
    provider = Provider.OPENAI
    model = "fake"

    def __init__(self, fails: bool = False) -> None:
        self.fails = fails
        self.max_tokens = 0

    def complete(self, system: str, user: str, *, max_tokens: int = 4096) -> LLMReply:
        self.max_tokens = max_tokens
        if self.fails:
            raise LLMAuthError("OpenAI: check your API key.")
        return LLMReply(text='{"ok":true}')


def test_fr_llm_02_probe_is_small_and_safe(monkeypatch) -> None:
    settings = LLMSettings(provider=Provider.OPENAI, model="fake", api_key=SecretStr("private-key"))
    client = ProbeClient()
    monkeypatch.setattr(key_check, "get_llm_client", lambda *args: client)
    assert key_check.probe_llm(settings) == (True, "Connection verified.")
    assert client.max_tokens == 32
    client.fails = True
    assert key_check.probe_llm(settings) == (False, "OpenAI: check your API key.")
