"""Typed accessors for Streamlit's rerun-backed session state."""

from __future__ import annotations

from datetime import date
from typing import cast

import streamlit as st
from pydantic import BaseModel, Field

from rfp_eval.domain.models import RunResult, SanitizedDocument, SupplierInput
from rfp_eval.tools.cache import MemoryCache


class SupplierDraft(BaseModel):
    draft_id: str
    pdf_name: str
    pdf_bytes: bytes = Field(repr=False, exclude=True)
    supplier_name: str = ""
    submission_date: date | None = None
    experience_rating: float | None = None
    document: SanitizedDocument | None = None
    rejection: str | None = None

    def to_input(self) -> SupplierInput:
        """Convert a complete usable draft into the orchestrator input contract."""
        if self.document is None or self.submission_date is None or self.experience_rating is None:
            raise ValueError("Supplier draft is incomplete")
        return SupplierInput(
            supplier_name=self.supplier_name.strip(),
            submission_date=self.submission_date,
            experience_rating=self.experience_rating,
            pdf_name=self.pdf_name,
            pdf_bytes=self.pdf_bytes,
        )


def get_drafts() -> list[SupplierDraft]:
    """Return the in-memory supplier drafts for this browser session."""
    if "suppliers" not in st.session_state:
        st.session_state["suppliers"] = []
    return cast(list[SupplierDraft], st.session_state["suppliers"])


def set_drafts(drafts: list[SupplierDraft]) -> None:
    """Replace session supplier drafts after an explicit upload or demo load."""
    st.session_state["suppliers"] = drafts


def get_cache() -> MemoryCache:
    """Return a session-scoped evaluation cache."""
    if "eval_cache" not in st.session_state:
        st.session_state["eval_cache"] = MemoryCache()
    return cast(MemoryCache, st.session_state["eval_cache"])


def get_run_result() -> RunResult | None:
    """Return the latest completed or failed run, if any."""
    return st.session_state.get("run_result")


def set_run_result(result: RunResult) -> None:
    """Keep the latest run visible after Streamlit reruns."""
    st.session_state["run_result"] = result
