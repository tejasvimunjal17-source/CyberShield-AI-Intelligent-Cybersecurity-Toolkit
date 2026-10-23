"""File report presentation (Part 7).

Same Summary / Detection / Details structure as the URL report, in CyberShield
AI's own styling, reusing the Part 6 vendor table and analysis-status widgets.
Only fields VirusTotal actually returned are shown; others are omitted or
labelled "Not returned". Dynamic text (names, types, tags, vendor labels) is
untrusted: it is shown via native widgets or html.escape()d badges only.
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from backend import virustotal_client as vt
from backend.file_report import VT_PENDING, VT_REPORT, compose_overview, format_utc, relative_age
from backend.security_utils import human_size
from components.cards import badge
from components.compat import DATAFRAME_STRETCH
from components.url_report_ui import render_analysis_status, render_detection_tab  # noqa: F401  (re-exported)


def _rows(pairs: list[tuple[str, str]]) -> None:
    st.dataframe([{"Field": k, "Value": v} for k, v in pairs], hide_index=True, **DATAFRAME_STRETCH)


def render_header_strip(report: vt.VTReport, now: datetime | None = None) -> None:
    age = relative_age(report.last_analysis_date, now)
    c1, c2, c3 = st.columns(3)
    c1.metric("File type", report.file_type or "n/a")
    c2.metric("Size", human_size(report.file_size) if report.file_size is not None else "n/a")
    c3.metric("Last analysis", age or ("n/a" if not report.last_analysis_date
                                       else format_utc(report.last_analysis_date)))
    st.caption("File type and size are what VirusTotal recorded. CyberShield AI never opened or ran the file.")


def render_summary_tab(report: vt.VTReport | None, vt_state: str, error: str = "",
                       queried_hash: str = "", now: datetime | None = None) -> None:
    ov = compose_overview(vt_state, report, error, queried_hash, now)
    st.markdown("**VirusTotal reputation** (external data, separate from the local hashes above)")
    st.markdown(badge(ov.vt_headline or "No data", ov.vt_tone), unsafe_allow_html=True)
    if ov.vt_detail:
        st.caption(ov.vt_detail)

    if report is not None and vt_state == VT_REPORT:
        c = st.columns(5)
        for col, (label, val) in zip(c, [
            ("Malicious", report.malicious), ("Suspicious", report.suspicious),
            ("Clean", report.harmless), ("Undetected", report.undetected),
            ("Timed out", report.timeout),
        ]):
            col.metric(label, val)
        if ov.last_analysis_utc:
            st.caption(f"Last analysis: {ov.last_analysis_utc}"
                       + (f" ({ov.last_analysis_age})" if ov.last_analysis_age else ""))
        if report.threat_label:
            st.markdown("**Suggested threat label** (from VirusTotal's classification)")
            st.code(report.threat_label, language=None)
        if report.threat_names:
            st.markdown("**Popular threat names reported**")
            st.code("\n".join(report.threat_names), language=None)

    for note in ov.caveats:
        if note.startswith("WARNING"):
            st.warning(note)
        else:
            st.caption(note)


def render_details_tab(report: vt.VTReport) -> None:
    info: list[tuple[str, str]] = []
    if report.file_type:
        info.append(("File type", report.file_type))
    if report.magic:
        info.append(("Magic", report.magic))
    if report.file_size is not None:
        info.append(("Size", f"{human_size(report.file_size)} ({report.file_size} bytes)"))
    if report.meaningful_name:
        info.append(("Most meaningful name", report.meaningful_name))
    if report.reputation is not None:
        info.append(("Community reputation score", str(report.reputation)))
    if info:
        st.markdown("**File information**")
        _rows(info)
    else:
        st.caption("VirusTotal returned no file-information fields for this report.")

    if report.names:
        st.markdown("**Names seen by VirusTotal**")
        st.code("\n".join(report.names), language=None)

    hashes = [(label, h) for label, h in (("SHA-256", report.sha256), ("SHA-1", report.sha1),
                                          ("MD5", report.md5)) if h]
    if hashes:
        st.markdown("**Hashes returned by VirusTotal**")
        st.code("\n".join(f"{label}: {h}" for label, h in hashes), language=None)

    if report.tags:
        st.markdown("**Tags**")
        st.markdown(" ".join(badge(t, "neutral") for t in report.tags), unsafe_allow_html=True)
        st.caption("Tags describe observed file properties. They are not verdicts.")

    history = [
        ("First submission", format_utc(report.first_submission_date)),
        ("Last submission", format_utc(report.last_submission_date)),
        ("Last analysis", format_utc(report.last_analysis_date)),
    ]
    if report.times_submitted is not None:
        history.append(("Times submitted", str(report.times_submitted)))
    st.markdown("**History**")
    _rows(history)

    st.markdown("**Report reference**")
    if report.report_id:
        st.code(report.report_id, language=None)
    st.markdown(f"[Open the full report on VirusTotal]({report.permalink})")


def render_file_report(report: vt.VTReport | None, vt_state: str, error: str = "",
                       queried_hash: str = "", now: datetime | None = None) -> None:
    """Entry point. `vt_state` is one of the backend.file_report VT_* constants."""
    if report is not None and vt_state == VT_REPORT:
        render_header_strip(report, now)
        summary, detection, details = st.tabs(["Summary", "Detection", "Details"])
        with summary:
            render_summary_tab(report, vt_state, error, queried_hash, now)
        with detection:
            render_detection_tab(report)
        with details:
            render_details_tab(report)
        return
    render_summary_tab(report, vt_state, error, queried_hash, now)
    if report is not None and vt_state == VT_PENDING:
        st.markdown(f"[Open the report on VirusTotal]({report.permalink})")
