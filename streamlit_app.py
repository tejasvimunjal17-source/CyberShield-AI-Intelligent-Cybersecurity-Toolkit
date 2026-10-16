"""CyberShield AI entry point.

Run locally:  streamlit run streamlit_app.py
"""

from __future__ import annotations

import streamlit as st

import app_registry as reg
from backend.logging_config import get_logger
from components.cyberguide_chat import render_cyberguide
from components.sidebar import render_sidebar
from components.theme import inject_css
from config import APP_NAME, get_app_env
from views import (about, dashboard, file_analyzer, learning_center,
                   qr_analyzer, qr_generator, settings, url_scanner)

logger = get_logger(__name__)

st.set_page_config(page_title=f"{APP_NAME}", page_icon="🛡️", layout="wide",
                   initial_sidebar_state="expanded")

PAGES = {
    "dashboard": dashboard.render,
    "url_scanner": url_scanner.render,
    "file_analyzer": file_analyzer.render,
    "qr_generator": qr_generator.render,
    "qr_analyzer": qr_analyzer.render,
    "learning_center": learning_center.render,
    "settings": settings.render,
    "about": about.render,
}
# Navigation and routing must never drift apart.
assert set(PAGES) == set(reg.implemented_keys()), "app_registry and PAGES are out of sync"


def main() -> None:
    inject_css()
    page = render_sidebar()
    try:
        PAGES[page]()
    except Exception as exc:  # noqa: BLE001 - last-resort safety net
        logger.exception("Unhandled error on page %s", page)
        st.error("Something went wrong on this page. Reload and try again.")
        if get_app_env() != "production":
            st.caption(f"Developer detail: {type(exc).__name__}: {exc}")
    render_cyberguide()


main()
