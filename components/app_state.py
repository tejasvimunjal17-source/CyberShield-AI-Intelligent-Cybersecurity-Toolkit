"""Landing-vs-application state. No Streamlit import: functions take any
dict-like session state, so the logic is unit-testable and the Streamlit
layer stays thin.

Two views:
  "landing"  entry screen (brand bar, hero, features, ...). Default for a
             fresh browser session.
  "app"      the existing application shell (temporary menu, pages,
             CyberGuide AI).

The existing page key ("page") is NOT renamed; this module only decides
which view is shown and, on entry, which page opens first.

Persistence: state lives in st.session_state, which is per browser session.
A browser refresh starts a new session, so the visitor sees the landing page
again. No query parameters are used.
"""

from __future__ import annotations

from collections.abc import MutableMapping

import app_registry as reg

VIEW_KEY = "view"
VIEW_LANDING = "landing"
VIEW_APP = "app"
_VIEWS = (VIEW_LANDING, VIEW_APP)

PAGE_KEY = "page"            # same key components/sidebar.py already uses
GUIDE_OPEN_KEY = "guide_open"  # same key components/cyberguide_chat.py already uses


def get_view(state: MutableMapping) -> str:
    """Current view. Anything missing or unknown means the landing page."""
    view = state.get(VIEW_KEY)
    return view if view in _VIEWS else VIEW_LANDING


def enter_app(state: MutableMapping, page: str | None = None, open_guide: bool = False) -> str:
    """Switch to the application view and choose the first page.

    page=None opens the Overview Dashboard (reg.DEFAULT_PAGE). An unknown page
    key also falls back to the dashboard. Only the view, page and (optionally)
    the chat-open flag are written; everything else in the session, such as
    chat history or tool results, is left untouched. Safe to call repeatedly.
    """
    target = page if page in reg.implemented_keys() else reg.DEFAULT_PAGE
    state[VIEW_KEY] = VIEW_APP
    state[PAGE_KEY] = target
    if open_guide:
        state[GUIDE_OPEN_KEY] = True
    return target
