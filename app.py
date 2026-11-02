"""Thin Streamlit entrypoint for the supplier evaluation workspace."""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from rfp_eval.db.repositories import CriteriaRepo, RunRepo, SupplierResultRepo
from rfp_eval.db.schema import init_and_seed_db
from rfp_eval.ui.screens import criteria, details, history, run, scorecard, suppliers
from rfp_eval.ui.screens.context import ScreenContext
from rfp_eval.ui.sidebar import render_sidebar
from rfp_eval.ui.styles import inject_styles


@st.cache_resource
def _boot(path_text: str) -> None:
    """Initialise the database once without caching repository class instances."""
    init_and_seed_db(Path(path_text))


def main() -> None:
    """Render the shared shell and only the active radio-selected screen."""
    st.set_page_config(page_title="Supplier Review", layout="wide")
    inject_styles()
    path_text = os.getenv("RFP_DB_PATH", "data/rfp_eval.db")
    _boot(path_text)
    path = Path(path_text)
    criteria_repo, run_repo, result_repo = (
        CriteriaRepo(path),
        RunRepo(path),
        SupplierResultRepo(path),
    )
    sidebar = render_sidebar()
    with st.sidebar:
        st.divider()
        if st.button("Previous runs", key="open_history"):
            st.session_state["show_history"] = True
        if st.session_state.get("show_history") and st.button(
            "Return to workflow", key="return_workflow"
        ):
            st.session_state["show_history"] = False
    context = ScreenContext(
        criteria_repo=criteria_repo,
        run_repo=run_repo,
        result_repo=result_repo,
        llm_settings=sidebar.settings,
        fault_mode=sidebar.fault_mode,
    )
    st.markdown(
        '<section class="workspace-hero animated-card">'
        '<span class="eyebrow">SUPPLIER REVIEW / PROCUREMENT WORKSPACE</span>'
        "<h1>Clarity in every decision.</h1>"
        "<p>Compare proposals, explore the evidence, and prepare your next negotiation "
        "with confidence.</p></section>",
        unsafe_allow_html=True,
    )
    if st.session_state.get("show_history", False):
        history.render(context)
        return
    screens = [criteria.render, suppliers.render, run.render, scorecard.render, details.render]
    labels = [
        "1 · Criteria",
        "2 · Suppliers",
        "3 · Run & leaderboard",
        "4 · Scorecard & risks",
        "5 · Playbook & details",
    ]
    stage = int(st.session_state.get("workflow_stage", 1))
    view = int(st.session_state.get("workflow_view", stage))
    columns = st.columns([1, 1, 1.25, 1.25, 1.25, 1])
    for index, (column, label) in enumerate(zip(columns[:5], labels, strict=True), 1):
        with column:
            available = index == stage or (stage == 4 and index in (3, 5))
            marker = "● " if index == view else "✓ " if index < stage else "○ "
            if st.button(
                marker + label,
                key=f"stage_{index}",
                disabled=not available,
                use_container_width=True,
            ):
                st.session_state["workflow_view"] = index
                view = index
    with columns[5]:
        if st.button("Cancel run", key="cancel_run", use_container_width=True):
            for key in list(st.session_state):
                if key.startswith(
                    ("supplier_", "submission_", "experience_", "description_", "sim_weight_")
                ) or key in {
                    "suppliers",
                    "run_result",
                    "playbook",
                    "proposal_uploads",
                    "criteria_editor",
                    "unlock_descriptions",
                }:
                    del st.session_state[key]
            st.session_state["workflow_stage"] = 1
            st.session_state["workflow_view"] = 1
            st.rerun()
    screens[view - 1](context)


if __name__ == "__main__":
    main()
