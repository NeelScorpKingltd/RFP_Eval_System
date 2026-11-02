"""Runtime limits and overridable provider model identifiers."""

from __future__ import annotations

import os

MAX_PDF_MB = 10
MAX_PDF_PAGES = 15
MIN_TEXT_CHARS = 100
MAX_SOURCE_CHARS = 60_000
STRIP_HIDDEN_TEXT = True
SCORE_PRECISION = 2
EVAL_PROMPT_VERSION = "eval-v2"
INJECTION_PATTERNS = (
    r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts?)",
    r"disregard\s+(the\s+)?(above|previous|earlier)",
    r"system\s+override",
    r"you\s+are\s+now\s+(an?\s+)?(assistant|ai|model)",
    r"(give|assign|award)\s+(this\s+)?(supplier|proposal|vendor)\s+"
    r"(a\s+)?(maximum|max|perfect|full)\s+score",
    r"(reveal|print|show)\s+(your\s+)?(system\s+)?prompt",
)
DEFAULT_MODELS = {
    "openai": os.getenv("RFP_OPENAI_MODEL", "gpt-4o-mini"),
    "gemini": os.getenv("RFP_GEMINI_MODEL", "gemini-3.8-flash"),
    "anthropic": os.getenv("RFP_ANTHROPIC_MODEL", "claude-sonnet-4-6"),
    "groq": os.getenv("RFP_GROQ_MODEL", "openai/gpt-oss-120b"),
}
