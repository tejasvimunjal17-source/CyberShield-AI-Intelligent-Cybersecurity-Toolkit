"""URL report presentation (Part 6).

Layout follows the information hierarchy of VirusTotal's own report page
(header strip, then Summary / Detection / Details) but uses CyberShield AI's
styling. Only fields the API actually returned are shown; missing fields are
omitted or labelled "not returned", never invented.

All dynamic text is untrusted (URLs, titles, vendor labels). It is shown via
native Streamlit widgets (code, dataframe, metric) or html.escape()d badges,
and redirect-chain URLs are rendered as inert text, never as links.
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from backend import virustotal_client as vt
from backend.url_analyzer import UrlAnalysis, defang
from backend.url_report import (
    VT_PENDING, VT_REPORT, compose_overview, format_utc, relative_age,
)
from components.cards import badge
from components.compat import DATAFRAME_STRETCH

VERDICT_LABELS = {
    "harmless": "Clean",
    "undetected": "Undetected",
    "malicious": "Malicious",
    "suspicious": "Suspicious",
    "timeout": "Timed out",
    "type-unsupported": "Unsupported",
}
VERDICT_TONES = {"malicious": "bad", "suspicious": "warn", "harmless": "info", "undetected": "neutral"}


def verdict_label(category: str) -> str:
    return VERDICT_LABELS.get(category, category or "Unknown")


def _tone_badge(text: str, tone: str) -> None:
    st.markdown(badge(text, tone), unsafe_allow_html=True)


def _rows(pairs: list[tuple[str, str]]) -> None:
    st.dataframe([{"Field": k, "Value": v} for k, v in pairs], hide_index=True, **DATAFRAME_STRETCH)


def render_header_strip(report: vt.VTReport, now: datetime | None = None) -> None:
    """Status code, content type and analysis age (the strip at the top of VT's report)."""
    age = relative_age(report.last_analysis_date, now)
    c1, c2, c3 = st.columns(3)
    c1.metric("HTTP status", str(report.http_status) if report.http_status is not None else "n/a")
    c2.metric("Content type", report.content_type.split(";")[0] if report.content_type else "n/a")
    c3.metric("Last analysis", age or ("n/a" if not report.last_analysis_date else format_utc(report.last_analysis_date)))
    st.caption("HTTP status and content type are what VirusTotal recorded when ITS scanner "
               "last fetched the page. CyberShield AI did not visit the URL.")


def render_summary_tab(analysis: UrlAnalysis, report: vt.VTReport | None, vt_state: str,
                       error: str = "", now: datetime | None = None) -> None:
    ov = compose_overview(analysis, vt_state, report, error, now)

    st.markdown("**Local heuristics** (computed from the URL text only)")
    tone = {"No strong heuristic signals": "info", "Some suspicious signals": "warn",
            "Many suspicious signals": "bad"}.get(ov.local_level, "neutral")
    _tone_badge(ov.local_level, tone)
    st.caption(f"{ov.local_finding_count} finding(s). Details are in the heuristic section above.")

    st.markdown("**VirusTotal reputation** (external data)")
    _tone_badge(ov.vt_headline or "No data", ov.vt_tone)
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
        if report.threat_names:
            st.markdown("**Threat names reported**")
            st.code("\n".join(report.threat_names), language=None)

    for note in ov.caveats:
        st.caption(note)


def render_detection_tab(report: vt.VTReport) -> None:
    st.markdown("**Security vendors' analysis**")
    if not report.all_results:
        st.info("VirusTotal did not return per-vendor results for this report.")
        return
    flagged = [r for r in report.all_results if r[1] in ("malicious", "suspicious")]
    if flagged:
        st.markdown(f"**Flagged by {len(flagged)} vendor(s)**")
        st.dataframe(
            [{"Vendor": e, "Verdict": verdict_label(c), "Label": r or "-"} for e, c, r in flagged],
            hide_index=True, **DATAFRAME_STRETCH,
        )
    else:
        st.success("No vendor returned a malicious or suspicious verdict. This is not proof of safety.")
    with st.expander(f"All vendor results ({len(report.all_results)})"):
        st.dataframe(
            [{"Vendor": e, "Verdict": verdict_label(c)} for e, c, _ in report.all_results],
            hide_index=True, **DATAFRAME_STRETCH,
        )
    if len(report.all_results) >= vt.MAX_ALL_RESULT_ROWS:
        st.caption(f"Showing the first {vt.MAX_ALL_RESULT_ROWS} vendor results.")


def render_details_tab(report: vt.VTReport) -> None:
    overview: list[tuple[str, str]] = []
    if report.final_url:
        overview.append(("Final URL (defanged)", defang(report.final_url)))
    if report.title:
        overview.append(("Page title", report.title))
    if report.http_status is not None:
        overview.append(("Last HTTP status", str(report.http_status)))
    if report.content_type:
        overview.append(("Content type", report.content_type))
    if report.reputation is not None:
        overview.append(("Community reputation score", str(report.reputation)))
    if overview:
        st.markdown("**URL overview**")
        _rows(overview)
    else:
        st.caption("VirusTotal returned no URL overview fields (final URL, title, status) for this report.")

    if report.redirection_chain:
        st.markdown("**Redirection chain**")
        st.caption("Shown as inert text. Defanged so nothing is clickable.")
        st.code("\n".join(("-> " if i else "") + defang(u) for i, u in enumerate(report.redirection_chain)),
                language=None)

    if report.categories:
        st.markdown("**Categories (by vendor)**")
        st.dataframe([{"Vendor": v, "Category": c} for v, c in report.categories],
                     hide_index=True, **DATAFRAME_STRETCH)

    if report.tags:
        st.markdown("**Tags**")
        st.markdown(" ".join(badge(t, "neutral") for t in report.tags), unsafe_allow_html=True)
        st.caption("Tags describe observed page features. They are not verdicts.")

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


def render_url_report(analysis: UrlAnalysis, report: vt.VTReport | None, vt_state: str,
                      error: str = "", now: datetime | None = None) -> None:
    """Entry point. `vt_state` is one of the backend.url_report VT_* constants."""
    if report is not None and vt_state == VT_REPORT:
        render_header_strip(report, now)
        summary, detection, details = st.tabs(["Summary", "Detection", "Details"])
        with summary:
            render_summary_tab(analysis, report, vt_state, error, now)
        with detection:
            render_detection_tab(report)
        with details:
            render_details_tab(report)
        return
    # No vendor data: only the summary applies (no empty Detection/Details tabs).
    render_summary_tab(analysis, report, vt_state, error, now)
    if report is not None and vt_state == VT_PENDING:
        st.markdown(f"[Open the report on VirusTotal]({report.permalink})")


def render_analysis_status(status: vt.VTAnalysis, now: datetime | None = None) -> None:
    """State of a submitted analysis. Does not claim completion unless VT said so."""
    labels = {"queued": "Queued", "in-progress": "In progress", "completed": "Completed"}
    _tone_badge(f"Analysis {labels.get(status.status, status.status)}",
                "info" if status.completed else "neutral")
    st.caption(f"Analysis ID: {status.analysis_id}")
    if not status.completed:
        st.info("VirusTotal has not finished this analysis. Wait a little and check again. "
                "No verdict exists yet.")
        return
    c = st.columns(5)
    for col, (label, val) in zip(c, [
        ("Malicious", status.malicious), ("Suspicious", status.suspicious),
        ("Clean", status.harmless), ("Undetected", status.undetected),
        ("Timed out", status.timeout),
    ]):
        col.metric(label, val)
    if status.date:
        age = relative_age(status.date, now)
        st.caption(f"Analysis date: {format_utc(status.date)}" + (f" ({age})" if age else ""))
    flagged = [r for r in status.results if r[1] in ("malicious", "suspicious")]
    if flagged:
        st.dataframe([{"Vendor": e, "Verdict": verdict_label(c_), "Label": r or "-"} for e, c_, r in flagged],
                     hide_index=True, **DATAFRAME_STRETCH)
    elif status.total_engines:
        st.caption("No vendor returned a malicious or suspicious verdict. This is not proof of safety.")
    st.caption("Press 'Look up existing report' again to load the full report with details.")

