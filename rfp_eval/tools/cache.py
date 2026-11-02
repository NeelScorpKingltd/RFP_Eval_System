"""Content-based evaluation cache projection and in-memory tier."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence

from rfp_eval.config import EVAL_PROMPT_VERSION
from rfp_eval.domain.models import Criterion, ValidatedEvaluation


def criteria_projection(criteria: Sequence[Criterion]) -> list[dict[str, int | str]]:
    """Return active LLM-visible criterion fields in stable ID order, excluding weights."""
    return [
        {
            "criterion_id": item.criterion_id,
            "name": item.name,
            "description": item.description,
            "max_score": item.max_score,
        }
        for item in sorted(criteria, key=lambda row: row.criterion_id)
        if item.is_active
    ]


def compute_cache_hash(pdf_bytes: bytes, criteria: Sequence[Criterion]) -> str:
    """Hash PDF bytes, prompt version, and canonical LLM-visible criterion JSON."""
    projection = {"v": EVAL_PROMPT_VERSION, "criteria": criteria_projection(criteria)}
    canonical = json.dumps(
        projection, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(pdf_bytes + b"\x00" + canonical).hexdigest()


class MemoryCache:
    """Session-scoped cache that never serves or stores fault-mode evaluations."""

    def __init__(self) -> None:
        self._values: dict[str, ValidatedEvaluation] = {}

    def get(self, key: str, *, fault_mode: bool = False) -> ValidatedEvaluation | None:
        """Return a defensive copy of a cached validation, unless fault mode is active."""
        if fault_mode:
            return None
        item = self._values.get(key)
        return item.model_copy(deep=True) if item else None

    def put(self, key: str, value: ValidatedEvaluation, *, fault_mode: bool = False) -> None:
        """Store a defensive copy unless fault mode is active."""
        if not fault_mode:
            self._values[key] = value.model_copy(deep=True)
