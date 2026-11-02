"""FR-PIPE-01..05 offline graph, persistence, cache, and export flows."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from rfp_eval.db.repositories import CriteriaRepo, RunRepo, SupplierResultRepo
from rfp_eval.db.schema import init_and_seed_db
from rfp_eval.domain.enums import PipelineStep, RunStatus
from rfp_eval.domain.errors import GateViolation, LLMAuthError, LLMTransportError
from rfp_eval.domain.models import SupplierInput
from rfp_eval.llm.fake import FakeLLMClient
from rfp_eval.orchestration.runner import Deps, run_evaluation
from rfp_eval.orchestration.state import RunRequest
from rfp_eval.services.export import build_unified_export
from rfp_eval.services.run_loader import load_run
from rfp_eval.tools.cache import MemoryCache

ROOT = Path(__file__).resolve().parents[2] / "sample_data" / "proposals"


def request(*, fault: bool = False, invalid: bool = False, third: bool = False) -> RunRequest:
    names = [("Apex Systems", "Apex_Systems.pdf"), ("NexaWorks", "NexaWorks.pdf")]
    if third:
        names.append(("Orbit Digital", "Orbit_Digital.pdf"))
    suppliers = [
        SupplierInput(
            supplier_name=name,
            submission_date=date(2026, 10, 10 + index),
            experience_rating=4.5,
            pdf_name=filename,
            pdf_bytes=(b"not pdf" if invalid and index == 1 else (ROOT / filename).read_bytes()),
        )
        for index, (name, filename) in enumerate(names)
    ]
    return RunRequest(suppliers=suppliers, fault_mode=fault)


def reply(score: int = 8) -> str:
    return json.dumps(
        {
            "supplier_name": "Provider-supplied name",
            "overall_summary": "Documented proposal.",
            "criteria": [
                {
                    "criterion_id": ident,
                    "score": score,
                    "justification": "Evidence",
                    "evidence": "Page 1",
                }
                for ident in range(1, 6)
            ],
            "procurement_risks": [],
        }
    )


def deps(tmp_path: Path, fake: FakeLLMClient) -> Deps:
    path = tmp_path / "evaluation.db"
    init_and_seed_db(path)
    return Deps(
        criteria_repo=CriteriaRepo(path),
        run_repo=RunRepo(path),
        result_repo=SupplierResultRepo(path),
        llm=fake,
        memory_cache=MemoryCache(),
        clock=lambda: datetime(2026, 10, 30, tzinfo=UTC),
    )


def test_fr_pipe_01_complete_persist_export_and_cache(tmp_path: Path) -> None:
    fake = FakeLLMClient([reply(8), reply(7)])
    dependencies = deps(tmp_path, fake)
    first = run_evaluation(request(), dependencies)
    assert first.status == RunStatus.COMPLETED
    assert first.rfp_run_id == "RUN-20261030-001"
    assert len(first.ranking.suppliers) == 2
    assert first.cache_stats.llm_calls == 2
    assert len(dependencies.result_repo.list_for_run(first.rfp_run_id)) == 2
    loaded = load_run(first.rfp_run_id, dependencies.run_repo, dependencies.result_repo)
    assert loaded.ranking == first.ranking
    exported = json.loads(
        build_unified_export(first.rfp_run_id, dependencies.run_repo, dependencies.result_repo)
    )
    assert exported["supplier_rankings"][0]["final_rank"] == 1
    assert exported["active_criteria"][0]["weight"] == 0.3
    assert exported["winner_negotiation_playbook"] == {}
    assert "source_text" not in json.dumps(exported)
    assert list(exported)[:9] == [
        "rfp_run_id",
        "created_at",
        "status",
        "active_criteria",
        "peer_benchmarks",
        "validation_warnings",
        "tie_break_explanations",
        "supplier_rankings",
        "winner_negotiation_playbook",
    ]
    assert build_unified_export(
        first.rfp_run_id, dependencies.run_repo, dependencies.result_repo
    ) == build_unified_export(first.rfp_run_id, dependencies.run_repo, dependencies.result_repo)

    second = run_evaluation(request(), dependencies)
    assert second.cache_stats.hits == 2
    assert second.cache_stats.llm_calls == 0
    assert len(fake.calls) == 2

    renamed = request()
    renamed.suppliers[0].supplier_name = "Apex Renamed"
    renamed.suppliers[0].submission_date = date(2026, 10, 9)
    renamed_result = run_evaluation(renamed, dependencies)
    assert renamed_result.cache_stats.hits == 2
    assert "Apex Renamed" in renamed_result.evaluations
    assert renamed_result.ranking.suppliers[0].submission_date == date(2026, 10, 9)

    edited = dependencies.criteria_repo.list_all()
    edited[0].weight = 40
    edited[-1].weight = 0
    dependencies.criteria_repo.save(edited)
    third = run_evaluation(request(), dependencies)
    assert third.cache_stats.hits == 2
    assert third.cache_stats.llm_calls == 0
    original_export = json.loads(
        build_unified_export(first.rfp_run_id, dependencies.run_repo, dependencies.result_repo)
    )
    assert original_export["active_criteria"][0]["weight"] == 0.3

    fresh_fake = FakeLLMClient([])
    fresh = Deps(
        criteria_repo=dependencies.criteria_repo,
        run_repo=dependencies.run_repo,
        result_repo=dependencies.result_repo,
        llm=fresh_fake,
        memory_cache=MemoryCache(),
        clock=dependencies.clock,
    )
    from_sqlite = run_evaluation(request(), fresh)
    assert from_sqlite.cache_stats.hits == 2
    assert from_sqlite.cache_stats.llm_calls == 0
    assert fresh_fake.calls == []


def test_fr_pipe_04_auth_failure_marks_run_failed(tmp_path: Path) -> None:
    fake = FakeLLMClient([LLMAuthError("check your API key")])
    dependencies = deps(tmp_path, fake)
    with pytest.raises(LLMAuthError):
        run_evaluation(request(), dependencies)
    assert dependencies.run_repo.get("RUN-20261030-001").status == RunStatus.FAILED


def test_fr_pipe_04_bad_pdf_fails_run_after_preflight(tmp_path: Path) -> None:
    dependencies = deps(tmp_path, FakeLLMClient([]))
    result = run_evaluation(request(invalid=True), dependencies)
    assert result.status == RunStatus.FAILED
    assert result.ranking is None
    assert any("at least two valid" in message.lower() for message in result.validation_warnings)


def test_fr_pipe_04_one_bad_pdf_does_not_abort_batch(tmp_path: Path) -> None:
    dependencies = deps(tmp_path, FakeLLMClient([reply(), reply()]))
    result = run_evaluation(request(invalid=True, third=True), dependencies)
    assert result.status == RunStatus.COMPLETED
    assert [item.supplier_name for item in result.ranking.suppliers] == [
        "Apex Systems",
        "Orbit Digital",
    ]
    assert any("not a valid PDF" in message for message in result.validation_warnings)


def test_fr_pipe_04_malformed_llm_reply_falls_back_for_one_supplier(tmp_path: Path) -> None:
    dependencies = deps(tmp_path, FakeLLMClient(["bad", "still bad", reply()]))
    result = run_evaluation(request(), dependencies)
    assert result.status == RunStatus.COMPLETED
    assert result.cache_stats.fallbacks == 1
    assert all(item.score == 0 for item in result.evaluations["Apex Systems"].criteria)
    assert result.evaluations["NexaWorks"].criteria[0].score == 8
    assert (
        next(
            row
            for row in dependencies.result_repo.list_for_run(result.rfp_run_id)
            if row.supplier_name == "Apex Systems"
        ).cache_hash
        is None
    )
    dependencies.llm = FakeLLMClient([reply(9)])
    repeated = run_evaluation(request(), dependencies)
    assert repeated.cache_stats.hits == 1
    assert repeated.cache_stats.llm_calls == 1


def test_fr_pipe_04_transport_failure_falls_back_for_one_supplier(tmp_path: Path) -> None:
    dependencies = deps(tmp_path, FakeLLMClient([LLMTransportError("unavailable"), reply()]))
    result = run_evaluation(request(), dependencies)
    assert result.status == RunStatus.COMPLETED
    assert result.cache_stats.fallbacks == 1
    assert any("LLM request failed" in message for message in result.validation_warnings)
    assert result.evaluations["NexaWorks"].criteria[0].score == 8


def test_fr_pipe_04_all_transport_failures_mark_run_failed(tmp_path: Path) -> None:
    dependencies = deps(
        tmp_path,
        FakeLLMClient(
            [
                LLMTransportError("OpenAI: connection failed"),
                LLMTransportError("OpenAI: connection failed"),
            ]
        ),
    )
    result = run_evaluation(request(), dependencies)
    assert result.status == RunStatus.FAILED
    assert result.ranking is None
    assert dependencies.run_repo.get(result.rfp_run_id).status == RunStatus.FAILED
    assert dependencies.result_repo.list_for_run(result.rfp_run_id) == []


def test_fr_pipe_04_unexpected_error_is_safe_and_failed(tmp_path: Path) -> None:
    dependencies = deps(tmp_path, FakeLLMClient([RuntimeError("private-key secret"), reply()]))
    with pytest.raises(RuntimeError, match="Evaluation failed") as caught:
        run_evaluation(request(), dependencies)
    assert "private-key secret" not in str(caught.value)
    assert dependencies.run_repo.get("RUN-20261030-001").status == RunStatus.FAILED


class RecordingReporter:
    def __init__(self) -> None:
        self.started: list[PipelineStep] = []
        self.finished: list[PipelineStep] = []
        self.warnings: list[str] = []

    def step_started(self, step: PipelineStep, detail: str = "") -> None:
        self.started.append(step)

    def step_progress(self, step: PipelineStep, done: int, total: int, detail: str = "") -> None:
        assert 1 <= done <= total

    def step_finished(self, step: PipelineStep, detail: str = "") -> None:
        self.finished.append(step)

    def warning(self, message: str) -> None:
        self.warnings.append(message)


def test_fr_pipe_02_progress_reports_all_steps(tmp_path: Path) -> None:
    dependencies = deps(tmp_path, FakeLLMClient([reply(), reply()]))
    reporter = RecordingReporter()
    result = run_evaluation(request(), dependencies, reporter)
    assert result.status == RunStatus.COMPLETED
    expected = list(PipelineStep)
    assert reporter.started == expected
    assert reporter.finished == expected


def test_fr_pipe_05_gate_prevents_run_creation(tmp_path: Path) -> None:
    dependencies = deps(tmp_path, FakeLLMClient([]))
    edited = dependencies.criteria_repo.list_all()
    edited[0].weight = 25
    dependencies.criteria_repo.save(edited)
    with pytest.raises(GateViolation):
        run_evaluation(request(), dependencies)
    assert dependencies.run_repo.get("RUN-20261030-001") is None


def test_fr_pipe_05_orchestrator_rechecks_supplier_metadata(tmp_path: Path) -> None:
    dependencies = deps(tmp_path, FakeLLMClient([]))
    invalid = request()
    invalid.suppliers[0].experience_rating = 8
    with pytest.raises(GateViolation, match="between 0 and 5"):
        run_evaluation(invalid, dependencies)
    assert dependencies.run_repo.get("RUN-20261030-001") is None


def test_fr_val_04_fault_mode_bypasses_both_cache_tiers(tmp_path: Path) -> None:
    fake = FakeLLMClient([reply(), reply(), reply(), reply()])
    dependencies = deps(tmp_path, fake)
    first = run_evaluation(request(), dependencies)
    assert first.status == RunStatus.COMPLETED
    fault = run_evaluation(request(fault=True), dependencies)
    assert fault.status == RunStatus.COMPLETED
    assert fault.cache_stats.hits == 0
    assert fault.cache_stats.llm_calls == 2
    assert len(fault.validation_warnings) == 2
    assert all(
        row.cache_hash is None for row in dependencies.result_repo.list_for_run(fault.rfp_run_id)
    )
