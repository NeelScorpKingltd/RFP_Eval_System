"""FR-CRIT-03 active-weight boundary tests."""

from __future__ import annotations

import pytest

from rfp_eval.domain.models import Criterion
from rfp_eval.tools.weight_gate import check_weight_gate


@pytest.mark.parametrize(
    ("weight", "valid"),
    [(99.99, False), (100.0, True), (100.009, True), (100.011, False)],
)
def test_fr_crit_03_weight_boundary(weight: float, valid: bool) -> None:
    criterion = Criterion(criterion_id=1, name="A", description="A", weight=weight, max_score=10)
    assert check_weight_gate([criterion]).valid is valid


def test_fr_crit_03_no_active_criteria() -> None:
    assert not check_weight_gate([]).valid


def test_fr_crit_03_negative_weight() -> None:
    criterion = Criterion(criterion_id=1, name="A", description="A", weight=-1, max_score=10)
    assert not check_weight_gate([criterion]).valid
