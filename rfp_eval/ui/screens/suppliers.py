"""Screen 2: proposal upload, metadata, and preflight feedback."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

import streamlit as st

from rfp_eval.domain.errors import DocumentRejected
from rfp_eval.tools.document_tool import sanitize_pdf
from rfp_eval.ui.components import render_readiness
from rfp_eval.ui.readiness import assess_readiness
from rfp_eval.ui.screens.context import ScreenContext
from rfp_eval.ui.state import SupplierDraft, get_drafts, set_drafts

_SAMPLE = Path(__file__).resolve().parents[3] / "sample_data"


def _draft(
    filename: str,
    data: bytes,
    *,
    name: str = "",
    submitted: date | None = None,
    rating: float | None = None,
) -> SupplierDraft:
    identifier = hashlib.sha256(filename.encode() + b"\0" + data).hexdigest()[:16]
    try:
        document = sanitize_pdf(name or filename, filename, data)
        rejection = None
    except DocumentRejected as error:
        document = None
        rejection = str(error)
    return SupplierDraft(
        draft_id=identifier,
        pdf_name=filename,
        pdf_bytes=data,
        supplier_name=name,
        submission_date=submitted,
        experience_rating=rating,
        document=document,
        rejection=rejection,
    )


def _load_demo() -> list[SupplierDraft]:
    metadata = json.loads((_SAMPLE / "suppliers.json").read_text(encoding="utf-8"))
    return [
        _draft(
            item["pdf_name"],
            (_SAMPLE / "proposals" / item["pdf_name"]).read_bytes(),
            name=item["supplier_name"],
            submitted=date.fromisoformat(item["submission_date"]),
            rating=float(item["experience_rating"]),
        )
        for item in metadata
    ]


def render(ctx: ScreenContext) -> None:
    """Accept PDF bytes once and show each supplier's readiness details."""
    st.header("Supplier proposals")
    st.caption("Upload PDFs and complete the metadata for each usable proposal.")
    if st.button("Load demo suppliers", key="load_demo"):
        set_drafts(_load_demo())
    uploads = st.file_uploader(
        "Upload proposal PDFs",
        type=["pdf"],
        accept_multiple_files=True,
        key="proposal_uploads",
    )
    drafts = get_drafts()
    existing = {draft.pdf_name for draft in drafts}
    for uploaded in uploads or []:
        if uploaded.name not in existing:
            drafts.append(_draft(uploaded.name, uploaded.getvalue()))
            existing.add(uploaded.name)
    for draft in drafts:
        with st.container(border=True):
            st.caption(draft.pdf_name)
            if draft.rejection:
                st.error(draft.rejection)
                continue
            if draft.document is not None:
                st.success(f"PDF accepted · {draft.document.page_count} page(s)")
                with st.expander("Sanitisation details"):
                    st.text(f"Size: {draft.document.size_bytes:,} bytes")
                    st.text(f"Pages: {draft.document.page_count}")
                    st.text(f"Extracted characters: {len(draft.document.text):,}")
                    st.caption("Security findings are listed below when detected.")
            first, second, third = st.columns([2, 1.2, 1.2])
            with first:
                draft.supplier_name = st.text_input(
                    "Supplier name",
                    value=draft.supplier_name,
                    key=f"supplier_name_{draft.draft_id}",
                )
            with second:
                submitted = st.date_input(
                    "Submission date",
                    value=draft.submission_date,
                    key=f"submission_date_{draft.draft_id}",
                )
                draft.submission_date = submitted if isinstance(submitted, date) else None
            with third:
                rating = st.number_input(
                    "Experience rating (0-5)",
                    min_value=0.0,
                    max_value=5.0,
                    value=draft.experience_rating,
                    step=0.1,
                    key=f"experience_rating_{draft.draft_id}",
                )
                draft.experience_rating = float(rating) if rating is not None else None
            if draft.document and draft.document.findings:
                with st.expander("Security findings"):
                    for finding in draft.document.findings:
                        st.text(f"Page {finding.page}: {finding.kind}")
                        st.code(finding.snippet)
    set_drafts(drafts)
    st.divider()
    render_readiness(
        assess_readiness(
            ctx.criteria_repo.list_all(),
            drafts,
            ctx.llm_settings is not None,
        )
    )
    supplier_ready = assess_readiness(ctx.criteria_repo.list_all(), drafts, True)
    if st.button(
        "Save suppliers & continue",
        type="primary",
        disabled=bool(supplier_ready.blocking),
        key="save_suppliers",
    ):
        st.session_state["workflow_stage"] = 3
        st.session_state["workflow_view"] = 3
        st.rerun()
