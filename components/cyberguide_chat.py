"""Floating CyberGuide AI chat. The panel is a fixed-position keyed
container (same technique as the Sahay AI reference), so it sits on every
page. st.chat_input cannot live inside a container, so a form is used."""

from __future__ import annotations

import streamlit as st

from components.compat import BUTTON_STRETCH

import app_registry as reg
from components.sidebar import go_to
from config import GUIDE_NAME, service_status
from cyberguide import engine

WELCOME = ("Hi, I'm CyberGuide AI. I explain how CyberShield AI works and help troubleshoot it. "
           "I can't run scans for you; scans happen on the tool pages.")
SUGGESTIONS = ("How do I generate a QR code?", "How do I analyze a suspicious URL?",
               "Why is VirusTotal not working?")


def _ask(question: str) -> None:
    history = st.session_state["guide_history"]
    with st.spinner("CyberGuide AI is thinking..."):
        result = engine.answer(question, history, service_status())
    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": result.text, "source": result.source,
                    "pages": result.pages, "notice": result.notice})


def render_cyberguide() -> None:
    st.session_state.setdefault("guide_open", False)
    st.session_state.setdefault("guide_history", [])

    with st.container(key="cyberguide_fab"):
        label = "✖ Close CyberGuide AI" if st.session_state["guide_open"] else f"💬 {GUIDE_NAME}"
        if st.button(label, key="guide_toggle", **BUTTON_STRETCH):
            st.session_state["guide_open"] = not st.session_state["guide_open"]
            st.rerun()
        if not st.session_state["guide_open"]:
            return

        st.caption("AI guide for this app. Explanations, not scan results.")
        with st.chat_message("assistant"):
            st.write(WELCOME)
        for i, turn in enumerate(st.session_state["guide_history"]):
            with st.chat_message(turn["role"]):
                st.markdown(turn["content"])
                if turn["role"] == "assistant":
                    tag = "AI-generated explanation" if turn.get("source") == "ai" else "From app documentation"
                    st.caption(tag)
                    if turn.get("notice"):
                        st.caption(turn["notice"])
                    for page in turn.get("pages", []):
                        module = reg.get_module(page)
                        if module and module.status == "implemented":
                            if st.button(f"Open {module.title}", key=f"guide_open_{i}_{page}"):
                                go_to(page)
                                st.rerun()

        if not st.session_state["guide_history"]:
            for s in SUGGESTIONS:
                if st.button(s, key=f"guide_sug_{s}", **BUTTON_STRETCH):
                    _ask(s)
                    st.rerun()

        with st.form("guide_form", clear_on_submit=True):
            text = st.text_input("Ask CyberGuide AI", max_chars=1000, label_visibility="collapsed",
                                 placeholder="Ask about a tool, setting or error...")
            if st.form_submit_button("Send", **BUTTON_STRETCH) and text.strip():
                _ask(text)
                st.rerun()
        if st.session_state["guide_history"] and st.button("Clear chat", key="guide_clear"):
            st.session_state["guide_history"] = []
            st.rerun()
