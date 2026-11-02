"""FR-NEG-01..06 winner-only on-demand playbook behavior."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from rfp_eval.domain.errors import LLMOutputError
from rfp_eval.llm.fake import FakeLLMClient
from rfp_eval.orchestration.runner import run_evaluation
from rfp_eval.services.briefing import render_negotiation_briefing
from rfp_eval.services.export import build_unified_export
from rfp_eval.services.negotiation import _remove_competitor_names, generate_and_store_playbook
from tests.integration.test_fr_pipe_01_graph import deps, reply, request


def playbook_reply() -> str:
    return json.dumps(
        {
            "stance": "Request firmer support terms.",
            "leverage_areas": ["Service quality"],
            "walkaway_risks": ["Capped remedies"],
            "negotiation_matrix": [
                {
                    "category": "SLA",
                    "proposal_vulnerability": "Capped credits",
                    "target_concession": "Higher service credits",
                    "scripted_meeting_question": "Can you raise the cap?",
                }
            ],
        }
    )


def test_fr_neg_01_04_generated_only_on_click_and_persisted_to_winner(tmp_path: Path) -> None:
    fake = FakeLLMClient([reply(8), reply(7), playbook_reply()])
    dependencies = deps(tmp_path, fake)
    run = run_evaluation(request(), dependencies)
    assert len(fake.calls) == 2
    assert all(
        row.negotiation_playbook_json is None
        for row in dependencies.result_repo.list_for_run(run.rfp_run_id)
    )
    playbook = generate_and_store_playbook(run, fake, dependencies.result_repo)
    rows = dependencies.result_repo.list_for_run(run.rfp_run_id)
    assert len(fake.calls) == 3
    assert rows[0].negotiation_playbook_json is not None
    assert rows[1].negotiation_playbook_json is None
    assert "| 1 | SLA |" in render_negotiation_briefing(playbook)
    assert "NexaWorks" not in fake.calls[-1][0] + fake.calls[-1][1]
    assert "two concise" in fake.calls[-1][0]
    assert _remove_competitor_names("NexaWorks proposed this", run) == (
        "[other supplier] proposed this"
    )
    exported = json.loads(
        build_unified_export(run.rfp_run_id, dependencies.run_repo, dependencies.result_repo)
    )
    assert exported["winner_negotiation_playbook"]["stance"] == playbook.stance


def test_fr_neg_03_invalid_json_does_not_persist(tmp_path: Path) -> None:
    fake = FakeLLMClient([reply(), reply(), "bad", "still bad"])
    dependencies = deps(tmp_path, fake)
    run = run_evaluation(request(), dependencies)
    with pytest.raises(LLMOutputError):
        generate_and_store_playbook(run, fake, dependencies.result_repo)
    assert all(
        row.negotiation_playbook_json is None
        for row in dependencies.result_repo.list_for_run(run.rfp_run_id)
    )


def test_fr_neg_06_competitor_name_in_output_is_rejected(tmp_path: Path) -> None:
    bad = json.loads(playbook_reply())
    bad["stance"] = "Compare with NexaWorks"
    fake = FakeLLMClient([reply(), reply(), json.dumps(bad)])
    dependencies = deps(tmp_path, fake)
    run = run_evaluation(request(), dependencies)
    with pytest.raises(LLMOutputError, match="another supplier"):
        generate_and_store_playbook(run, fake, dependencies.result_repo)
    row = dependencies.result_repo.list_for_run(run.rfp_run_id)[0]
    assert row.negotiation_playbook_json is None
