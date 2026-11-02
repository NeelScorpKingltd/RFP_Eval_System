"""Deterministic unified JSON export built from persisted rows."""

from __future__ import annotations

import json
from datetime import UTC

from rfp_eval.db.repositories import RunRepo, SupplierResultRepo


def build_unified_export(run_id: str, run_repo: RunRepo, result_repo: SupplierResultRepo) -> str:
    """Serialize the frozen unified run keys using only saved database content."""
    run = run_repo.get(run_id)
    rows = result_repo.list_for_run(run_id)
    if run is None or not rows:
        raise ValueError(f"Completed run not found: {run_id}")
    snapshots = [json.loads(row.result_json) for row in rows]
    first = snapshots[0]
    criteria = [{**item, "weight": item["weight"] / 100.0} for item in first["active_criteria"]]
    rankings = [
        {
            "final_rank": row.final_rank,
            "supplier_name": row.supplier_name,
            "submission_date": row.submission_date.isoformat(),
            "experience_rating": row.experience_rating,
            "absolute_score": row.absolute_score,
            "ppi": row.ppi,
            "scorecard": payload["criteria"],
            "overall_summary": payload["overall_summary"],
            "procurement_risks": payload["procurement_risks"],
        }
        for row, payload in zip(rows, snapshots, strict=True)
    ]
    winner = rows[0]
    data = {
        "rfp_run_id": run.rfp_run_id,
        "created_at": run.created_at.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z"),
        "status": run.status.value,
        "active_criteria": criteria,
        "peer_benchmarks": first["peer_benchmarks"],
        "validation_warnings": first["run_warnings"],
        "tie_break_explanations": first["tie_break_explanations"],
        "supplier_rankings": rankings,
        "winner_negotiation_playbook": (
            json.loads(winner.negotiation_playbook_json) if winner.negotiation_playbook_json else {}
        ),
        "security_findings": {
            row.supplier_name: payload["security_findings"]
            for row, payload in zip(rows, snapshots, strict=True)
        },
        "cache_stats": first["cache_stats"],
        "meta": {
            key: value
            for key, value in first["meta"].items()
            if key != "llm_attempts" and key != "cache_hit"
        },
    }
    return json.dumps(data, indent=2, ensure_ascii=False)
