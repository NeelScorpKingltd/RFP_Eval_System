"""Anthropic Messages adapter."""

from __future__ import annotations

from typing import Any

from pydantic import SecretStr

from rfp_eval.domain.enums import Provider
from rfp_eval.llm.base import LLMReply
from rfp_eval.llm.providers._retry import request_with_retry


class AnthropicClient:
    provider = Provider.ANTHROPIC

    def __init__(self, api_key: SecretStr, model: str, sdk: Any = None) -> None:
        if sdk is None:
            from anthropic import Anthropic

            sdk = Anthropic(api_key=api_key.get_secret_value())
        self.sdk = sdk
        self.model = model

    def complete(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.0,
        json_mode: bool = True,
        max_tokens: int = 4096,
    ) -> LLMReply:
        """Request one Anthropic message with JSON instructions in the prompt."""
        response = request_with_retry(
            "Anthropic",
            lambda: self.sdk.messages.create(
                model=self.model,
                system=system,
                messages=[{"role": "user", "content": user}],
                temperature=temperature,
                max_tokens=max_tokens,
            ),
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        return LLMReply(
            text=text,
            input_tokens=getattr(response.usage, "input_tokens", None),
            output_tokens=getattr(response.usage, "output_tokens", None),
        )
