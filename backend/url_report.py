"""Wording and composition helpers for the URL report (Part 6).

Pure functions: no Streamlit, no network. Keeps the two evidence sources
separate on purpose:

* local heuristics  -> text-of-the-URL signals computed by backend.url_analyzer
* VirusTotal data   -> external reputation from backend.virustotal_client

Nothing here merges them into one score. A zero-detection result is never
described as "safe", and a missing/failed lookup is never described as clean.
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urlsplit

from backend.url_analyzer import UrlAnalysis
from backend.virustotal_client import VTReport

STALE_AFTER_DAYS = 30

# State of the external lookup, as the UI knows it.
VT_NOT_CONFIGURED = "not_configured"
VT_NOT_REQUESTED = "not_requested"
VT_ERROR = "error"
VT_NOT_FOUND = "not_found"
VT_PENDING = "pending"
VT_REPORT = "report"

NOT_RETURNED = "Not returned by VirusTotal"


def format_utc(ts: int | None) -> str:
    if not isinstance(ts, int) or isinstance(ts, bool):
        return NOT_RETURNED
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    except (OverflowError, OSError, ValueError):
        return NOT_RETURNED


def relative_age(ts: int | None, now: datetime | None = None) -> str:
    """'5 hours ago' style text, or '' when the timestamp is missing/in the future."""
    if not isinstance(ts, int) or isinstance(ts, bool):
        return ""
    now = now or datetime.now(timezone.utc)
    seconds = int(now.timestamp()) - ts
    if seconds < 0:
        return ""
    if seconds < 90:
        return "moments ago"
    for unit, size in (("day", 86400), ("hour", 3600), ("minute", 60)):
        if seconds >= size:
            n = seconds // size
            return f"{n} {unit}{'s' if n != 1 else ''} ago"
    return ""


def is_stale(ts: int | None, now: datetime | None = None, days: int = STALE_AFTER_DAYS) -> bool:
    if not isinstance(ts, int) or isinstance(ts, bool):
        return False
    now = now or datetime.now(timezone.utc)
    return (int(now.timestamp()) - ts) > days * 86400


@dataclass(frozen=True)
class VtHeadline:
    tone: str       # ok-style tones are avoided: zero detections is only "info"
    headline: str
    detail: str = ""


def vt_headline(report: VTReport) -> VtHeadline:
    """One factual sentence describing the vendor results of a found report."""
    total = report.total_engines
    if report.pending:
        return VtHeadline("neutral", "A report exists but has no vendor results yet.",
                          "Analysis may still be pending. Check again later.")
    if report.malicious:
        extra = f" and {report.suspicious} as suspicious" if report.suspicious else ""
        return VtHeadline(
            "bad",
            f"{report.malicious} of {total} vendor results flagged this URL as malicious{extra}.",
            "Treat the link as dangerous until you have verified it another way. "
            "Individual vendors can be wrong, so look at who flagged it in the Detection tab.",
        )
    if report.suspicious:
        return VtHeadline(
            "warn",
            f"{report.suspicious} of {total} vendor results flagged this URL as suspicious.",
            "No vendor called it malicious, but suspicious flags deserve caution.",
        )
    return VtHeadline(
        "info",
        "No security vendors flagged this URL as malicious or suspicious in the latest analysis.",
        "This is not proof the URL is safe. New or targeted threats are often missed at first.",
    )


@dataclass
class UrlOverview:
    """What the Summary tab shows, assembled from real state only."""
    local_level: str
    local_finding_count: int
    vt_state: str
    vt_headline: str = ""
    vt_detail: str = ""
    vt_tone: str = "neutral"
    last_analysis_utc: str = ""
    last_analysis_age: str = ""
    caveats: list[str] = field(default_factory=list)


def compose_overview(
    analysis: UrlAnalysis,
    vt_state: str,
    report: VTReport | None = None,
    error: str = "",
    now: datetime | None = None,
) -> UrlOverview:
    ov = UrlOverview(
        local_level=analysis.signal_level,
        local_finding_count=len(analysis.findings),
        vt_state=vt_state,
    )
    ov.caveats.append(
        "The local heuristic level counts structural signals in the URL text. "
        "It is not a probability that the URL is malicious."
    )
    if vt_state == VT_NOT_CONFIGURED:
        ov.vt_headline = "VirusTotal is not configured, so no reputation data is available."
        ov.vt_detail = "Local heuristics above still apply."
    elif vt_state == VT_NOT_REQUESTED:
        ov.vt_headline = "No VirusTotal lookup has been requested yet."
    elif vt_state == VT_ERROR:
        ov.vt_headline = "The VirusTotal lookup failed, so there is no reputation data."
        ov.vt_detail = (error or "Unknown error.") + " A failed lookup says nothing about the URL."
    elif vt_state == VT_NOT_FOUND:
        ov.vt_headline = "VirusTotal has no existing report for this URL."
        ov.vt_detail = ("That is not a verdict. It only means no report exists yet. "
                        "You can explicitly request a new analysis below.")
    elif vt_state == VT_PENDING:
        h = vt_headline(report) if report else VtHeadline("neutral", "Report pending.")
        ov.vt_headline, ov.vt_detail, ov.vt_tone = h.headline, h.detail, h.tone
    elif vt_state == VT_REPORT and report is not None:
        h = vt_headline(report)
        ov.vt_headline, ov.vt_detail, ov.vt_tone = h.headline, h.detail, h.tone
        if report.last_analysis_date:
            ov.last_analysis_utc = format_utc(report.last_analysis_date)
            ov.last_analysis_age = relative_age(report.last_analysis_date, now)
            if is_stale(report.last_analysis_date, now):
                ov.caveats.append(
                    f"This VirusTotal analysis is more than {STALE_AFTER_DAYS} days old. "
                    "The URL's content or reputation may have changed since."
                )
        if not report.last_analysis_date:
            ov.caveats.append("VirusTotal did not return an analysis date for this report.")
    return ov


def submission_privacy_notes(url: str) -> list[str]:
    """Plain-language notes shown BEFORE a URL is submitted for a new analysis."""
    notes = [
        "The full URL text will be sent to VirusTotal, a third-party service.",
        "VirusTotal shares submissions with its security community, so others may see this URL.",
        "CyberShield AI never visits the URL. VirusTotal's own scanners may request it.",
    ]
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
    except ValueError:
        return notes
    if parts.query:
        notes.append("This URL has query parameters. They can contain session tokens, "
                     "email addresses, reset codes or other private data.")
    if parts.username is not None or "@" in parts.netloc:
        notes.append("This URL contains text before an '@' that may be a username or password.")
    if parts.fragment:
        notes.append("This URL has a fragment (#...) that may carry private data.")
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            notes.append("This points to a private or local address. VirusTotal cannot reach it, "
                         "and submitting it would only reveal your internal address.")
    except ValueError:
        if host == "localhost" or host.endswith((".local", ".internal", ".lan")):
            notes.append("This looks like an internal hostname. VirusTotal cannot reach it.")
    return notes
