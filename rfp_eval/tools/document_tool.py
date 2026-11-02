"""Bounded PDF extraction and security preflight."""

from __future__ import annotations

import hashlib

import fitz

from rfp_eval.config import (
    MAX_PDF_MB,
    MAX_PDF_PAGES,
    MAX_SOURCE_CHARS,
    MIN_TEXT_CHARS,
    STRIP_HIDDEN_TEXT,
)
from rfp_eval.domain.enums import RejectionCode
from rfp_eval.domain.errors import DocumentRejected
from rfp_eval.domain.models import InjectionFinding, SanitizedDocument
from rfp_eval.security.injection_scanner import scan_for_injection


def _page_text(page: fitz.Page) -> tuple[str, list[InjectionFinding]]:
    """Extract visible spans and flag white or tiny text."""
    pieces: list[str] = []
    findings: list[InjectionFinding] = []
    page_data = page.get_text("dict")
    for block in page_data.get("blocks", []):
        for line in block.get("lines", []):
            visible: list[str] = []
            for span in line.get("spans", []):
                value = str(span.get("text", ""))
                hidden = span.get("color") == 0xFFFFFF or float(span.get("size", 0)) < 1.5
                if hidden and value.strip():
                    findings.append(
                        InjectionFinding(
                            kind="hidden_text",
                            pattern="white_or_tiny_span",
                            snippet=value[:120].replace("<", "&lt;").replace(">", "&gt;"),
                            page=page.number + 1,
                        )
                    )
                    if not STRIP_HIDDEN_TEXT:
                        visible.append(value)
                elif value:
                    visible.append(value)
            if visible:
                pieces.append("".join(visible))
    return "\n".join(pieces), findings


def sanitize_pdf(supplier_name: str, filename: str, data: bytes) -> SanitizedDocument:
    """Check size, format, encryption, pages, and visible text; raise DocumentRejected."""
    if len(data) > MAX_PDF_MB * 1024 * 1024:
        raise DocumentRejected(RejectionCode.TOO_LARGE, f"{filename}: exceeds 10 MB limit.")
    if not data.startswith(b"%PDF"):
        raise DocumentRejected(RejectionCode.NOT_A_PDF, f"{filename}: not a valid PDF.")
    try:
        document = fitz.open(stream=data, filetype="pdf")
    except (fitz.FileDataError, ValueError) as exc:
        raise DocumentRejected(RejectionCode.NOT_A_PDF, f"{filename}: not a valid PDF.") from exc
    try:
        if document.needs_pass:
            raise DocumentRejected(RejectionCode.ENCRYPTED, f"{filename}: encrypted PDF.")
        if document.page_count > MAX_PDF_PAGES:
            raise DocumentRejected(
                RejectionCode.TOO_MANY_PAGES,
                f"{filename}: {document.page_count} pages exceeds 15-page limit.",
            )
        pages: list[str] = []
        findings: list[InjectionFinding] = []
        for page_number, page in enumerate(document, 1):
            text, hidden = _page_text(page)
            pages.append(f"--- page {page_number} ---\n{text}")
            findings.extend(hidden)
            findings.extend(scan_for_injection(text, page_number))
        source = "\n\n".join(pages)
        if len("".join(page.split("\n", 1)[-1] for page in pages).strip()) <= MIN_TEXT_CHARS:
            raise DocumentRejected(RejectionCode.NO_TEXT, f"{filename}: no extractable text.")
        return SanitizedDocument(
            supplier_name=supplier_name,
            text=source[:MAX_SOURCE_CHARS],
            page_count=document.page_count,
            size_bytes=len(data),
            pdf_sha256=hashlib.sha256(data).hexdigest(),
            findings=findings,
        )
    finally:
        document.close()
