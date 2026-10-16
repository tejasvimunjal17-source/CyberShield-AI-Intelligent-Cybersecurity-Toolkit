"""Theme CSS. Deliberately small: it styles our own classes and a few
layout details, and leaves Streamlit's native widgets alone so controls
keep working across Streamlit versions."""

from __future__ import annotations

import streamlit as st

COLORS = {
    "bg": "#0B1628", "panel": "#12233D", "border": "#24405F",
    "text": "#E6EEF8", "muted": "#9DB0C8", "cyan": "#22D3EE", "teal": "#14B8A6",
    "ok": "#34D399", "warn": "#FBBF24", "bad": "#F87171", "info": "#60A5FA",
}

_CSS = f"""
<style>
.block-container {{ padding-top: 1.6rem; max-width: 1100px; }}
.cs-card {{ background:{COLORS['panel']}; border:1px solid {COLORS['border']};
  border-radius:12px; padding:14px 16px; margin-bottom:10px; }}
.cs-card h4 {{ margin:0 0 4px 0; font-size:1rem; }}
.cs-muted {{ color:{COLORS['muted']}; font-size:0.9rem; }}
.cs-metric {{ font-size:1.5rem; font-weight:700; margin:2px 0; }}
.cs-badge {{ display:inline-block; padding:2px 10px; border-radius:999px;
  font-size:0.8rem; font-weight:600; border:1px solid currentColor; }}
.cs-ok {{ color:{COLORS['ok']}; }} .cs-warn {{ color:{COLORS['warn']}; }}
.cs-bad {{ color:{COLORS['bad']}; }} .cs-info {{ color:{COLORS['info']}; }}
.cs-neutral {{ color:{COLORS['muted']}; }}
.cs-finding {{ border-left:4px solid {COLORS['border']}; padding:8px 12px; margin:8px 0;
  background:{COLORS['panel']}; border-radius:0 8px 8px 0; }}
.cs-finding.high {{ border-left-color:{COLORS['bad']}; }}
.cs-finding.medium {{ border-left-color:{COLORS['warn']}; }}
.cs-finding.low {{ border-left-color:{COLORS['info']}; }}
.cs-finding.info {{ border-left-color:{COLORS['muted']}; }}
.cs-hero h1 {{ margin-bottom:0; }}
.cs-hero p {{ color:{COLORS['cyan']}; margin-top:2px; }}
/* Floating CyberGuide AI */
div[class*="st-key-cyberguide_fab"] {{
  position: fixed !important; bottom: 18px; right: 18px; z-index: 999;
  width: min(390px, calc(100vw - 24px)); max-height: 82vh; overflow-y: auto;
  background:{COLORS['panel']}; border:1px solid {COLORS['border']};
  border-radius:16px; padding:10px 12px; box-shadow:0 8px 28px rgba(0,0,0,.45);
}}
@media (max-width: 640px) {{
  .block-container {{ padding-left: .8rem; padding-right: .8rem; }}
}}
</style>
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
