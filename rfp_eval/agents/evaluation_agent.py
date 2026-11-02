"""Isolated per-supplier LLM evaluation."""

from __future__ import annotations

from collections.abc import Sequence

from rfp_eval.domain.models import Criterion, RawEvaluation, SanitizedDocument
from rfp_eval.llm.base import LLMClient
from rfp_eval.llm.fault_injection import FaultInjector
from rfp_eval.llm.json_retry import call_with_json_retry
from rfp_eval.llm.prompts import build_evaluation_prompt
from rfp_eval.security.sandbox import wrap_untrusted


def _validate_shape(payload: dict[str, object]) -> None:
    """Require the top-level fields before full deterministic normalization."""
    if not isinstance(payload.get("supplier_name"), str):
        raise ValueError("supplier_name must be a string")
    if not isinstance(payload.get("overall_summary"), str):
        raise ValueError("overall_summary must be a string")
    if not isinstance(payload.get("criteria"), list):
        raise ValueError("criteria must be a list")


class EvaluationAgent:
    """Prompt one proposal at a time and return an untrusted parsed payload."""

    def __init__(self, client: LLMClient, fault: FaultInjector | None = None) -> None:
        self.client = client
        self.fault = fault

    def evaluate(self, doc: SanitizedDocument, criteria: Sequence[Criterion]) -> RawEvaluation:
        """Build isolated prompts, retry malformed JSON, and optionally inject a demo fault."""
        system, user = build_evaluation_prompt(wrap_untrusted(doc.text), criteria)
        raw = call_with_json_retry(self.client, system, user, validate=_validate_shape)
        if self.fault is not None:
            return self.fault.inject(doc.supplier_name, raw, list(criteria))
        return raw
