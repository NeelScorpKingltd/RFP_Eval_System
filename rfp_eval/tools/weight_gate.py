"""Validate active criterion weights before evaluation."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel

from rfp_eval.domain.models import Criterion


class GateResult(BaseModel):
    valid: bool
    active_total: float
    message: str


def check_weight_gate(criteria: Sequence[Criterion]) -> GateResult:
    """Return whether active weights sum to 100 within the frozen tolerance."""
    active = [criterion for criterion in criteria if criterion.is_active]
    total = sum(criterion.weight for criterion in active)
    if not active:
        return GateResult(valid=False, active_total=total, message="No active criteria.")
    if any(criterion.weight < 0 for criterion in active):
        return GateResult(valid=False, active_total=total, message="Weights cannot be negative.")
    valid = abs(total - 100.0) < 0.01
    message = (
        "Criteria weights total 100%."
        if valid
        else f"Active weights total {total:.2f}%; 100% required."
    )
    return GateResult(valid=valid, active_total=total, message=message)
