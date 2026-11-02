"""Create and seed the local SQLite database."""

from __future__ import annotations

import os
from pathlib import Path

from rfp_eval.db.schema import init_and_seed_db


def main() -> None:
    """Run the same idempotent setup used by the application."""
    init_and_seed_db(Path(os.getenv("RFP_DB_PATH", "data/rfp_eval.db")))


if __name__ == "__main__":
    main()
