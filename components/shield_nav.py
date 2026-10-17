"""Shield toggle + custom navigation drawer (application view only).

Behavior
- The shield button (fixed, top-left) flips st.session_state
  ["cybershield_sidebar_open"] via an on_click callback, so Streamlit's single
  automatic rerun updates the UI: no st.rerun(), no JavaScript.
- The drawer is rendered only while open. Choosing a page runs the `navigate`
  callback: sets the existing "page" key and closes the drawer.
- The active page's button gets a different widget key (cs_navitem_active_*),
  which the CSS uses for the highlight. It is also the native "primary" type
  and its tooltip says "Current page", so the state is not conveyed by color
  alone.
- Not rendered on the landing page (streamlit_app.py returns before this).
"""

from __future__ import annotations

from html import escape

import streamlit as st

from components import nav_state
from components.compat import BUTTON_STRETCH
from components.shield_nav_css import (DRAWER_KEY, ITEM_ACTIVE_PREFIX, ITEM_PREFIX,
                                       TOGGLE_BOX_KEY, TOGGLE_BTN_KEY, shield_nav_css)
from config import APP_NAME


def _toggle() -> None:
    nav_state.toggle_sidebar(st.session_state)


def _select(page: str) -> None:
    nav_state.navigate(st.session_state, page)


def render_shield_nav(active_page: str) -> None:
    st.session_state.setdefault(nav_state.SIDEBAR_KEY, nav_state.DEFAULT_SIDEBAR_OPEN)
    st.markdown(shield_nav_css(), unsafe_allow_html=True)
    is_open = nav_state.is_sidebar_open(st.session_state)

    with st.container(key=TOGGLE_BOX_KEY):
        st.button("🛡️", key=TOGGLE_BTN_KEY, on_click=_toggle,
                  help="Close navigation" if is_open else "Open navigation")

    if not is_open:
        return

    with st.container(key=DRAWER_KEY):
        st.markdown(
            f'<div class="cs-d-head"><div class="cs-d-brand">{escape(APP_NAME)}</div>'
            '<div class="cs-d-tag">Intelligent Security. Clear Insights.</div></div>',
            unsafe_allow_html=True,
        )
        for group, modules in nav_state.nav_groups():
            st.markdown(f'<div class="cs-d-group">{escape(group)}</div>', unsafe_allow_html=True)
            for m in modules:
                active = m.key == active_page
                st.button(
                    f"{m.icon}  {m.title}",
                    key=f"{ITEM_ACTIVE_PREFIX if active else ITEM_PREFIX}{m.key}",
                    on_click=_select, args=(m.key,),
                    type="primary" if active else "secondary",
                    help="Current page" if active else None,
                    **BUTTON_STRETCH,
                )
        st.markdown('<div class="cs-d-foot">Educational toolkit. Results are guidance, not guarantees.</div>',
                    unsafe_allow_html=True)
