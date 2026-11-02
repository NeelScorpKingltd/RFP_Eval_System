"""Screen 1: controlled rubric editing with an explicit Save gate."""

from __future__ import annotations

import streamlit as st
from pydantic import ValidationError

from rfp_eval.domain.models import Criterion
from rfp_eval.tools.weight_gate import check_weight_gate
from rfp_eval.ui.components import render_readiness
from rfp_eval.ui.readiness import assess_readiness
from rfp_eval.ui.screens.context import ScreenContext
from rfp_eval.ui.state import get_drafts


def render(ctx: ScreenContext) -> None:
    """Render criteria from SQLite and persist only validated explicit edits."""
    st.header("Evaluation criteria")
    st.caption(
        "Set the weights and review the rubric before evaluating. Active weights must total 100%."
    )
    criteria = ctx.criteria_repo.list_all()
    rows = [
        {
            "criterion_id": item.criterion_id,
            "name": item.name,
            "weight": item.weight,
            "is_active": item.is_active,
        }
        for item in criteria
    ]
    st.caption("Weights and active status")
    edited = st.data_editor(
        rows,
        key="criteria_editor",
        hide_index=True,
        num_rows="fixed",
        column_config={
            "criterion_id": st.column_config.NumberColumn("ID", disabled=True),
            "name": st.column_config.TextColumn("Criterion", disabled=True),
            "weight": st.column_config.NumberColumn(
                "Weight %", min_value=0.0, max_value=100.0, step=0.01
            ),
            "is_active": st.column_config.CheckboxColumn("Active"),
        },
        width="stretch",
    )
    with st.expander("View assessment details and edit descriptions"):
        st.caption(
            "Criterion names and maximum scores are fixed. Unlock descriptions to edit them."
        )
        unlock = st.checkbox("Unlock 'What to assess' editing", key="unlock_descriptions")
        descriptions: dict[int, str] = {}
        for item in criteria:
            st.text(f"{item.criterion_id}. {item.name}")
            st.caption(f"Maximum score: {item.max_score}")
            if unlock:
                descriptions[item.criterion_id] = st.text_area(
                    "What to assess",
                    value=item.description,
                    key=f"description_{item.criterion_id}",
                )
            else:
                st.text(item.description)
        if unlock:
            st.caption("Save criteria to apply description changes to future evaluations.")
    try:
        proposed = [
            Criterion.model_validate(
                {
                    **item.model_dump(),
                    "weight": row["weight"],
                    "is_active": row["is_active"],
                    "description": descriptions.get(item.criterion_id, item.description),
                }
            )
            for item, row in zip(criteria, edited, strict=True)
        ]
        if any(not item.name.strip() or not item.description.strip() for item in proposed):
            raise ValueError("Criterion name and description are required.")
        gate = check_weight_gate(proposed)
        if not gate.valid:
            st.warning(gate.message)
    except (ValidationError, ValueError) as exc:
        proposed = []
        st.error(str(exc))
    valid = bool(proposed and check_weight_gate(proposed).valid)
    if st.button("Save criteria", type="primary", disabled=not valid, key="save_criteria"):
        ctx.criteria_repo.save(proposed)
        st.session_state["workflow_stage"] = 2
        st.session_state["workflow_view"] = 2
        st.rerun()
    st.divider()
    st.caption("Run readiness")
    render_readiness(
        assess_readiness(
            proposed or criteria,
            get_drafts(),
            ctx.llm_settings is not None,
        )
    )
