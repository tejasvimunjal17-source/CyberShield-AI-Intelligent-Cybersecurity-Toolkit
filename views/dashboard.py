from __future__ import annotations

import streamlit as st

from components.compat import BUTTON_STRETCH

import app_registry as reg
from components.cards import badge, info_card
from components.header import hero
from components.sidebar import go_to
from config import service_status


def render() -> None:
    hero()
    st.write("A toolkit for inspecting suspicious links, checking file hashes, and creating or "
             "inspecting QR codes, with optional VirusTotal and AI help.")

    st.subheader("Service status")
    status = service_status()
    c1, c2 = st.columns(2)
    with c1:
        info_card("VirusTotal", "Reputation lookups for URLs and hashes.",
                  badge("key detected" if status["virustotal"] else "not configured",
                        "ok" if status["virustotal"] else "warn"))
    with c2:
        info_card("OpenRouter (AI)", "Powers CyberGuide AI and AI explanations.",
                  badge("key detected" if status["openrouter"] else "not configured",
                        "ok" if status["openrouter"] else "warn"))
    st.caption("'Key detected' only means a value is set. Connections are tested when you run a lookup or ask CyberGuide AI.")

    st.subheader("Tools")
    tools = [m for m in reg.implemented() if m.key not in ("dashboard", "settings", "about")]
    cols = st.columns(2)
    for i, m in enumerate(tools):
        with cols[i % 2]:
            info_card(f"{m.icon} {m.title}", m.summary)
            if st.button(f"Open {m.title}", key=f"dash_open_{m.key}", **BUTTON_STRETCH):
                go_to(m.key)
                st.rerun()

    with st.expander("Planned, not available yet"):
        for m in reg.planned():
            st.markdown(f"- **{m.title}**: {m.summary}")

    st.info("Use the 🛡️ shield button (top-left) to open navigation, or the 💬 CyberGuide AI button (bottom-right) if you are not sure where to start.")
