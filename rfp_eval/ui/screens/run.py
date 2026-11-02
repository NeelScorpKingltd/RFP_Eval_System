"""Screen 3: evaluation action, live tracker, ranking, and sensitivity."""

from __future__ import annotations

from datetime import UTC, datetime

import streamlit as st

from rfp_eval.domain.errors import ConfigError, GateViolation, LLMAuthError
from rfp_eval.domain.models import RankedSupplier, RunResult
from rfp_eval.llm.factory import get_llm_client
from rfp_eval.orchestration.runner import Deps, run_evaluation
from rfp_eval.orchestration.state import RunRequest
from rfp_eval.services.sensitivity import recompute
from rfp_eval.ui.components import render_readiness
from rfp_eval.ui.readiness import assess_readiness
from rfp_eval.ui.reporter import StreamlitProgressReporter
from rfp_eval.ui.screens.context import ScreenContext
from rfp_eval.ui.state import get_cache, get_drafts, get_run_result, set_run_result


def _leaderboard(suppliers: list[RankedSupplier]) -> None:
    """Render the required leaderboard columns with numeric progress bars."""
    rows = [
        {
            "Rank": item.final_rank,
            "Supplier": item.supplier_name,
            "Absolute Score": item.absolute_score,
            "PPI": item.ppi,
            "Submission Date": item.submission_date.isoformat(),
            "Experience Rating": item.experience_rating,
        }
        for item in suppliers
    ]
    st.dataframe(
        rows,
        hide_index=True,
        width="stretch",
        column_config={
            "Absolute Score": st.column_config.ProgressColumn(
                "Absolute Score", min_value=0, max_value=100, format="%.2f"
            ),
            "PPI": st.column_config.ProgressColumn(
                "PPI", min_value=0, max_value=100, format="%.2f"
            ),
        },
    )


def _simulator(result: RunResult) -> None:
    """Recompute rankings from stored scores when weight sliders change."""
    if result.ranking is None:
        return
    with st.expander("What-If weight simulator", expanded=False):
        st.caption("Adjust weights to explore rank movement. The baseline run stays saved.")
        slider_values = {
            criterion.criterion_id: st.slider(
                criterion.name,
                0.0,
                100.0,
                float(criterion.weight),
                1.0,
                key=f"sim_weight_{result.rfp_run_id}_{criterion.criterion_id}",
            )
            for criterion in result.active_criteria
        }
        simulation = recompute(result, slider_values)
        st.caption("Weights are normalised to 100% for this comparison.")
        rows = []
        for item in simulation.ranking.suppliers:
            original = item.final_rank + simulation.rank_deltas[item.supplier_name]
            movement = (
                f"{'⬆️' if item.final_rank < original else '⬇️'} #{original} to #{item.final_rank}"
                if original != item.final_rank
                else "No change"
            )
            rows.append(
                {
                    "Rank": item.final_rank,
                    "Supplier": item.supplier_name,
                    "PPI": item.ppi,
                    "Movement": movement,
                }
            )
        st.dataframe(rows, hide_index=True, width="stretch")


def render(ctx: ScreenContext) -> None:
    """Gate Evaluate, then show a persisted baseline and optional simulation."""
    st.header("Run & leaderboard")
    read_only = int(st.session_state.get("workflow_stage", 1)) >= 4
    if read_only:
        st.caption("Saved run · review only")
    else:
        drafts = get_drafts()
        readiness = assess_readiness(
            ctx.criteria_repo.list_all(),
            drafts,
            ctx.llm_settings is not None,
        )
        render_readiness(readiness)
    if not read_only and st.button(
        "Evaluate", type="primary", disabled=not readiness.ready, key="evaluate"
    ):
        reporter = None
        try:
            if ctx.llm_settings is None:
                raise ConfigError("Select an LLM provider before evaluating.")
            client = get_llm_client(
                ctx.llm_settings.provider,
                ctx.llm_settings.api_key,
                ctx.llm_settings.model,
            )
            dependencies = Deps(
                criteria_repo=ctx.criteria_repo,
                run_repo=ctx.run_repo,
                result_repo=ctx.result_repo,
                llm=client,
                memory_cache=get_cache(),
                clock=lambda: datetime.now(UTC),
            )
            request = RunRequest(
                suppliers=[draft.to_input() for draft in drafts if draft.document is not None],
                fault_mode=ctx.fault_mode,
            )
            reporter = StreamlitProgressReporter()
            result = run_evaluation(request, dependencies, reporter)
            set_run_result(result)
        except (ConfigError, GateViolation, LLMAuthError, RuntimeError, ValueError) as error:
            if reporter is not None:
                reporter.failed()
            st.error(str(error))
    displayed = get_run_result()
    if displayed is None:
        st.info("Complete setup and run an evaluation to see the leaderboard.")
        return
    st.caption(f"Showing saved run {displayed.rfp_run_id}")
    if displayed.ranking is None:
        st.error("This run did not produce a ranking.")
        for warning in displayed.validation_warnings:
            st.text(warning)
        return
    if displayed.cache_stats.fallbacks:
        st.warning(
            f"{displayed.cache_stats.fallbacks} supplier evaluation(s) used fallback scores. "
            "Review warnings before relying on this ranking."
        )
    st.subheader("Baseline ranking")
    if len(displayed.ranking.suppliers) > 1:
        leader, runner_up = displayed.ranking.suppliers[:2]
        first, second = st.columns(2)
        first.metric("Leader PPI", f"{leader.ppi:.2f}")
        first.caption(leader.supplier_name)
        second.metric("Runner-up PPI", f"{runner_up.ppi:.2f}")
        second.caption(runner_up.supplier_name)
    _leaderboard(displayed.ranking.suppliers)
    _simulator(displayed)
    if not read_only and st.button("Continue to scorecards", key="continue_scorecards"):
        st.session_state["workflow_stage"] = 4
        st.session_state["workflow_view"] = 4
        st.rerun()
