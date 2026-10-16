from __future__ import annotations

import streamlit as st

from components.header import page_header
from content.learning_topics import TOPICS


def render() -> None:
    page_header("Security Learning Center", "Short beginner lessons that connect to the tools in this app.")
    st.caption("General educational guidance, not a complete security course.")
    for title, points in TOPICS:
        with st.expander(title):
            for p in points:
                st.markdown(f"- {p}")
