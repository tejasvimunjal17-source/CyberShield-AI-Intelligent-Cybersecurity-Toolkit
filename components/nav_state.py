"""Navigation-drawer state and ordering. No Streamlit import: functions take
any dict-like session state, so the logic is unit-testable.

State variable (dedicated, clearly named):
  st.session_state["cybershield_sidebar_open"]  -> bool, default False

Default is closed on purpose: the drawer is a fixed overlay, and Python
cannot detect the viewport width. Open-by-default would cover the whole
screen on a phone. The shield button is always visible, so it stays
discoverable (the dashboard also points to it).

Opening or closing writes ONLY this key. The current page ("page") is never
touched by a toggle, so toggling cannot send the user back to the dashboard.
"""

from __future__ import annotations

from collections.abc import MutableMapping

import app_registry as reg
from components.app_state import PAGE_KEY

SIDEBAR_KEY = "cybershield_sidebar_open"
DEFAULT_SIDEBAR_OPEN = False

# Order of groups in the drawer. Items inside a group keep registry order.
# Result: Dashboard, URL Scanner, File Hash, QR Generator, QR Analyzer,
# Learning Center, Settings, About.
NAV_GROUP_ORDER = ("Platform", "Analysis", "QR Tools", "Learn", "System")


def is_sidebar_open(state: MutableMapping) -> bool:
    return bool(state.get(SIDEBAR_KEY, DEFAULT_SIDEBAR_OPEN))


def toggle_sidebar(state: MutableMapping) -> bool:
    """Flip open/closed. Returns the new value. Touches nothing else."""
    state[SIDEBAR_KEY] = not is_sidebar_open(state)
    return state[SIDEBAR_KEY]


def close_sidebar(state: MutableMapping) -> None:
    state[SIDEBAR_KEY] = False


def navigate(state: MutableMapping, page: str) -> str:
    """Go to an implemented page and close the drawer.

    An unknown or planned page key leaves the current page unchanged (the
    drawer still closes). Selecting the page that is already active is fine.
    Returns the page now shown.
    """
    if page in reg.implemented_keys():
        state[PAGE_KEY] = page
    close_sidebar(state)
    current = state.get(PAGE_KEY)
    return current if current in reg.implemented_keys() else reg.DEFAULT_PAGE


def nav_groups() -> list[tuple[str, tuple[reg.Module, ...]]]:
    """Implemented modules grouped and ordered for the drawer. Planned
    modules are never included."""
    grouped: dict[str, list[reg.Module]] = {}
    for module in reg.implemented():
        grouped.setdefault(module.group, []).append(module)
    ordered = [g for g in NAV_GROUP_ORDER if g in grouped]
    ordered += [g for g in grouped if g not in NAV_GROUP_ORDER]   # unknown groups last
    return [(g, tuple(grouped[g])) for g in ordered]
