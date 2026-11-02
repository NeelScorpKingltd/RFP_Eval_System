"""FR-DEL-03 generated synthetic and edge-case PDF fixtures."""

from __future__ import annotations

from pathlib import Path

import fitz

from rfp_eval.domain.enums import RejectionCode
from rfp_eval.domain.errors import DocumentRejected
from rfp_eval.tools.document_tool import sanitize_pdf

ROOT = Path(__file__).resolve().parents[2] / "sample_data"


def test_fr_del_03_four_proposals_have_required_sections() -> None:
    expected = (
        "Executive Summary and Requirement Understanding",
        "Proposed Solution and Approach",
        "Timeline, Team and Milestones",
        "Price Table and Assumptions",
        "Security, Compliance and Risk Controls",
        "Support Model, Experience and References",
    )
    files = sorted((ROOT / "proposals").glob("*.pdf"))
    assert len(files) == 4
    for file in files:
        with fitz.open(file) as pdf:
            assert 2 <= pdf.page_count <= 4
            text = "\n".join(page.get_text() for page in pdf)
        assert all(section in text for section in expected)
        assert sanitize_pdf(file.stem, file.name, file.read_bytes()).text


def test_fr_sup_02_generated_image_only_fixture_rejected() -> None:
    file = ROOT / "edge_cases" / "image_only.pdf"
    try:
        sanitize_pdf("Image", file.name, file.read_bytes())
    except DocumentRejected as error:
        assert error.code == RejectionCode.NO_TEXT
    else:
        raise AssertionError("Image-only PDF was accepted")
