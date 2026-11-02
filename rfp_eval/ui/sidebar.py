"""Provider selection, BYOK secret input, and fault controls."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping

import streamlit as st
from pydantic import BaseModel

from rfp_eval.domain.enums import Provider
from rfp_eval.domain.errors import ConfigError
from rfp_eval.llm.base import LLMSettings
from rfp_eval.llm.factory import resolve_settings
from rfp_eval.ui.key_check import probe_llm


class SidebarConfig(BaseModel):
    settings: LLMSettings | None
    fault_mode: bool


def _demo_secrets() -> Mapping[str, str]:
    """Read only the two configured demo secrets, tolerating an absent file."""
    try:
        provider = st.secrets.get("DEFAULT_LLM_PROVIDER", "")
        key = st.secrets.get("DEFAULT_LLM_API_KEY", "")
    except FileNotFoundError:
        return {}
    return {"DEFAULT_LLM_PROVIDER": str(provider), "DEFAULT_LLM_API_KEY": str(key)}


def render_sidebar() -> SidebarConfig:
    """Return a secret-bearing configuration held only in session memory."""
    with st.sidebar:
        st.title("Evaluation setup")
        st.caption("Choose where proposal text is evaluated.")
        provider = st.selectbox(
            "LLM provider",
            list(Provider),
            format_func=lambda option: option.value.title(),
            key="llm_provider",
        )
        key = st.text_input("API key", type="password", key="llm_api_key")
        st.divider()
        secrets = _demo_secrets()
        demo_available = bool(
            secrets.get("DEFAULT_LLM_PROVIDER") and secrets.get("DEFAULT_LLM_API_KEY")
        )
        use_demo = st.checkbox(
            "Use Free Default Demo Model",
            disabled=not demo_available,
            key="use_demo",
        )
        if not demo_available:
            st.caption("Demo model unavailable: no shared key is configured.")
        fault = st.checkbox(
            "Simulate Malformed LLM Output",
            disabled=not (use_demo or bool(key)),
            key="fault_mode",
        )
        if fault:
            st.warning("Fault simulation is active. This run will skip the cache.")
        try:
            settings = resolve_settings(use_demo, provider, key, secrets)
        except ConfigError:
            settings = None
        if settings is not None:
            signature = hashlib.sha256(
                (
                    settings.provider.value
                    + "\0"
                    + settings.model
                    + "\0"
                    + settings.api_key.get_secret_value()
                ).encode()
            ).hexdigest()
            if st.session_state.get("key_check_signature") != signature:
                with st.spinner("Checking provider connection…"):
                    valid, message = probe_llm(settings)
                st.session_state["key_check_signature"] = signature
                st.session_state["key_check_status"] = (valid, message)
            valid, message = st.session_state["key_check_status"]
            if valid:
                st.success("● Live · " + message)
            else:
                st.error("● Unavailable · " + message)
                if st.button("Retry connection", key="retry_key_check"):
                    st.session_state.pop("key_check_signature", None)
                    st.rerun()
        else:
            st.session_state.pop("key_check_signature", None)
            st.session_state.pop("key_check_status", None)
        verified = settings is not None and st.session_state.get("key_check_status", (False, ""))[0]
        return SidebarConfig(
            settings=settings if verified else None,
            fault_mode=bool(fault and verified),
        )
