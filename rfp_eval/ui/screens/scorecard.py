"""Screen 4: criterion evidence and side-by-side procurement risks."""

from __future__ import annotations

import html

import streamlit as st

from rfp_eval.ui.screens.context import ScreenContext
from rfp_eval.ui.state import get_run_result


def render(ctx: ScreenContext) -> None:
    """Present the saved supplier scorecards and risk excerpts safely."""
    st.header("Scorecard & risk radar")
    result = get_run_result()
    if result is None or result.ranking is None:
        st.info("Run an evaluation to inspect supplier evidence and risks.")
        return
    names = [item.supplier_name for item in result.ranking.suppliers]
    selected = st.selectbox("Supplier scorecard", names, key="scorecard_supplier")
    supplier = next(item for item in result.ranking.suppliers if item.supplier_name == selected)
    rank, absolute, ppi = st.columns(3)
    rank.metric("Overall rank", f"#{supplier.final_rank}")
    absolute.metric("Absolute score", f"{supplier.absolute_score:.2f}")
    ppi.metric("Peer performance index", f"{supplier.ppi:.2f}")
    compared = st.selectbox(
        "Compare a criterion with the peer best",
        supplier.scorecard,
        format_func=lambda row: row.name,
        key="criterion_comparison",
    )
    own, peer = st.columns(2)
    own.metric("Supplier score", f"{compared.score:g} / {compared.max_score}")
    peer.metric("Best peer score", f"{compared.benchmark:g} / {compared.max_score}")
    st.subheader("Criterion score comparison")
    st.caption("Validated supplier scores beside the highest score in this run, by criterion.")
    st.bar_chart(
        [
            {"Criterion": row.name, "Supplier": row.score, "Peer best": row.benchmark}
            for row in supplier.scorecard
        ],
        x="Criterion",
        y=["Supplier", "Peer best"],
        color=["#087f75", "#a8bcb7"],
        horizontal=True,
        stack=False,
        height=300,
    )
    st.dataframe(
        [
            {
                "Criterion": row.name,
                "Score": row.score,
                "Max": row.max_score,
                "Benchmark": row.benchmark,
                "Gap": row.gap,
                "Relative %": row.relative_pct,
                "Weight %": row.weight,
            }
            for row in supplier.scorecard
        ],
        hide_index=True,
        width="stretch",
        column_config={
            "Relative %": st.column_config.ProgressColumn(
                "Relative %",
                min_value=0,
                max_value=100,
                format="%.2f",
            ),
        },
    )
    st.subheader("Evidence & justification")
    for row in supplier.scorecard:
        with st.expander(html.escape(row.name)):
            st.caption("Evidence")
            st.caption(row.evidence or "No excerpt provided.")
            st.caption("Justification")
            st.caption(row.justification)
    st.divider()
    st.subheader("Procurement risk radar")
    supplier_filter, severity_filter = st.columns(2)
    with supplier_filter:
        visible_supplier = st.selectbox(
            "Supplier", ["All suppliers", *names], key="risk_supplier_filter"
        )
    with severity_filter:
        visible_severity = st.selectbox(
            "Severity", ["All severities", "High", "Medium", "Low"], key="risk_severity_filter"
        )
    visible = [
        (name, risk)
        for name in names
        if visible_supplier == "All suppliers" or name == visible_supplier
        for risk in result.evaluations[name].procurement_risks
        if visible_severity == "All severities" or risk.severity == visible_severity
    ]
    st.caption(f"{len(visible)} risk(s) shown")
    st.caption("Risk counts reflect the current supplier and severity filters.")
    st.bar_chart(
        [
            {"Severity": severity, "Risks": sum(risk.severity == severity for _, risk in visible)}
            for severity in ("High", "Medium", "Low")
        ],
        x="Severity",
        y="Risks",
        color="#b55a4b",
        horizontal=True,
        sort=False,
        height=210,
    )
    if not visible:
        st.info("No risks match these filters.")
    for offset in range(0, len(visible), 2):
        for column, (name, risk) in zip(st.columns(2), visible[offset : offset + 2], strict=False):
            with column, st.container(border=True):
                st.caption(f"{risk.severity.upper()} · {risk.risk_category}")
                st.text(name)
                st.caption(risk.issue)
                with st.expander("View proposal excerpt"):
                    st.caption(risk.verbatim_excerpt or "No excerpt provided.")
