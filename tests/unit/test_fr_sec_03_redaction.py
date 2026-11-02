"""FR-SEC-03 provider key masking."""

from __future__ import annotations

from pydantic import SecretStr

from rfp_eval.security.redaction import redact


def test_fr_sec_03_known_and_bearer_secrets_removed() -> None:
    text = "private123 Bearer abc456 sk-abcdefghijklmnop"
    cleaned = redact(text, SecretStr("private123"))
    assert "private123" not in cleaned
    assert "abc456" not in cleaned
    assert "sk-abcdefghijklmnop" not in cleaned
