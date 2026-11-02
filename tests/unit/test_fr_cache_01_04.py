"""FR-CACHE-01..04 canonical projection and fault-mode isolation."""

from __future__ import annotations

from rfp_eval.domain.models import Criterion, ValidatedEvaluation
from rfp_eval.llm.fake import FakeLLMClient
from rfp_eval.llm.json_retry import call_with_json_retry
from rfp_eval.tools.cache import MemoryCache, compute_cache_hash


def criterion(
    ident: int, weight: float = 50, description: str = "A", max_score: int = 10
) -> Criterion:
    return Criterion(
        criterion_id=ident,
        name=f"C{ident}",
        description=description,
        weight=weight,
        max_score=max_score,
    )


def test_fr_cache_01_02_stable_order_and_weight_only_change() -> None:
    original = [criterion(1), criterion(2)]
    expected = compute_cache_hash(b"pdf", original)
    assert expected == compute_cache_hash(b"pdf", original[::-1])
    assert expected == compute_cache_hash(b"pdf", [criterion(1, 80), criterion(2, 20)])
    assert expected != compute_cache_hash(b"other pdf", original)
    assert expected != compute_cache_hash(b"pdf", [criterion(1, description="B"), criterion(2)])
    assert expected != compute_cache_hash(b"pdf", [criterion(1, max_score=11), criterion(2)])


def test_fr_cache_04_fault_mode_neither_reads_nor_writes() -> None:
    cache = MemoryCache()
    value = ValidatedEvaluation(
        supplier_name="Apex",
        overall_summary="",
        criteria=[],
        procurement_risks=[],
        warnings=[],
        llm_attempts=1,
    )
    cache.put("normal", value)
    assert cache.get("normal", fault_mode=True) is None
    cache.put("fault", value, fault_mode=True)
    assert cache.get("fault") is None
    cached = cache.get("normal")
    assert cached == value and cached is not value


def test_fr_cache_02_weight_only_change_reuses_scores_without_llm() -> None:
    first_criteria = [criterion(1, 80), criterion(2, 20)]
    second_criteria = [criterion(1, 50), criterion(2, 50)]
    fake = FakeLLMClient(['{"criteria":[]}'])
    cache = MemoryCache()

    def evaluate_if_missing(criteria: list[Criterion]) -> ValidatedEvaluation:
        key = compute_cache_hash(b"same pdf bytes", criteria)
        existing = cache.get(key)
        if existing is not None:
            return existing
        raw = call_with_json_retry(fake, "system", "user", validate=lambda _: None)
        assert raw.payload is not None
        value = ValidatedEvaluation(
            supplier_name="Apex",
            overall_summary="",
            criteria=[],
            procurement_risks=[],
            warnings=[],
            llm_attempts=raw.attempts,
        )
        cache.put(key, value)
        return value

    assert evaluate_if_missing(first_criteria) == evaluate_if_missing(second_criteria)
    assert len(fake.calls) == 1
