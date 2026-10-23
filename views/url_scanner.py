from __future__ import annotations

import streamlit as st

from backend import openrouter_client as orc
from backend import url_report
from backend import virustotal_client as vt
from backend.ai_explainer import explain_url_findings
from backend.security_utils import MAX_URL_LENGTH
from backend.url_analyzer import analyze_url
from components import url_report_ui, vt_report
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


def _vt_state(stored: dict) -> str:
    if stored.get("error"):
        return url_report.VT_ERROR
    report = stored.get("report")
    if report is None:
        return url_report.VT_ERROR
    if not report.found:
        return url_report.VT_NOT_FOUND
    if report.pending:
        return url_report.VT_PENDING
    return url_report.VT_REPORT


def _render_submission(analysis, key_prefix: str) -> None:
    """Opt-in request for a NEW analysis. Nothing is sent until the user confirms."""
    url = analysis.normalized
    confirm_key = f"{key_prefix}_vt_confirm"
    # Consent is per URL: never carry a ticked box over to a different URL.
    if st.session_state.get(f"{confirm_key}_url") != url:
        st.session_state[confirm_key] = False
        st.session_state[f"{confirm_key}_url"] = url
    sub_key, status_key = f"{key_prefix}_vt_sub", f"{key_prefix}_vt_status"

    with st.expander("Request a new analysis (shares this URL with VirusTotal)"):
        st.markdown("**Before you submit, understand what happens:**")
        for note in url_report.submission_privacy_notes(url):
            st.markdown(f"- {note}")
        confirmed = st.checkbox(
            "I understand and want to share this URL with VirusTotal.", key=confirm_key)
        if st.button("Submit URL to VirusTotal", key=f"{key_prefix}_vt_submit_btn",
                     disabled=not confirmed):
            if confirmed:  # belt and braces: the client also refuses without confirmed=True
                result, err = vt_report.safe_call(vt.submit_url, url, confirmed=True)
                st.session_state[sub_key] = {"url": url, "analysis_id": result.analysis_id if result else "",
                                             "error": err}
                st.session_state.pop(status_key, None)

        sub = st.session_state.get(sub_key)
        if not sub or sub.get("url") != url:
            return
        if sub.get("error"):
            st.error(sub["error"])
            return
        st.success("VirusTotal accepted the URL for analysis. This is not a verdict yet.")
        st.caption(f"Analysis ID: {sub['analysis_id']}")
        if st.button("Check analysis status", key=f"{key_prefix}_vt_status_btn"):
            status, err = vt_report.safe_call(vt.get_analysis, sub["analysis_id"])
            st.session_state[status_key] = {"url": url, "status": status, "error": err}
        shown = st.session_state.get(status_key)
        if shown and shown.get("url") == url:
            if shown.get("error"):
                st.error(shown["error"])
            elif shown.get("status") is not None:
                url_report_ui.render_analysis_status(shown["status"])


def render_vt_section(analysis, key_prefix: str) -> None:
    st.subheader("VirusTotal reputation")
    if not vt_report.vt_available():
        vt_report.not_configured_notice()
        return
    st.caption("External data from a third party, separate from the local heuristics above. "
               "'Look up existing report' sends an encoded form of this URL to VirusTotal to read a report "
               "that already exists. It does not request a new scan, and the app never visits the URL.")
    state_key = f"{key_prefix}_vt_result"
    if st.button("Look up existing report", key=f"{key_prefix}_vt_btn"):
        report, err = vt_report.safe_call(vt.lookup_url, analysis.normalized)
        st.session_state[state_key] = {"url": analysis.normalized, "report": report, "error": err}
    stored = st.session_state.get(state_key)
    if not stored or stored.get("url") != analysis.normalized:
        return
    url_report_ui.render_url_report(analysis, stored.get("report"), _vt_state(stored),
                                    error=stored.get("error", ""))
    _render_submission(analysis, key_prefix)


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

    st.subheader("Local heuristic analysis")
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
