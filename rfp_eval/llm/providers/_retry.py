"""Translate provider exceptions and retry transient failures."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

from rfp_eval.domain.errors import ConfigError, LLMAuthError, LLMTransportError

T = TypeVar("T")


def request_with_retry(provider: str, request: Callable[[], T]) -> T:
    """Retry transport failures twice; turn authentication failures into safe errors."""
    for attempt in range(3):
        try:
            return request()
        except Exception as exc:
            code = getattr(exc, "status_code", None)
            if code is None:
                code = getattr(exc, "code", None)
            if code in (401, 403):
                raise LLMAuthError(f"{provider}: check your API key.") from None
            if code in (400, 404):
                raise ConfigError(
                    f"{provider}: model or request configuration is invalid."
                ) from None
            if code == 429:
                reason = "rate limit reached; try again later."
            elif code in (500, 502, 503, 504):
                reason = "provider service unavailable; try again later."
            else:
                reason = "connection failed; check network access and try again."
            if attempt == 2:
                raise LLMTransportError(f"{provider}: {reason}") from None
            time.sleep((1, 2)[attempt])
    raise AssertionError("unreachable")
