"""Reusable safe presentation fragments."""

from __future__ import annotations

import streamlit as st

from rfp_eval.ui.readiness import Readiness


def render_readiness(readiness: Readiness) -> None:
    """Show all blockers and nonblocking upload warnings."""
    if readiness.ready:
        st.success("Ready to evaluate")
    else:
        for message in readiness.blocking:
            st.warning(message)
    for message in readiness.warnings:
        st.info(message)
