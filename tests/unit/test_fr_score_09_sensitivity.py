"""FR-SCORE-09 simulator must call the ranking tool for identical weights."""

from __future__ import annotations

from datetime import UTC, datetime

from rfp_eval.domain.enums import RunStatus
from rfp_eval.domain.models import CacheStats, Criterion, RunMeta, RunResult
from rfp_eval.services.sensitivity import recompute
from rfp_eval.tools.ranking_tool import rank_suppliers
from tests.unit.test_fr_score_ranking import entry


def test_fr_score_09_identity_with_ranking_tool() -> None:
    criteria = [
        Criterion(criterion_id=1, name="C1", description="", weight=60, max_score=10),
        Criterion(criterion_id=2, name="C2", description="", weight=40, max_score=10),
    ]
    inputs = [entry("A", (9, 5), 12), entry("B", (7, 8), 10)]
    expected = rank_suppliers(inputs, criteria)
    baseline = RunResult(
        rfp_run_id="RUN-20261030-001",
        created_at=datetime(2026, 10, 30, tzinfo=UTC),
        status=RunStatus.COMPLETED,
        active_criteria=criteria,
        ranking=expected,
        evaluations={item.supplier_name: item.evaluation for item in inputs},
        validation_warnings=[],
        security_findings={},
        cache_stats=CacheStats(),
        meta=RunMeta(provider="fake", model="fake"),
    )
    result = recompute(baseline, {1: 60, 2: 40})
    assert result.ranking == expected
    assert result.rank_deltas == {"B": 0, "A": 0}
    fallback = recompute(baseline, {1: 0, 2: 0})
    assert fallback.ranking == expected
    assert fallback.normalized_weights == {1: 60.0, 2: 40.0}
