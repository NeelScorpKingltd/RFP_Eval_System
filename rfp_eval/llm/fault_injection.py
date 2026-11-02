"""Deterministic validation demonstration, never used as a cache value."""

from __future__ import annotations

from copy import deepcopy

from rfp_eval.domain.models import Criterion, RawEvaluation


class FaultInjector:
    """Alter one named supplier's parsed evaluation in demo mode."""

    def __init__(self, target_supplier: str) -> None:
        self.target_supplier = target_supplier

    def inject(
        self, supplier_name: str, raw: RawEvaluation, criteria: list[Criterion]
    ) -> RawEvaluation:
        """Set one score to 14 and omit another active criterion for the target."""
        if supplier_name != self.target_supplier or raw.payload is None:
            return raw
        active = sorted(
            (item for item in criteria if item.is_active), key=lambda item: item.criterion_id
        )
        if len(active) < 2:
            return raw
        payload = deepcopy(raw.payload)
        entries = payload.get("criteria")
        if not isinstance(entries, list):
            entries = []
        first, omitted = active[0].criterion_id, active[1].criterion_id
        retained = [
            item
            for item in entries
            if isinstance(item, dict) and item.get("criterion_id") != omitted
        ]
        target = next((item for item in retained if item.get("criterion_id") == first), None)
        if target is None:
            target = {"criterion_id": first, "justification": "Demo fault", "evidence": ""}
            retained.append(target)
        target["score"] = 14
        payload["criteria"] = retained
        return raw.model_copy(update={"payload": payload})
