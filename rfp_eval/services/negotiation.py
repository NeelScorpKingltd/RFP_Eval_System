"""Generate and persist a playbook for the completed run winner."""

from __future__ import annotations

import json
import re

from rfp_eval.agents.negotiation_agent import LLMClient, NegotiationAgent
from rfp_eval.db.repositories import SupplierResultRepo
from rfp_eval.domain.enums import RunStatus
from rfp_eval.domain.errors import LLMOutputError
from rfp_eval.domain.models import RunResult, WinnerNegotiationPlaybook


def _remove_competitor_names(source: str, run: RunResult) -> str:
    if run.ranking is None:
        return source
    for supplier in run.ranking.suppliers[1:]:
        source = re.sub(
            re.escape(supplier.supplier_name), "[other supplier]", source, flags=re.IGNORECASE
        )
    return source


def generate_and_store_playbook(
    run: RunResult,
    client: LLMClient,
    result_repo: SupplierResultRepo,
) -> WinnerNegotiationPlaybook:
    """Generate on click, validate, and update only Rank 1's persisted row."""
    if run.status != RunStatus.COMPLETED or run.ranking is None:
        raise ValueError("A completed ranking is required")
    winner = run.ranking.suppliers[0]
    row = next(
        (item for item in result_repo.list_for_run(run.rfp_run_id) if item.final_rank == 1), None
    )
    if row is None:
        raise ValueError("Rank 1 result is missing")
    payload = json.loads(row.result_json)
    source = _remove_competitor_names(payload["source_text"], run)
    playbook = NegotiationAgent(client).generate(winner, source, run.ranking.benchmarks)
    rendered = playbook.model_dump_json()
    for supplier in run.ranking.suppliers[1:]:
        if supplier.supplier_name.casefold() in rendered.casefold():
            raise LLMOutputError("Playbook named another supplier; no playbook was saved.")
    result_repo.save_winner_playbook(
        run.rfp_run_id,
        rendered,
    )
    return playbook
