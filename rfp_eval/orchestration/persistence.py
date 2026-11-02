"""Build per-supplier persisted JSON from one completed graph state."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from rfp_eval.domain.models import StoredSupplierResult
from rfp_eval.llm.prompts import EVAL_PROMPT_VERSION
from rfp_eval.orchestration.state import RunState

if TYPE_CHECKING:
    from rfp_eval.orchestration.runner import Deps


def build_stored_rows(state: RunState, deps: Deps) -> list[StoredSupplierResult]:
    """Serialize scorecards and run snapshots without secrets or rejected files."""
    ranking = state["ranking"]
    rows: list[StoredSupplierResult] = []
    for supplier in ranking.suppliers:
        name = supplier.supplier_name
        evaluation = state["evaluations"][name]
        payload = {
            "supplier_name": name,
            "overall_summary": evaluation.overall_summary,
            "criteria": [item.model_dump(mode="json") for item in supplier.scorecard],
            "procurement_risks": [
                item.model_dump(mode="json") for item in evaluation.procurement_risks
            ],
            "validation_warnings": evaluation.warnings,
            "security_findings": [
                item.model_dump(mode="json") for item in state["documents"][name].findings
            ],
            "meta": {
                "provider": deps.llm.provider.value,
                "model": deps.llm.model,
                "cache_hit": name in state["cache_hits"],
                "fault_mode": state["fault_mode"],
                "prompt_version": EVAL_PROMPT_VERSION,
                "llm_attempts": evaluation.llm_attempts,
            },
            "source_text": state["documents"][name].text,
            "active_criteria": [
                item.model_dump(mode="json") for item in state["criteria"] if item.is_active
            ],
            "peer_benchmarks": {str(key): value for key, value in ranking.benchmarks.items()},
            "tie_break_explanations": ranking.tie_break_explanations,
            "run_warnings": state.get("warnings", []),
            "cache_stats": state["cache_stats"],
        }
        rows.append(
            StoredSupplierResult(
                rfp_run_id=state["run_id"],
                supplier_name=name,
                submission_date=supplier.submission_date,
                experience_rating=supplier.experience_rating,
                absolute_score=supplier.absolute_score,
                ppi=supplier.ppi,
                final_rank=supplier.final_rank,
                result_json=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                cache_hash=(
                    None
                    if state["fault_mode"]
                    or any(
                        "LLM output could not be parsed" in warning
                        for warning in evaluation.warnings
                    )
                    else state["cache_hashes"].get(name)
                ),
            )
        )
    return rows
