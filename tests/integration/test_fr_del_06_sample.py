"""FR-DEL-06 release walkthrough using only the offline fake provider."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.export_sample_run import main


def test_fr_del_06_sample_has_four_ranked_suppliers_and_risk_radar(tmp_path: Path) -> None:
    """The reproducible sample demonstrates the full successful batch path."""
    output = tmp_path / "sample_run.json"
    main(output)
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "COMPLETED"
    assert [item["final_rank"] for item in payload["supplier_rankings"]] == [1, 2, 3, 4]
    assert payload["cache_stats"]["llm_calls"] == 4
    brightpath = next(
        item for item in payload["supplier_rankings"] if item["supplier_name"] == "BrightPath Tech"
    )
    assert len(brightpath["procurement_risks"]) == 3
    assert payload["winner_negotiation_playbook"] == {}
    assert "source_text" not in json.dumps(payload)


def test_fr_del_06_sample_export_is_byte_reproducible(tmp_path: Path) -> None:
    """A second offline run produces exactly the same exported bytes."""
    output = tmp_path / "sample_run.json"
    main(output)
    first = output.read_bytes()
    main(output)
    assert output.read_bytes() == first
