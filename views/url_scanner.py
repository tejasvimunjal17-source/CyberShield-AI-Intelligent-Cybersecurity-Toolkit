from __future__ import annotations

import streamlit as st

from backend import openrouter_client as orc
from backend.ai_explainer import explain_url_findings
from backend.security_utils import MAX_URL_LENGTH
from backend.url_analyzer import analyze_url
from components import vt_report
from components.cards import badge, finding_card
from components.header import page_header
from config import get_openrouter_config

TONE = {"No strong heuristic signals": "info", "Some suspicious signals": "warn",
        "Many suspicious signals": "bad", "Could not analyze": "neutral"}

RECOMMENDATIONS = (
    "Do not open the link if you were not expecting it.",
    "Reach the organization through its official app or a website address you type yourself.",
    "Never enter passwords or one-time codes on a page reached from an unexpected message.",
    "Report suspected phishing to your email provider, school or employer.",
)


def render_analysis(analysis, key_prefix: str) -> None:
    """Shared with the QR analyzer."""
    if not analysis.valid:
        st.error(analysis.error)
        return
    st.markdown(badge(analysis.signal_level, TONE[analysis.signal_level]), unsafe_allow_html=True)
    st.caption("Heuristic result based only on the text of the URL. Nothing was visited.")
    st.markdown("**Safe-to-share (defanged) form**")
    st.code(analysis.defanged, language=None)
    c1, c2, c3 = st.columns(3)
    c1.metric("Scheme", analysis.scheme)
    c2.metric("Port", analysis.port or ("443" if analysis.scheme == "https" else "80"))
    c3.write("**Host**")
    c3.code(analysis.hostname, language=None)
    st.caption(f"Approximate registered domain: {analysis.registered_domain}")
    if analysis.findings:
        for f in sorted(analysis.findings, key=lambda x: -{"high": 3, "medium": 2, "low": 1, "info": 0}[x.severity]):
            finding_card(f.severity, f.title, f.detail)
    else:
        st.success("No heuristic signals were found. This does not mean the URL is safe.")
    with st.expander("Recommended defensive actions"):
        for r in RECOMMENDATIONS:
            st.markdown(f"- {r}")


def render_vt_section(analysis, key_prefix: str) -> None:
    st.subheader("VirusTotal reputation")
    if not vt_report.vt_available():
        vt_report.not_configured_notice()
        return
    st.caption("Pressing the button sends this URL's text to VirusTotal (a third party). "
               "The app only reads existing reports and does not submit the URL for scanning.")
    state_key = f"{key_prefix}_vt"
    if st.button("Look up on VirusTotal", key=f"{key_prefix}_vt_btn"):
        report = vt_report.run_lookup("url", analysis.normalized)
        st.session_state[state_key] = (analysis.normalized, report)
    stored = st.session_state.get(state_key)
    if stored and stored[0] == analysis.normalized and stored[1] is not None:
        vt_report.render_report(stored[1])


def render() -> None:
    page_header("URL Security Scanner",
                "Inspect a suspicious link without opening it. Analysis is offline unless you request a lookup.")
    url = st.text_input("URL to analyze", max_chars=MAX_URL_LENGTH,
                        placeholder="https://example.com/login")
    if st.button("Analyze URL", type="primary"):
        st.session_state["url_analysis"] = analyze_url(url)
        st.session_state.pop("url_ai", None)

    analysis = st.session_state.get("url_analysis")
    if analysis is None:
        st.info("Paste a URL and press Analyze URL. The app never visits it.")
        return

    render_analysis(analysis, "url")
    if not analysis.valid:
        return
    render_vt_section(analysis, "url")

    st.subheader("AI explanation (optional)")
    if not get_openrouter_config().is_configured:
        st.info("AI explanations are disabled: OPENROUTER_API_KEY is not set. See Settings & API Configuration.")
        return
    st.caption("Sends only the hostname and the finding titles to OpenRouter, not the full URL.")
    if st.button("Explain findings with AI", key="url_ai_btn"):
        try:
            with st.spinner("Generating explanation..."):
                st.session_state["url_ai"] = explain_url_findings(analysis)
        except orc.OpenRouterError as exc:
            st.error(str(exc))
    if st.session_state.get("url_ai"):
        st.markdown(st.session_state["url_ai"])
        st.caption("AI-generated explanation of the heuristic findings. It is not a scan result.")
