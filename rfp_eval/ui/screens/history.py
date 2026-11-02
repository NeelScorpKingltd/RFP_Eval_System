"""Sidebar-accessible history of persisted evaluation runs."""

from __future__ import annotations

import streamlit as st

from rfp_eval.domain.enums import RunStatus
from rfp_eval.services.run_loader import load_run
from rfp_eval.ui.screens.context import ScreenContext
from rfp_eval.ui.state import set_run_result


def render(ctx: ScreenContext) -> None:
    """List saved runs and restore a completed one without provider calls."""
    st.header("Previous runs")
    runs = ctx.run_repo.list_recent()
    if not runs:
        st.info("No saved evaluations yet.")
        return
    for run in runs:
        with st.container(border=True):
            st.text(run.rfp_run_id)
            st.caption(f"{run.created_at:%Y-%m-%d %H:%M} UTC · {run.status.value}")
            if run.status == RunStatus.COMPLETED and st.button(
                "Load results", key=f"load_{run.rfp_run_id}"
            ):
                set_run_result(load_run(run.rfp_run_id, ctx.run_repo, ctx.result_repo))
                st.session_state["workflow_stage"] = 4
                st.session_state["workflow_view"] = 4
                st.session_state["show_history"] = False
                st.rerun()
