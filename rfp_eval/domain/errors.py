"""Typed errors handled at application boundaries."""

from __future__ import annotations

from rfp_eval.domain.enums import RejectionCode


class DocumentRejected(ValueError):
    """A supplier PDF failed preflight validation."""

    def __init__(self, code: RejectionCode, message: str) -> None:
        super().__init__(message)
        self.code = code


class GateViolation(ValueError):
    """Run prerequisites were not met."""


class LLMAuthError(RuntimeError):
    """The selected provider rejected the credentials."""


class LLMTransportError(RuntimeError):
    """The selected provider could not be reached."""


class LLMOutputError(RuntimeError):
    """The selected provider returned unusable output."""


class ConfigError(ValueError):
    """Application configuration is incomplete or invalid."""
