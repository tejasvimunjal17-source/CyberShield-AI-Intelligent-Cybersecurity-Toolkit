"""CSS for Streamlit "chrome" (toolbar, header, default sidebar). No
Streamlit import, so it can be unit-tested without Streamlit installed.

What is supported and what is not
- `toolbarMode = "minimal"` (.streamlit/config.toml) hides Streamlit's own
  developer options, but its documented meaning is "show only options set
  externally (e.g. Streamlit Community Cloud)". It therefore KEEPS the Share /
  star / edit / GitHub items that Community Cloud injects. No toolbarMode
  value removes host-injected items.
- `[ui] hideTopBar = true` is the config route to hide the top bar. It is
  set in config.toml. Whether it also removes Community Cloud's items depends
  on the Streamlit version, so it is not relied on alone.
- The CSS below is a best-effort fallback that hides the toolbar and (when the
  custom shield navigation is in use) the whole header. These `data-testid`
  values are Streamlit internals and may change between versions; if they stop
  matching, the controls simply reappear and nothing else breaks.
  A private GitHub repository changes what Community Cloud shows and is the
  other practical option.

Why hiding the header is safe now
- Navigation is the custom shield button and drawer (components/shield_nav.py).
  They are `position: fixed` elements in the page body, not part of Streamlit's
  header. The header is therefore not needed. When the legacy Streamlit sidebar
  is enabled (SHOW_DEFAULT_SIDEBAR = True) its collapse control lives in the
  header, so then only the toolbar is hidden.

Deliberately not targeted
- The "Manage app" control. It belongs to Streamlit Community Cloud, not to
  this app's page, and no selector here matches it.
"""

from __future__ import annotations

# Toolbar controls (Share, star, edit, GitHub, deploy, app menu, status).
TOOLBAR_SELECTORS = (
    '[data-testid="stToolbar"]',
    '[data-testid="stToolbarActions"]',
    '[data-testid="stAppDeployButton"]',
    ".stAppDeployButton",
    '[data-testid="stMainMenu"]',
)

# The header bar and the decoration line above it. Hidden only when the custom
# shield navigation replaces the default sidebar.
HEADER_SELECTORS = (
    '[data-testid="stHeader"]',
    '[data-testid="stDecoration"]',
)

SIDEBAR_SELECTORS = (
    '[data-testid="stSidebar"]',
    '[data-testid="stSidebarCollapsedControl"]',
    '[data-testid="collapsedControl"]',
    '[data-testid="stSidebarNav"]',
)


def _rule(selectors: tuple[str, ...]) -> str:
    return ",\n".join(selectors) + " { display: none !important; }"


def chrome_css(hide_default_sidebar: bool) -> str:
    """hide_default_sidebar=True means the custom shield navigation is in use:
    hide the toolbar, header and (safety net) any default sidebar. False means
    the legacy Streamlit sidebar is on: hide only the toolbar."""
    rules = [_rule(TOOLBAR_SELECTORS)]
    if hide_default_sidebar:
        rules.append(_rule(HEADER_SELECTORS))
        rules.append(_rule(SIDEBAR_SELECTORS))
    return "<style>\n" + "\n".join(rules) + "\n</style>"

