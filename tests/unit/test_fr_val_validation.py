"""FR-VAL-01..03 hostile LLM reply normalization."""

from __future__ import annotations

from rfp_eval.domain.models import Criterion, RawEvaluation
from rfp_eval.tools.validation_tool import validate_evaluation


def criteria() -> list[Criterion]:
    return [
        Criterion(criterion_id=i, name=f"C{i}", description="", weight=50, max_score=10)
        for i in (1, 2)
    ]


def test_fr_val_02_03_missing_and_clipped() -> None:
    raw = RawEvaluation(
        payload={
            "supplier_name": "Imposter",
            "overall_summary": "Summary",
            "criteria": [{"criterion_id": 1, "score": 14, "justification": "Claim"}],
        },
        attempts=1,
    )
    output = validate_evaluation(raw, "Apex", criteria())
    assert output.supplier_name == "Apex"
    assert [row.score for row in output.criteria] == [10, 0]
    assert output.criteria[1].justification == (
        "Criterion missing from LLM output; normalized to 0 by Validation Tool"
    )
    assert output.warnings == [
        "Apex: Criterion 1 score (14) exceeded max_score (10); clipped to 10.",
        "Apex: Criterion 2 (C2) missing from LLM output; normalized to 0.",
    ]


def test_fr_val_01_unparseable_payload_falls_back() -> None:
    output = validate_evaluation(RawEvaluation(payload=None, attempts=2), "Apex", criteria())
    assert [row.score for row in output.criteria] == [0, 0]
    assert output.warnings == [
        "LLM output could not be parsed after 2 attempts; all criteria set to 0."
    ]


def test_fr_val_03_negative_and_nonnumeric() -> None:
    raw = RawEvaluation(
        payload={
            "overall_summary": 42,
            "criteria": [
                {"criterion_id": 1, "score": -2},
                {"criterion_id": 2, "score": "excellent"},
            ],
        },
        attempts=1,
    )
    output = validate_evaluation(raw, "Apex", criteria())
    assert [row.score for row in output.criteria] == [0, 0]
    assert output.overall_summary == ""
    assert output.warnings == [
        "Apex: Criterion 1 score (-2) below 0; clipped to 0.",
        "Apex: Criterion 2 score ('excellent') is not numeric; set to 0.",
    ]


def test_fr_val_01_unknown_duplicate_name_match_and_risk_normalization() -> None:
    raw = RawEvaluation(
        payload={
            "overall_summary": "Summary",
            "criteria": [
                "garbage",
                {"criterion_id": 99, "name": "c1", "score": 7, "evidence": "Page 1"},
                {"criterion_id": 1, "score": 8},
                {"criterion_id": 88, "score": 1},
                {"criterion_id": 2, "score": 5},
            ],
            "procurement_risks": [
                {},
                {"issue": "Capped SLA credits", "severity": "Extreme", "verbatim_excerpt": "cap"},
            ],
        },
        attempts=1,
    )
    output = validate_evaluation(raw, "Apex", criteria())
    assert [row.score for row in output.criteria] == [7, 5]
    assert output.criteria[0].evidence == "Page 1"
    assert output.procurement_risks[0].severity == "Medium"
    assert output.warnings == [
        "Apex: Duplicate criterion 1 ignored.",
        "Apex: Unknown criterion (88) ignored.",
        "Unknown risk severity ('Extreme'); normalized to Medium.",
    ]
