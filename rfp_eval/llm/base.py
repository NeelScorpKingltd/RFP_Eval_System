"""Provider-independent LLM contracts."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, SecretStr

from rfp_eval.domain.enums import Provider


class LLMReply(BaseModel):
    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None


class LLMSettings(BaseModel):
    provider: Provider
    model: str
    api_key: SecretStr
    is_demo: bool = False


class LLMClient(Protocol):
    provider: Provider
    model: str

    def complete(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.0,
        json_mode: bool = True,
        max_tokens: int = 4096,
    ) -> LLMReply:
        """Return a provider's text response or raise a typed LLM error."""
        ...
