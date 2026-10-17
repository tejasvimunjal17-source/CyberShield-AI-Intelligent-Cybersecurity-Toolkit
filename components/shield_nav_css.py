"""CSS for the shield toggle and navigation drawer. No Streamlit import.

How it works (and what it is NOT)
- The drawer is a keyed st.container() styled `position: fixed`, the same
  technique the floating CyberGuide AI panel already uses. It overlays the
  page; it does not push content. It is rendered only while open, so there is
  no hidden-offscreen state to get out of sync with session state.
- It does not use Streamlit's own sidebar element, and nothing here targets
  stSidebar / stHeader / stToolbar (Part 1 owns those).
- There is no backdrop: the shield button (always on top) and choosing a page
  both close it.
- Key names are chosen so no key is a substring of another; Streamlit adds a
  `st-key-<key>` class and the selectors below match with `*=`.
"""

from __future__ import annotations

TOGGLE_BOX_KEY = "cybershield_navtoggle_box"
TOGGLE_BTN_KEY = "cybershield_navtoggle_btn"
DRAWER_KEY = "cybershield_navdrawer_panel"
ITEM_PREFIX = "cs_navitem_"
ITEM_ACTIVE_PREFIX = "cs_navitem_active_"

_CSS = """
<style>
/* content must never sit under the fixed shield button */
.block-container { padding-top: 4rem !important; }

/* ---------- shield toggle ---------- */
div[class*="st-key-cybershield_navtoggle_box"] {
  position: fixed !important; top: 10px; left: 12px; z-index: 1000000; width: 48px;
}
div[class*="st-key-cybershield_navtoggle_btn"] button {
  width: 44px; height: 44px; min-height: 44px; padding: 0; font-size: 1.35rem; line-height: 1;
  border-radius: 12px; border: 1px solid rgba(34,211,238,.5);
  background: linear-gradient(135deg, rgba(34,211,238,.20), rgba(20,184,166,.12)), #12233D;
  box-shadow: 0 4px 14px rgba(0,0,0,.35);
}
div[class*="st-key-cybershield_navtoggle_btn"] button:hover {
  border-color: #22D3EE; box-shadow: 0 0 0 3px rgba(34,211,238,.18), 0 4px 14px rgba(0,0,0,.35);
}
div[class*="st-key-cybershield_navtoggle_btn"] button:focus-visible {
  outline: 2px solid #22D3EE; outline-offset: 2px;
}

/* ---------- drawer ---------- */
div[class*="st-key-cybershield_navdrawer_panel"] {
  position: fixed !important; top: 0; left: 0; bottom: 0; z-index: 999998;
  width: min(300px, 86vw); overflow-y: auto; box-sizing: border-box; padding: 12px 14px 20px 14px;
  background: linear-gradient(180deg, #0E1D33, #0B1628);
  border-right: 1px solid #24405F; box-shadow: 8px 0 30px rgba(0,0,0,.45);
  animation: cs-drawer-in .18s ease-out;
}
@keyframes cs-drawer-in { from { transform: translateX(-16px); opacity: 0; } to { transform: none; opacity: 1; } }
@media (prefers-reduced-motion: reduce) {
  div[class*="st-key-cybershield_navdrawer_panel"] { animation: none; }
}
.cs-d-head { min-height: 44px; padding-left: 56px; display: flex; flex-direction: column;
  justify-content: center; margin-bottom: 10px; }
.cs-d-brand { font-weight: 800; font-size: 1.08rem; letter-spacing: -.01em; color: #E6EEF8; }
.cs-d-tag { font-size: .74rem; color: #9DB0C8; line-height: 1.3; }
.cs-d-group { margin: 14px 4px 4px 4px; font-size: .72rem; font-weight: 700; letter-spacing: .08em;
  text-transform: uppercase; color: #14B8A6; }
.cs-d-foot { margin-top: 18px; padding-top: 12px; border-top: 1px solid #24405F; font-size: .76rem;
  color: #9DB0C8; line-height: 1.45; }

/* ---------- navigation items ---------- */
div[class*="st-key-cs_navitem_"] button {
  justify-content: flex-start !important; text-align: left; min-height: 42px; border-radius: 10px;
  background: transparent !important; border: 1px solid transparent !important; color: #E6EEF8 !important;
}
div[class*="st-key-cs_navitem_"] button * { color: inherit !important; text-align: left; }
div[class*="st-key-cs_navitem_"] button:hover {
  background: rgba(34,211,238,.09) !important; border-color: rgba(34,211,238,.28) !important;
}
div[class*="st-key-cs_navitem_"] button:focus-visible { outline: 2px solid #22D3EE; outline-offset: 1px; }
div[class*="st-key-cs_navitem_active_"] button {
  background: rgba(34,211,238,.14) !important; border-color: rgba(34,211,238,.6) !important;
  color: #22D3EE !important; font-weight: 700; box-shadow: inset 3px 0 0 #22D3EE;
}

@media (max-width: 640px) {
  div[class*="st-key-cybershield_navdrawer_panel"] { width: min(300px, 88vw); }
}
</style>
"""


def shield_nav_css() -> str:
    return _CSS
