"""Export a reproducible four-supplier demonstration through the production pipeline."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from rfp_eval.db.repositories import CriteriaRepo, RunRepo, SupplierResultRepo
from rfp_eval.db.schema import init_and_seed_db
from rfp_eval.domain.enums import RunStatus
from rfp_eval.domain.models import SupplierInput
from rfp_eval.llm.fake import FakeLLMClient
from rfp_eval.orchestration.runner import Deps, run_evaluation
from rfp_eval.orchestration.state import RunRequest
from rfp_eval.services.export import build_unified_export
from rfp_eval.tools.cache import MemoryCache

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "sample_data"
SCORES = (
    (9, 7, 5, 9, 8),
    (6, 8, 9, 4, 5),
    (8, 9, 8, 7, 9),
    (6, 7, 7, 7, 9),
)


def _reply(name: str, scores: tuple[int, ...]) -> str:
    """Create a fixed fake LLM reply; production validation and ranking do the math."""
    risks = (
        [
            {
                "risk_category": "Commercial",
                "severity": "Medium",
                "issue": "Travel expenses may increase total cost.",
                "verbatim_excerpt": "travel expenses are passed through to the customer",
            },
            {
                "risk_category": "Security",
                "severity": "High",
                "issue": "Independent compliance evidence is absent.",
                "verbatim_excerpt": "omits independent compliance evidence",
            },
            {
                "risk_category": "SLA",
                "severity": "Medium",
                "issue": "Service credits have a low cap.",
                "verbatim_excerpt": "SLA credits are capped at one month's fees",
            },
        ]
        if name == "BrightPath Tech"
        else []
    )
    return json.dumps(
        {
            "supplier_name": name,
            "overall_summary": f"Synthetic proposal review for {name}.",
            "criteria": [
                {
                    "criterion_id": criterion_id,
                    "score": score,
                    "justification": "Supported by the synthetic proposal.",
                    "evidence": "See the submitted proposal PDF.",
                }
                for criterion_id, score in enumerate(scores, 1)
            ],
            "procurement_risks": risks,
        }
    )


def main(output_path: Path | None = None) -> None:
    """Run the offline sample in a temporary database and write unified JSON."""
    metadata = json.loads((SAMPLE / "suppliers.json").read_text(encoding="utf-8"))
    suppliers = [
        SupplierInput(
            supplier_name=item["supplier_name"],
            submission_date=date.fromisoformat(item["submission_date"]),
            experience_rating=float(item["experience_rating"]),
            pdf_name=item["pdf_name"],
            pdf_bytes=(SAMPLE / "proposals" / item["pdf_name"]).read_bytes(),
        )
        for item in metadata
    ]
    replies = [
        _reply(item["supplier_name"], scores) for item, scores in zip(metadata, SCORES, strict=True)
    ]
    with TemporaryDirectory() as directory:
        db_path = Path(directory) / "sample.db"
        init_and_seed_db(db_path)
        dependencies = Deps(
            criteria_repo=CriteriaRepo(db_path),
            run_repo=RunRepo(db_path),
            result_repo=SupplierResultRepo(db_path),
            llm=FakeLLMClient(replies),
            memory_cache=MemoryCache(),
            clock=lambda: datetime(2026, 10, 30, tzinfo=UTC),
        )
        run = run_evaluation(RunRequest(suppliers=suppliers), dependencies)
        if run.status != RunStatus.COMPLETED:
            raise RuntimeError("Synthetic sample run did not complete")
        export = build_unified_export(
            run.rfp_run_id, dependencies.run_repo, dependencies.result_repo
        )
    (output_path or SAMPLE / "sample_run.json").write_text(export + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
