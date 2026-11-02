"""Recompute a stored evaluation under alternative criterion weights."""

from __future__ import annotations

from collections.abc import Mapping

from rfp_eval.domain.models import RankInput, RunResult, SensitivityResult
from rfp_eval.tools.ranking_tool import rank_suppliers


def recompute(baseline: RunResult, slider_weights: Mapping[int, float]) -> SensitivityResult:
    """Normalize sliders to 100 and rank stored scores without LLM or database calls."""
    if baseline.ranking is None:
        raise ValueError("A completed baseline ranking is required")
    active = sorted(
        (c for c in baseline.active_criteria if c.is_active), key=lambda c: c.criterion_id
    )
    proposed = {
        c.criterion_id: max(0.0, slider_weights.get(c.criterion_id, c.weight)) for c in active
    }
    total = sum(proposed.values())
    if total <= 0:
        proposed = {c.criterion_id: c.weight for c in active}
        total = sum(proposed.values())
    if total <= 0:
        raise ValueError("Active criteria must have positive total weight")
    weights = {ident: proposed[ident] * 100.0 / total for ident in sorted(proposed)}
    adjusted = [c.model_copy(update={"weight": weights[c.criterion_id]}) for c in active]
    entries = [
        RankInput(
            supplier_name=s.supplier_name,
            submission_date=s.submission_date,
            experience_rating=s.experience_rating,
            evaluation=baseline.evaluations[s.supplier_name],
        )
        for s in baseline.ranking.suppliers
    ]
    ranking = rank_suppliers(entries, adjusted)
    old = {s.supplier_name: s.final_rank for s in baseline.ranking.suppliers}
    deltas = {s.supplier_name: old[s.supplier_name] - s.final_rank for s in ranking.suppliers}
    return SensitivityResult(ranking=ranking, normalized_weights=weights, rank_deltas=deltas)
