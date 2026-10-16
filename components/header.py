from __future__ import annotations

from html import escape

import streamlit as st

from config import APP_NAME, APP_TAGLINE


def page_header(title: str, subtitle: str = "") -> None:
    st.title(title)
    if subtitle:
        st.caption(subtitle)


def hero() -> None:
    st.markdown(
        f'<div class="cs-hero"><h1>🛡️ {escape(APP_NAME)}</h1><p>{escape(APP_TAGLINE)}</p></div>',
        unsafe_allow_html=True,
    )
