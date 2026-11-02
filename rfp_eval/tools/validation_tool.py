"""Normalize untrusted LLM payloads against authoritative criteria."""

from __future__ import annotations

import math
from collections.abc import Sequence

from rfp_eval.domain.models import (
    Criterion,
    CriterionResult,
    ProcurementRisk,
    RawEvaluation,
    ValidatedEvaluation,
)


def _missing(supplier: str, criterion: Criterion, warnings: list[str]) -> CriterionResult:
    warnings.append(
        f"{supplier}: Criterion {criterion.criterion_id} ({criterion.name}) "
        "missing from LLM output; normalized to 0."
    )
    return CriterionResult(
        criterion_id=criterion.criterion_id,
        score=0,
        max_score=criterion.max_score,
        justification="Criterion missing from LLM output; normalized to 0 by Validation Tool",
    )


def _normalize_score(
    raw: object, supplier: str, criterion: Criterion, warnings: list[str]
) -> float:
    ident = criterion.criterion_id
    if isinstance(raw, bool) or not isinstance(raw, (float, int)) or not math.isfinite(raw):
        warnings.append(f"{supplier}: Criterion {ident} score ({raw!r}) is not numeric; set to 0.")
        return 0.0
    value = float(raw)
    if value < 0:
        warnings.append(f"{supplier}: Criterion {ident} score ({raw}) below 0; clipped to 0.")
        return 0.0
    if value > criterion.max_score:
        warnings.append(
            f"{supplier}: Criterion {ident} score ({raw}) exceeded max_score "
            f"({criterion.max_score}); clipped to {criterion.max_score}."
        )
        return float(criterion.max_score)
    return value


def _risks(payload: object, warnings: list[str]) -> list[ProcurementRisk]:
    if not isinstance(payload, list):
        return []
    result: list[ProcurementRisk] = []
    for item in payload[:15]:
        if not isinstance(item, dict) or not isinstance(item.get("issue"), str):
            continue
        severity = item.get("severity", "Medium")
        if severity not in ("High", "Medium", "Low"):
            warnings.append(f"Unknown risk severity ({severity!r}); normalized to Medium.")
            severity = "Medium"
        result.append(
            ProcurementRisk(
                risk_category=str(item.get("risk_category", "Technical")),
                severity=severity,
                issue=item["issue"],
                verbatim_excerpt=str(item.get("verbatim_excerpt", "")),
            )
        )
    return result


def validate_evaluation(
    raw: RawEvaluation, supplier_name: str, criteria: Sequence[Criterion]
) -> ValidatedEvaluation:
    """Clip, fill, and order one supplier's LLM scores, preserving exact warnings."""
    active = sorted((c for c in criteria if c.is_active), key=lambda c: c.criterion_id)
    if raw.payload is None:
        message = (
            f"LLM output could not be parsed after {raw.attempts} attempts; all criteria set to 0."
        )
        return ValidatedEvaluation(
            supplier_name=supplier_name,
            overall_summary=message,
            criteria=[
                CriterionResult(
                    criterion_id=c.criterion_id,
                    score=0,
                    max_score=c.max_score,
                    justification=(
                        "Criterion missing from LLM output; normalized to 0 by Validation Tool"
                    ),
                )
                for c in active
            ],
            procurement_risks=[],
            warnings=[message],
            llm_attempts=raw.attempts,
        )
    payload = raw.payload
    warnings: list[str] = []
    source = payload.get("criteria")
    entries = source if isinstance(source, list) else []
    matched: dict[int, dict[str, object]] = {}
    by_id = {c.criterion_id: c for c in active}
    by_name = {c.name.casefold(): c for c in active}
    for item in entries:
        if not isinstance(item, dict):
            continue
        ident = item.get("criterion_id")
        criterion = by_id.get(ident) if isinstance(ident, int) else None
        if criterion is None and isinstance(item.get("name"), str):
            criterion = by_name.get(item["name"].casefold())
        if criterion is None:
            warnings.append(f"{supplier_name}: Unknown criterion ({ident!r}) ignored.")
        elif criterion.criterion_id in matched:
            warnings.append(
                f"{supplier_name}: Duplicate criterion {criterion.criterion_id} ignored."
            )
        else:
            matched[criterion.criterion_id] = item
    rows: list[CriterionResult] = []
    for criterion in active:
        item = matched.get(criterion.criterion_id)
        if item is None:
            rows.append(_missing(supplier_name, criterion, warnings))
            continue
        rows.append(
            CriterionResult(
                criterion_id=criterion.criterion_id,
                score=_normalize_score(item.get("score"), supplier_name, criterion, warnings),
                max_score=criterion.max_score,
                justification=str(item.get("justification", "")),
                evidence=str(item.get("evidence", "")),
            )
        )
    summary = payload.get("overall_summary")
    return ValidatedEvaluation(
        supplier_name=supplier_name,
        overall_summary=summary if isinstance(summary, str) else "",
        criteria=rows,
        procurement_risks=_risks(payload.get("procurement_risks"), warnings),
        warnings=warnings,
        llm_attempts=raw.attempts,
    )
