"""Stable domain enumerations."""

from __future__ import annotations

from enum import StrEnum


class Provider(StrEnum):
    OPENAI = "openai"
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"
    GROQ = "groq"


class Severity(StrEnum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class RunStatus(StrEnum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class PipelineStep(StrEnum):
    SANITIZE = "sanitize"
    CACHE = "cache_check"
    EVALUATE = "evaluate"
    VALIDATE = "validate"
    SCORE = "score"
    BENCHMARK = "benchmark"
    RANK = "rank"
    PERSIST = "persist"


class RejectionCode(StrEnum):
    TOO_LARGE = "TOO_LARGE"
    NOT_A_PDF = "NOT_A_PDF"
    ENCRYPTED = "ENCRYPTED"
    TOO_MANY_PAGES = "TOO_MANY_PAGES"
    NO_TEXT = "NO_TEXT"
