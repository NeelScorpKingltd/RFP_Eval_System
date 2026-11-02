"""Screen 5: run details and negotiation entry point."""

from __future__ import annotations

import html

import streamlit as st

from rfp_eval.domain.errors import ConfigError, LLMAuthError, LLMOutputError, LLMTransportError
from rfp_eval.domain.models import WinnerNegotiationPlaybook
from rfp_eval.llm.factory import get_llm_client
from rfp_eval.services.briefing import render_negotiation_briefing
from rfp_eval.services.export import build_unified_export
from rfp_eval.services.negotiation import generate_and_store_playbook
from rfp_eval.ui.screens.context import ScreenContext
from rfp_eval.ui.state import get_run_result


def render(ctx: ScreenContext) -> None:
    """Show audit details and a downloadable unified JSON record."""
    st.header("Playbook & run details")
    result = get_run_result()
    if result is None or result.ranking is None:
        st.info("Complete an evaluation to review the winner and audit record.")
        return
    winner = result.ranking.suppliers[0]
    st.markdown(
        '<div class="winner-banner"><strong>Rank 1 supplier</strong><br>'
        + html.escape(winner.supplier_name)
        + f" · PPI {winner.ppi:.2f}</div>",
        unsafe_allow_html=True,
    )
    st.subheader("BAFO negotiation playbook")
    stored = next(
        (item for item in ctx.result_repo.list_for_run(result.rfp_run_id) if item.final_rank == 1),
        None,
    )
    playbook = (
        WinnerNegotiationPlaybook.model_validate_json(stored.negotiation_playbook_json)
        if stored is not None and stored.negotiation_playbook_json
        else None
    )
    if st.button(
        f"✨ Generate BAFO Negotiation Playbook for {html.escape(winner.supplier_name)}",
        disabled=ctx.llm_settings is None,
        type="primary",
        key="generate_playbook",
    ):
        try:
            if ctx.llm_settings is None:
                raise ConfigError("Select an LLM provider before generating a playbook.")
            client = get_llm_client(
                ctx.llm_settings.provider, ctx.llm_settings.api_key, ctx.llm_settings.model
            )
            playbook = generate_and_store_playbook(result, client, ctx.result_repo)
            st.session_state["playbook"] = playbook
            st.success("Playbook saved for the Rank 1 supplier.")
        except (ConfigError, LLMAuthError, LLMTransportError, LLMOutputError, ValueError) as error:
            st.error(str(error))
    if ctx.llm_settings is None:
        st.caption("Configure a provider to generate a playbook on demand.")
    if playbook is not None:
        st.caption("Negotiation stance")
        with st.container(border=True):
            st.caption(playbook.stance)
        st.subheader("Negotiation priorities")
        for index, point in enumerate(playbook.negotiation_matrix, 1):
            with st.container(border=True):
                st.caption(f"PRIORITY {index} · {point.category}")
                vulnerability, concession = st.columns(2)
                with vulnerability:
                    st.caption("Proposal vulnerability")
                    st.caption(point.proposal_vulnerability)
                with concession:
                    st.caption("Target concession")
                    st.caption(point.target_concession)
                with st.expander("Meeting question"):
                    st.caption(point.scripted_meeting_question)
        with st.expander("Leverage areas and walkaway risks"):
            for item in playbook.leverage_areas:
                st.caption(item)
            for item in playbook.walkaway_risks:
                st.caption(item)
        st.download_button(
            "Download Negotiation Briefing Doc (Markdown)",
            render_negotiation_briefing(playbook),
            file_name=f"{result.rfp_run_id}-bafo.md",
            mime="text/markdown",
        )
    st.divider()
    st.subheader("Run record")
    st.text(f"Run ID: {result.rfp_run_id}")
    st.text(f"Status: {result.status.value}")
    st.text(
        f"Cache hits: {result.cache_stats.hits} · misses: {result.cache_stats.misses} "
        f"· LLM calls: {result.cache_stats.llm_calls} · fallbacks: {result.cache_stats.fallbacks}"
    )
    with st.expander("Validation warnings"):
        if not result.validation_warnings:
            st.caption("None")
        for warning in result.validation_warnings:
            st.text(warning)
    with st.expander("Ranking explanations"):
        for explanation in result.ranking.tie_break_explanations:
            st.text(explanation)
    try:
        export = build_unified_export(result.rfp_run_id, ctx.run_repo, ctx.result_repo)
    except ValueError as error:
        st.error(str(error))
    else:
        st.download_button(
            "Download Unified Run JSON",
            export,
            file_name=f"{result.rfp_run_id}.json",
            mime="application/json",
        )
