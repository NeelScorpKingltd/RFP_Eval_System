"""Generate four fictional procurement proposals with PyMuPDF."""

from __future__ import annotations

import json
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1] / "sample_data"

PROPOSALS = {
    "Apex_Systems": (
        "Apex Systems",
        "2026-10-10",
        4.8,
        "Enterprise architecture with documented integrations and audited controls.",
        "A phased implementation over six months with a dedicated delivery lead.",
        "Premium fixed implementation fee with separately priced support.",
        "SOC 2 controls, encryption, audit logging and incident response evidence.",
        "Named support engineers and references from large enterprises.",
    ),
    "BrightPath_Tech": (
        "BrightPath Tech",
        "2026-10-14",
        3.4,
        "A practical cloud solution with standard API integrations.",
        "Fast three-month rollout, contingent on customer staffing dependencies.",
        "Lowest headline price; travel expenses are passed through to the customer.",
        "Security overview is brief and omits independent compliance evidence.",
        "Business-hour help desk; SLA credits are capped at one month's fees.",
    ),
    "NexaWorks": (
        "NexaWorks",
        "2026-10-12",
        4.5,
        "Flexible integration architecture with a clear migration path.",
        "Detailed workstreams, milestones, acceptance gates and escalation owners.",
        "Competitive fixed fee with transparent assumptions and change control.",
        "Documented encryption, access controls and annual penetration tests.",
        "24-hour support and strong references for similar deployments.",
    ),
    "Orbit_Digital": (
        "Orbit Digital",
        "2026-10-15",
        4.6,
        "Modern platform, but the legacy integration method is still vague.",
        "Four-month schedule with experienced project management.",
        "Mid-range commercial offer with standard payment milestones.",
        "Baseline security controls and a published compliance program.",
        "Experienced support team with several relevant client references.",
    ),
}


def _add_page(document: fitz.Document, heading: str, sections: list[tuple[str, str]]) -> None:
    page = document.new_page()
    page.insert_text((54, 55), heading, fontsize=18)
    y = 100
    for title, body in sections:
        page.insert_text((54, y), title, fontsize=12)
        y += 24
        page.insert_textbox(
            fitz.Rect(54, y, 540, y + 70),
            (body + " " + body).strip(),
            fontsize=10,
        )
        y += 115


def main() -> None:
    """Write repeatable synthetic PDFs and supplier metadata to sample_data."""
    folder = ROOT / "proposals"
    folder.mkdir(parents=True, exist_ok=True)
    metadata: list[dict[str, str | float]] = []
    for filename, data in PROPOSALS.items():
        name, date, rating, technical, plan, price, security, support = data
        document = fitz.open()
        _add_page(
            document,
            name + " — RFP Proposal",
            [
                ("Executive Summary and Requirement Understanding", technical),
                ("Proposed Solution and Approach", technical),
                ("Timeline, Team and Milestones", plan),
            ],
        )
        _add_page(
            document,
            name + " — Commercial and Operations",
            [
                ("Price Table and Assumptions", price),
                ("Security, Compliance and Risk Controls", security),
                ("Support Model, Experience and References", support),
            ],
        )
        document.save(folder / f"{filename}.pdf")
        document.close()
        metadata.append(
            {
                "supplier_name": name,
                "submission_date": date,
                "experience_rating": rating,
                "pdf_name": f"{filename}.pdf",
            }
        )
    (ROOT / "suppliers.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
