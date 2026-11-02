"""Restore validated scores from persisted cache rows."""

from __future__ import annotations

import json

from rfp_eval.domain.models import (
    CriterionResult,
    ProcurementRisk,
    StoredSupplierResult,
    ValidatedEvaluation,
)


def with_current_name(value: ValidatedEvaluation, supplier_name: str) -> ValidatedEvaluation:
    """Rebind cached warning prefixes and metadata to the current supplier."""
    old = value.supplier_name
    warnings = [
        warning.replace(old + ":", supplier_name + ":", 1)
        if warning.startswith(old + ":")
        else warning
        for warning in value.warnings
    ]
    return value.model_copy(
        update={"supplier_name": supplier_name, "warnings": warnings},
        deep=True,
    )


def rebuild_cached_evaluation(row: StoredSupplierResult, supplier_name: str) -> ValidatedEvaluation:
    """Use stored scores and prose while replacing cached supplier metadata."""
    payload = json.loads(row.result_json)
    criteria = [
        CriterionResult.model_validate(
            {
                "criterion_id": item["criterion_id"],
                "score": item["score"],
                "max_score": item["max_score"],
                "justification": item.get("justification", ""),
                "evidence": item.get("evidence", ""),
            }
        )
        for item in payload["criteria"]
    ]
    risks = [ProcurementRisk.model_validate(item) for item in payload.get("procurement_risks", [])]
    evaluation = ValidatedEvaluation(
        supplier_name=row.supplier_name,
        overall_summary=payload.get("overall_summary", ""),
        criteria=criteria,
        procurement_risks=risks,
        warnings=payload.get("validation_warnings", []),
        llm_attempts=payload.get("meta", {}).get("llm_attempts", 0),
    )
    return with_current_name(evaluation, supplier_name)
