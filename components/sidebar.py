"""Sidebar navigation driven by app_registry. Page choice lives in
st.session_state["page"]; there is no hidden routing."""

from __future__ import annotations

import streamlit as st

from components.compat import BUTTON_STRETCH

import app_registry as reg
from config import APP_NAME


def go_to(page_key: str) -> None:
    if page_key in reg.implemented_keys():
        st.session_state["page"] = page_key


def current_page() -> str:
    page = st.session_state.get("page", reg.DEFAULT_PAGE)
    return page if page in reg.implemented_keys() else reg.DEFAULT_PAGE


def _nav_buttons(page: str, key_prefix: str) -> None:
    """Grouped navigation buttons from the registry, used by the legacy
    Streamlit sidebar (SHOW_DEFAULT_SIDEBAR = True). The custom shield drawer
    lives in components/shield_nav.py."""
    groups: dict[str, list[reg.Module]] = {}
    for module in reg.implemented():
        groups.setdefault(module.group, []).append(module)
    for group, modules in groups.items():
        st.caption(group)
        for m in modules:
            if st.button(f"{m.icon}  {m.title}", key=f"{key_prefix}_{m.key}",
                         **BUTTON_STRETCH,
                         type="primary" if m.key == page else "secondary"):
                st.session_state["page"] = m.key
                st.rerun()


def render_sidebar() -> str:
    page = current_page()
    with st.sidebar:
        st.markdown(f"### 🛡️ {APP_NAME}")
        _nav_buttons(page, key_prefix="nav")
        upcoming = reg.planned()
        if upcoming:
            st.caption("Planned (not available yet)")
            for m in upcoming:
                st.markdown(f"<span class='cs-muted'>{m.icon} {m.title}</span>",
                            unsafe_allow_html=True)
        st.divider()
        st.caption("Educational toolkit. Not a guarantee of safety.")
    return current_page()
