"""Shared rendering for VirusTotal lookups and the lookup call itself, so
the URL scanner, file analyzer and QR analyzer behave identically."""

from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from components.compat import DATAFRAME_STRETCH

from backend import virustotal_client as vt
from components.cards import badge
from config import get_virustotal_config


def vt_available() -> bool:
    return get_virustotal_config().is_configured


def run_lookup(kind: str, value: str) -> vt.VTReport | None:
    """Performs a REAL lookup. Returns None (after showing the reason) on failure."""
    try:
        with st.spinner("Asking VirusTotal for an existing report..."):
            return vt.lookup_hash(value) if kind == "file" else vt.lookup_url(value)
    except vt.VirusTotalError as exc:
        st.error(str(exc))
        return None


def render_report(report: vt.VTReport) -> None:
    if not report.found:
        st.warning(
            "VirusTotal has no existing report for this item. That is not a verdict: "
            "it only means nobody has submitted it. This app does not submit items."
        )
        return
    if report.pending:
        st.info("A report exists but has no engine results yet (analysis may be pending). Check again later.")
        st.markdown(f"[Open the report on VirusTotal]({report.permalink})")
        return

    if report.malicious:
        st.markdown(badge(f"{report.malicious} engines: malicious", "bad"), unsafe_allow_html=True)
    elif report.suspicious:
        st.markdown(badge(f"{report.suspicious} engines: suspicious", "warn"), unsafe_allow_html=True)
    else:
        st.markdown(badge("No engine flagged this item", "info"), unsafe_allow_html=True)

    cols = st.columns(5)
    for col, (label, val) in zip(cols, [
        ("Malicious", report.malicious), ("Suspicious", report.suspicious),
        ("Harmless", report.harmless), ("Undetected", report.undetected),
        ("Timeout", report.timeout),
    ]):
        col.metric(label, val)

    st.caption(f"{report.total_engines} engine results.")
    if report.last_analysis_date:
        when = datetime.fromtimestamp(report.last_analysis_date, tz=timezone.utc)
        st.caption(f"Last analysis (UTC): {when:%Y-%m-%d %H:%M}")
    if not (report.malicious or report.suspicious):
        st.caption("Zero detections do not prove an item is safe. New threats are often missed at first.")
    if report.flagged_engines:
        st.markdown("**Engines that flagged it**")
        st.dataframe(
            [{"Engine": e, "Category": c, "Label": r} for e, c, r in report.flagged_engines],
            **DATAFRAME_STRETCH, hide_index=True,
        )
    st.markdown(f"[Open the full report on VirusTotal]({report.permalink})")


def not_configured_notice() -> None:
    st.info(
        "VirusTotal lookups are disabled: VIRUSTOTAL_API_KEY is not set. "
        "See Settings & API Configuration. All local tools still work."
    )
