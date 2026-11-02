"""FR-SCORE-01..08 golden vectors and stable tie-break behavior."""

from __future__ import annotations

from datetime import date

import pytest

from rfp_eval.domain.models import Criterion, CriterionResult, RankInput, ValidatedEvaluation
from rfp_eval.tools.ranking_tool import rank_suppliers, relative_performance_pct


def criterion(ident: int, weight: float) -> Criterion:
    return Criterion(
        criterion_id=ident, name=f"C{ident}", description="", weight=weight, max_score=10
    )


def entry(name: str, scores: tuple[float, float], day: int, rating: float = 4.0) -> RankInput:
    return RankInput(
        supplier_name=name,
        submission_date=date(2026, 10, day),
        experience_rating=rating,
        evaluation=ValidatedEvaluation(
            supplier_name=name,
            overall_summary="",
            criteria=[
                CriterionResult(criterion_id=i, score=score, max_score=10, justification="evidence")
                for i, score in enumerate(scores, 1)
            ],
            procurement_risks=[],
            warnings=[],
            llm_attempts=1,
        ),
    )


def test_fr_score_01_08_golden_vector() -> None:
    result = rank_suppliers(
        [entry("A", (9, 5), 12), entry("B", (7, 8), 10), entry("C", (9, 5), 15)],
        [criterion(1, 60), criterion(2, 40)],
    )
    assert result.benchmarks == {1: 9, 2: 8}
    assert [(s.supplier_name, s.final_rank, s.absolute_score, s.ppi) for s in result.suppliers] == [
        ("B", 1, 74.0, 86.67),
        ("A", 2, 74.0, 85.0),
        ("C", 3, 74.0, 85.0),
    ]
    assert result.tie_break_explanations == [
        "Rank 1 (B) ranked above Rank 2 (A) via Tier 1 rule: Higher PPI (86.67 vs 85.00).",
        "Rank 2 (A) and Rank 3 (C) tied on PPI (85.00). Tie resolved via Tier 2 rule: "
        "Earlier Submission Date (2026-10-12 vs 2026-10-15).",
    ]


def test_fr_score_04_zero_benchmark() -> None:
    assert relative_performance_pct(0, 0) == 100.0
    assert relative_performance_pct(3, 0) == 0.0


def test_fr_score_06_tier3_and_tier4() -> None:
    criteria = [criterion(1, 60), criterion(2, 40)]
    result = rank_suppliers(
        [
            entry("Zulu", (5, 5), 12, 4),
            entry("Alpha", (5, 5), 12, 4),
            entry("Bravo", (5, 5), 12, 3),
        ],
        criteria,
    )
    assert [s.supplier_name for s in result.suppliers] == ["Alpha", "Zulu", "Bravo"]
    assert result.tie_break_explanations == [
        "Rank 1 (Alpha) and Rank 2 (Zulu) tied on PPI (100.00), Submission Date "
        "(2026-10-12) and Experience Rating (4.0). Tie resolved via Tier 4 rule: "
        "Supplier Name alphabetical order (alpha vs zulu).",
        "Rank 2 (Zulu) and Rank 3 (Bravo) tied on PPI (100.00) and Submission Date "
        "(2026-10-12). Tie resolved via Tier 3 rule: Higher Historical Experience "
        "Rating (4.0 vs 3.0).",
    ]


def test_fr_score_06_input_order_does_not_change_output() -> None:
    criteria = [criterion(1, 60), criterion(2, 40)]
    inputs = [entry("A", (9, 5), 12), entry("B", (7, 8), 10), entry("C", (9, 5), 15)]
    assert rank_suppliers(inputs, criteria) == rank_suppliers(inputs[::-1], criteria[::-1])


def test_fr_score_06_duplicate_names_rejected() -> None:
    with pytest.raises(ValueError, match="unique"):
        rank_suppliers(
            [entry("A", (5, 5), 12), entry("a", (5, 5), 13)], [criterion(1, 60), criterion(2, 40)]
        )


def test_fr_score_01_no_active_criteria_rejected() -> None:
    with pytest.raises(ValueError, match="positive total"):
        rank_suppliers([entry("A", (5, 5), 12)], [])


def test_fr_score_04_all_zero_criterion_gives_each_supplier_100_pct() -> None:
    result = rank_suppliers(
        [entry("A", (0, 5), 12), entry("B", (0, 8), 10)],
        [criterion(1, 60), criterion(2, 40)],
    )
    assert result.benchmarks[1] == 0
    assert [s.scorecard[0].relative_pct for s in result.suppliers] == [100.0, 100.0]


def test_fr_score_06_rounded_ppi_tie_uses_submission_date() -> None:
    result = rank_suppliers(
        [entry("HigherRaw", (10, 10), 15), entry("Earlier", (9.9999, 10), 12)],
        [criterion(1, 60), criterion(2, 40)],
    )
    assert [(s.supplier_name, s.ppi) for s in result.suppliers] == [
        ("Earlier", 100.0),
        ("HigherRaw", 100.0),
    ]
    assert "Tier 2 rule" in result.tie_break_explanations[0]
