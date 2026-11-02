"""Detect obvious instruction attempts in proposal text."""

from __future__ import annotations

import re

from rfp_eval.config import INJECTION_PATTERNS
from rfp_eval.domain.models import InjectionFinding

_COMPILED = tuple(re.compile(pattern, re.IGNORECASE) for pattern in INJECTION_PATTERNS)


def scan_for_injection(text: str, page: int | None = None) -> list[InjectionFinding]:
    """Return bounded, escaped snippets for suspicious phrases."""
    normalized = re.sub(r"\s+", " ", text)
    findings: list[InjectionFinding] = []
    for pattern in _COMPILED:
        for match in pattern.finditer(normalized):
            snippet = normalized[max(0, match.start() - 30) : match.end() + 30]
            findings.append(
                InjectionFinding(
                    kind="phrase",
                    pattern=pattern.pattern,
                    snippet=snippet[:120].replace("<", "&lt;").replace(">", "&gt;"),
                    page=page,
                )
            )
    return findings
