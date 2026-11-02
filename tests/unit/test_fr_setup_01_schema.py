"""FR-SETUP-01 database setup contract."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

from rfp_eval.db.repositories import CriteriaRepo, RunRepo, SupplierResultRepo
from rfp_eval.db.schema import init_and_seed_db
from rfp_eval.domain.models import StoredSupplierResult


def test_fr_setup_01_seed_is_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "db.sqlite"
    init_and_seed_db(path)
    init_and_seed_db(path)
    criteria = CriteriaRepo(path).list_all()
    assert len(criteria) == 5
    assert sum(item.weight for item in criteria if item.is_active) == 100


def test_fr_db_02_run_ids_and_atomic_supplier_persistence(tmp_path: Path) -> None:
    path = tmp_path / "db.sqlite"
    init_and_seed_db(path)
    runs = RunRepo(path)
    now = datetime(2026, 10, 30, tzinfo=UTC)
    first = runs.create(now)
    second = runs.create(now)
    assert first == "RUN-20261030-001"
    assert second == "RUN-20261030-002"
    results = SupplierResultRepo(path)
    row = StoredSupplierResult(
        rfp_run_id=first,
        supplier_name="Apex",
        submission_date=date(2026, 10, 10),
        experience_rating=4.8,
        absolute_score=88.5,
        ppi=91.25,
        final_rank=1,
        result_json='{"meta":{"fault_mode":false}}',
        cache_hash="abc",
    )
    results.save_completed(first, [row])
    assert results.list_for_run(first) == [row]
    assert results.find_by_cache_hash("abc") == row
    fault_row = row.model_copy(
        update={
            "rfp_run_id": second,
            "result_json": '{"meta":{"fault_mode":true}}',
        }
    )
    results.save_completed(second, [fault_row])
    assert results.find_by_cache_hash("abc") == row


def test_fr_db_02_failed_atomic_write_leaves_run_in_progress(tmp_path: Path) -> None:
    path = tmp_path / "db.sqlite"
    init_and_seed_db(path)
    run_id = RunRepo(path).create(datetime(2026, 10, 30, tzinfo=UTC))
    result = SupplierResultRepo(path)
    bad_row = StoredSupplierResult(
        rfp_run_id=run_id,
        supplier_name="Apex",
        submission_date=date(2026, 10, 10),
        experience_rating=4.0,
        absolute_score=80,
        ppi=80,
        final_rank=1,
        result_json="{}",
    )
    import sqlite3

    import pytest

    with pytest.raises(sqlite3.IntegrityError):
        result.save_completed(run_id, [bad_row, bad_row])
    assert result.list_for_run(run_id) == []
