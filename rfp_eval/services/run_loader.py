"""Reload a completed historical run without a new LLM call."""

from __future__ import annotations

import json

from rfp_eval.db.repositories import RunRepo, SupplierResultRepo
from rfp_eval.domain.models import (
    CacheStats,
    Criterion,
    CriterionResult,
    InjectionFinding,
    ProcurementRisk,
    RankedSupplier,
    RankingResult,
    RunMeta,
    RunResult,
    ScorecardRow,
    ValidatedEvaluation,
)


def load_run(run_id: str, run_repo: RunRepo, result_repo: SupplierResultRepo) -> RunResult:
    """Reconstruct scorecards, warnings, and metadata from persisted result JSON."""
    run = run_repo.get(run_id)
    rows = result_repo.list_for_run(run_id)
    if run is None or not rows:
        raise ValueError(f"Completed run not found: {run_id}")
    payloads = {row.supplier_name: json.loads(row.result_json) for row in rows}
    first = payloads[rows[0].supplier_name]
    suppliers: list[RankedSupplier] = []
    evaluations: dict[str, ValidatedEvaluation] = {}
    findings: dict[str, list[InjectionFinding]] = {}
    for row in rows:
        payload = payloads[row.supplier_name]
        scorecard = [ScorecardRow.model_validate(item) for item in payload["criteria"]]
        suppliers.append(
            RankedSupplier(
                final_rank=row.final_rank,
                supplier_name=row.supplier_name,
                submission_date=row.submission_date,
                experience_rating=row.experience_rating,
                absolute_score=row.absolute_score,
                ppi=row.ppi,
                scorecard=scorecard,
            )
        )
        evaluations[row.supplier_name] = ValidatedEvaluation(
            supplier_name=row.supplier_name,
            overall_summary=payload["overall_summary"],
            criteria=[CriterionResult.model_validate(item) for item in payload["criteria"]],
            procurement_risks=[
                ProcurementRisk.model_validate(item) for item in payload["procurement_risks"]
            ],
            warnings=payload["validation_warnings"],
            llm_attempts=payload["meta"]["llm_attempts"],
        )
        findings[row.supplier_name] = [
            InjectionFinding.model_validate(item) for item in payload["security_findings"]
        ]
    return RunResult(
        rfp_run_id=run_id,
        created_at=run.created_at,
        status=run.status,
        active_criteria=[Criterion.model_validate(item) for item in first["active_criteria"]],
        ranking=RankingResult(
            benchmarks={int(key): value for key, value in first["peer_benchmarks"].items()},
            suppliers=suppliers,
            tie_break_explanations=first["tie_break_explanations"],
        ),
        evaluations=evaluations,
        validation_warnings=first["run_warnings"],
        security_findings=findings,
        cache_stats=CacheStats.model_validate(first["cache_stats"]),
        meta=RunMeta.model_validate(first["meta"]),
    )
