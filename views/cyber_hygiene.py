"""Cyber Hygiene: practical, beginner-friendly security habits per operating system.

Static educational content (content/cyber_hygiene.py). Nothing here calls a network
service, reads user input or writes session state. Streamlit columns stack into one
column on narrow screens, which gives the required mobile layout without custom CSS.
All text is escaped before it goes into HTML.
"""

from __future__ import annotations

from html import escape

import streamlit as st

from components.header import page_header
from content.cyber_hygiene import (DOCS_CHECKED, GENERAL_NOTE, SECTIONS, Item,
                                   OsSection)


def _card(item: Item) -> None:
    st.markdown(
        f'<div class="cs-card"><h4>{escape(item.title)}</h4>'
        f'<div class="cs-muted"><strong>What it is:</strong> {escape(item.what)}<br>'
        f'<strong>Why it matters:</strong> {escape(item.why)}</div></div>',
        unsafe_allow_html=True,
    )


def _render_item(item: Item) -> None:
    _card(item)
    with st.expander("How to enable, and our recommendation"):
        st.markdown("**How to enable**")
        st.markdown("\n".join(f"{n}. {step}" for n, step in enumerate(item.steps, 1)))
        st.markdown(f"**Security recommendation:** {item.tip}")
        if item.note:
            st.caption(f"Availability: {item.note}")
    if item.doc is not None:
        st.link_button(f"📘 Official docs · {item.doc.label}", item.doc.url)
    else:
        st.caption("No official documentation link is shown for this tip.")


def _render_section(section: OsSection) -> None:
    st.write(section.intro)
    (st.warning if section.notice_tone == "warning" else st.info)(section.notice)
    items = section.items
    for start in range(0, len(items), 2):
        for col, item in zip(st.columns(2), items[start:start + 2]):
            with col:
                _render_item(item)


def render() -> None:
    page_header("Cyber Hygiene",
                "Practical security habits for Android, Windows, iOS and macOS.")
    st.caption(GENERAL_NOTE)
    st.caption(f"Official documentation links were checked on {DOCS_CHECKED}. Vendors reorganize their help "
               "pages, so a link may move.")
    tabs = st.tabs([f"{s.icon} {s.title}" for s in SECTIONS])
    for tab, section in zip(tabs, SECTIONS):
        with tab:
            _render_section(section)
