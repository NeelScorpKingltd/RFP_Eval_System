"""Idempotent database creation and default criterion seeding."""

from __future__ import annotations

from pathlib import Path

from rfp_eval.db.connection import connection

DEFAULT_CRITERIA = (
    (1, "Technical Capability", "Architecture, integration, and technical fit", 30.0, 10, 1),
    (2, "Implementation Approach", "Plan, timeline, delivery team, and milestones", 20.0, 10, 1),
    (3, "Commercial Value", "Price, terms, assumptions, and total cost", 20.0, 10, 1),
    (4, "Security and Compliance", "Security controls and compliance evidence", 20.0, 10, 1),
    (
        5,
        "Support and Experience",
        "Support model, references, and relevant experience",
        10.0,
        10,
        1,
    ),
)


def init_and_seed_db(path: Path) -> None:
    """Create the frozen tables and seed five criteria when none exist."""
    with connection(path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS evaluation_criteria (
                criterion_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                weight REAL NOT NULL,
                max_score INTEGER NOT NULL,
                is_active INTEGER DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS rfp_runs (
                rfp_run_id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS supplier_results (
                rfp_run_id TEXT NOT NULL,
                supplier_name TEXT NOT NULL,
                submission_date TEXT NOT NULL,
                experience_rating REAL NOT NULL,
                absolute_score REAL NOT NULL,
                ppi REAL NOT NULL,
                final_rank INTEGER NOT NULL,
                result_json TEXT NOT NULL,
                negotiation_playbook_json TEXT,
                cache_hash TEXT,
                PRIMARY KEY (rfp_run_id, supplier_name),
                FOREIGN KEY (rfp_run_id) REFERENCES rfp_runs(rfp_run_id)
            );
            CREATE INDEX IF NOT EXISTS idx_supplier_results_cache_hash
                ON supplier_results(cache_hash);
            """
        )
        count = conn.execute("SELECT COUNT(*) FROM evaluation_criteria").fetchone()[0]
        if count == 0:
            conn.executemany(
                "INSERT INTO evaluation_criteria VALUES (?, ?, ?, ?, ?, ?)", DEFAULT_CRITERIA
            )
