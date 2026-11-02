"""OpenAI Chat Completions adapter."""

from __future__ import annotations

from typing import Any

from pydantic import SecretStr

from rfp_eval.domain.enums import Provider
from rfp_eval.llm.base import LLMReply
from rfp_eval.llm.providers._retry import request_with_retry


class OpenAIClient:
    provider = Provider.OPENAI

    def __init__(self, api_key: SecretStr, model: str, sdk: Any = None) -> None:
        if sdk is None:
            from openai import OpenAI

            sdk = OpenAI(api_key=api_key.get_secret_value(), timeout=20.0, max_retries=0)
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
        """Request one JSON-capable OpenAI completion."""
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        response = request_with_retry("OpenAI", lambda: self.sdk.chat.completions.create(**kwargs))
        return LLMReply(
            text=response.choices[0].message.content or "",
            input_tokens=getattr(response.usage, "prompt_tokens", None),
            output_tokens=getattr(response.usage, "completion_tokens", None),
        )
