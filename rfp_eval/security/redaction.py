"""Remove credentials from provider errors before display or logging."""

from __future__ import annotations

import re

from pydantic import SecretStr

_BEARER = re.compile(r"Bearer\s+\S+", re.IGNORECASE)
_KEY = re.compile(r"\b(?:sk|gsk)_[A-Za-z0-9_-]{12,}\b|\bsk-[A-Za-z0-9_-]{12,}\b")


def redact(text: str, secret: SecretStr | None = None) -> str:
    """Mask a known secret and common bearer/key shapes in text."""
    if secret is not None:
        value = secret.get_secret_value()
        if value:
            text = text.replace(value, "[REDACTED]")
    return _KEY.sub("[REDACTED]", _BEARER.sub("Bearer [REDACTED]", text))
