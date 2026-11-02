"""Google Gemini generate_content adapter."""

from __future__ import annotations

from typing import Any

from pydantic import SecretStr

from rfp_eval.domain.enums import Provider
from rfp_eval.llm.base import LLMReply
from rfp_eval.llm.providers._retry import request_with_retry


class GeminiClient:
    provider = Provider.GEMINI

    def __init__(self, api_key: SecretStr, model: str, sdk: Any = None) -> None:
        if sdk is None:
            from google import genai

            sdk = genai.Client(api_key=api_key.get_secret_value())
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
        """Request one Gemini completion with JSON MIME type when supported."""
        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=temperature,
            max_output_tokens=max_tokens,
            response_mime_type="application/json" if json_mode else None,
        )
        response = request_with_retry(
            "Gemini",
            lambda: self.sdk.models.generate_content(
                model=self.model,
                contents=user,
                config=config,
            ),
        )
        usage = response.usage_metadata
        return LLMReply(
            text=response.text or "",
            input_tokens=getattr(usage, "prompt_token_count", None),
            output_tokens=getattr(usage, "candidates_token_count", None),
        )
