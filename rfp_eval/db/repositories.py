"""Parameterised SQLite repository operations."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from rfp_eval.db.connection import connection
from rfp_eval.domain.enums import RunStatus
from rfp_eval.domain.models import Criterion, StoredRun, StoredSupplierResult


class CriteriaRepo:
    """Read and update persisted evaluation criteria."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def list_all(self) -> list[Criterion]:
        """Return criteria ordered by stable identifier."""
        with connection(self.path) as conn:
            rows = conn.execute(
                "SELECT * FROM evaluation_criteria ORDER BY criterion_id"
            ).fetchall()
        return [Criterion.model_validate(dict(row)) for row in rows]

    def save(self, criteria: list[Criterion]) -> None:
        """Update existing criteria in one transaction."""
        with connection(self.path) as conn:
            for item in criteria:
                conn.execute(
                    """UPDATE evaluation_criteria SET name=?, description=?, weight=?,
                       max_score=?, is_active=? WHERE criterion_id=?""",
                    (
                        item.name,
                        item.description,
                        item.weight,
                        item.max_score,
                        int(item.is_active),
                        item.criterion_id,
                    ),
                )


class RunRepo:
    """Create run IDs and update lifecycle status."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def create(self, now: datetime) -> str:
        """Allocate the next daily run ID inside one write transaction."""
        day = now.strftime("%Y%m%d")
        with connection(self.path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT MAX(rfp_run_id) FROM rfp_runs WHERE rfp_run_id LIKE ?",
                (f"RUN-{day}-%",),
            ).fetchone()
            last = row[0]
            next_number = int(last.rsplit("-", 1)[1]) + 1 if last else 1
            run_id = f"RUN-{day}-{next_number:03d}"
            conn.execute(
                "INSERT INTO rfp_runs(rfp_run_id, created_at, status) VALUES (?, ?, ?)",
                (run_id, now.isoformat(), RunStatus.IN_PROGRESS.value),
            )
        return run_id

    def set_status(self, run_id: str, status: RunStatus) -> None:
        """Persist a completed or failed run state."""
        with connection(self.path) as conn:
            cursor = conn.execute(
                "UPDATE rfp_runs SET status=? WHERE rfp_run_id=?",
                (status.value, run_id),
            )
            if cursor.rowcount != 1:
                raise ValueError(f"Unknown run ID: {run_id}")

    def get(self, run_id: str) -> StoredRun | None:
        """Load a persisted run header by ID."""
        with connection(self.path) as conn:
            row = conn.execute("SELECT * FROM rfp_runs WHERE rfp_run_id=?", (run_id,)).fetchone()
        return StoredRun.model_validate(dict(row)) if row else None

    def list_recent(self) -> list[StoredRun]:
        """List saved run headers, newest first, without reading proposal content."""
        with connection(self.path) as conn:
            rows = conn.execute(
                "SELECT * FROM rfp_runs ORDER BY created_at DESC, rfp_run_id DESC LIMIT 100"
            ).fetchall()
        return [StoredRun.model_validate(dict(row)) for row in rows]


class SupplierResultRepo:
    """Store completed supplier rows and retrieve cache candidates."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def save_completed(self, run_id: str, rows: list[StoredSupplierResult]) -> None:
        """Insert every supplier row and complete the run atomically."""
        if any(row.rfp_run_id != run_id for row in rows):
            raise ValueError("Supplier result belongs to a different run")
        with connection(self.path) as conn:
            conn.executemany(
                """INSERT INTO supplier_results
                   (rfp_run_id, supplier_name, submission_date, experience_rating,
                    absolute_score, ppi, final_rank, result_json,
                    negotiation_playbook_json, cache_hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    (
                        row.rfp_run_id,
                        row.supplier_name,
                        row.submission_date.isoformat(),
                        row.experience_rating,
                        row.absolute_score,
                        row.ppi,
                        row.final_rank,
                        row.result_json,
                        row.negotiation_playbook_json,
                        row.cache_hash,
                    )
                    for row in rows
                ],
            )
            cursor = conn.execute(
                "UPDATE rfp_runs SET status=? WHERE rfp_run_id=? AND status=?",
                (RunStatus.COMPLETED.value, run_id, RunStatus.IN_PROGRESS.value),
            )
            if cursor.rowcount != 1:
                raise ValueError(f"Run is not in progress: {run_id}")

    def list_for_run(self, run_id: str) -> list[StoredSupplierResult]:
        """Load supplier rows in deterministic rank order."""
        with connection(self.path) as conn:
            rows = conn.execute(
                """SELECT * FROM supplier_results WHERE rfp_run_id=?
                   ORDER BY final_rank, supplier_name COLLATE NOCASE""",
                (run_id,),
            ).fetchall()
        return [StoredSupplierResult.model_validate(dict(row)) for row in rows]

    def find_by_cache_hash(self, cache_hash: str) -> StoredSupplierResult | None:
        """Find a completed, non-fault result eligible for reuse."""
        with connection(self.path) as conn:
            rows = conn.execute(
                """SELECT sr.* FROM supplier_results sr
                   JOIN rfp_runs rr ON rr.rfp_run_id = sr.rfp_run_id
                   WHERE sr.cache_hash=? AND rr.status=?
                   ORDER BY rr.created_at DESC, sr.rfp_run_id DESC""",
                (cache_hash, RunStatus.COMPLETED.value),
            ).fetchall()
        for row in rows:
            item = StoredSupplierResult.model_validate(dict(row))
            payload = json.loads(item.result_json)
            fallback = any(
                "LLM output could not be parsed" in warning
                for warning in payload.get("validation_warnings", [])
            )
            if not payload.get("meta", {}).get("fault_mode", False) and not fallback:
                return item
        return None

    def save_winner_playbook(self, run_id: str, playbook_json: str) -> None:
        """Update the Rank 1 row only after a validated playbook is generated."""
        with connection(self.path) as conn:
            cursor = conn.execute(
                """UPDATE supplier_results SET negotiation_playbook_json=?
                   WHERE rfp_run_id=? AND final_rank=1""",
                (playbook_json, run_id),
            )
            if cursor.rowcount != 1:
                raise ValueError(f"Rank 1 supplier not found for {run_id}")
