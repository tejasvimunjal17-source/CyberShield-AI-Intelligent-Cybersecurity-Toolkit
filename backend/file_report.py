"""Wording, cross-checks and upload safeguards for the File Hash Analyzer (Part 7).

Pure functions: no Streamlit, no network. As in backend/url_report.py, local
facts (the hashes computed in this app) and VirusTotal reputation data are kept
apart and never merged into one verdict. Zero detections is never "safe", and a
missing report or failed lookup is never "clean".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from backend.security_utils import human_size, identify_hash
from backend.url_report import (  # shared state constants and time helpers
    STALE_AFTER_DAYS, VT_ERROR, VT_NOT_CONFIGURED, VT_NOT_FOUND, VT_NOT_REQUESTED,
    VT_PENDING, VT_REPORT, VtHeadline, format_utc, is_stale, relative_age,
)
from backend.virustotal_client import VT_MAX_UPLOAD_BYTES, VTReport
from config import MAX_UPLOAD_BYTES

# Largest file this app will even offer to upload: the lower of the app's own
# limit and VirusTotal's direct-upload ceiling.
UPLOAD_LIMIT_BYTES = min(MAX_UPLOAD_BYTES, VT_MAX_UPLOAD_BYTES)

__all__ = [
    "VT_ERROR", "VT_NOT_CONFIGURED", "VT_NOT_FOUND", "VT_NOT_REQUESTED", "VT_PENDING", "VT_REPORT",
    "UPLOAD_LIMIT_BYTES", "FileOverview", "compose_overview", "file_headline", "hash_match_status",
    "upload_blocker", "upload_privacy_notes", "format_utc", "relative_age",
]


def file_headline(report: VTReport) -> VtHeadline:
    """One factual sentence describing the vendor results of a found file report."""
    total = report.total_engines
    if report.pending:
        return VtHeadline("neutral", "A report exists but has no vendor results yet.",
                          "Analysis may still be pending. Check again later.")
    if report.malicious:
        extra = f" and {report.suspicious} as suspicious" if report.suspicious else ""
        return VtHeadline(
            "bad",
            f"{report.malicious} of {total} vendor results flagged this file as malicious{extra}.",
            "Do not open or run the file until you have verified it another way. Individual vendors "
            "can be wrong, so check which vendors flagged it in the Detection tab.",
        )
    if report.suspicious:
        return VtHeadline(
            "warn",
            f"{report.suspicious} of {total} vendor results flagged this file as suspicious.",
            "No vendor called it malicious, but suspicious flags deserve caution.",
        )
    return VtHeadline(
        "info",
        "No security vendors flagged this file as malicious or suspicious in the latest analysis.",
        "This is not proof the file is safe. New, packed or targeted malware is often missed at first.",
    )


def hash_match_status(report: VTReport | None, queried_hash: str) -> bool | None:
    """Does the report VirusTotal returned actually contain the hash we asked about?

    True / False when VirusTotal returned at least one hash to compare, None when
    it returned none (nothing to cross-check). A False result should be shown as a
    warning: the report may not describe the file the user has.
    """
    if report is None or not report.found:
        return None
    returned = {h for h in (report.sha256, report.sha1, report.md5) if h}
    if not returned:
        return None
    q = (queried_hash or "").strip().lower()
    if identify_hash(q) is None:
        return None
    return q in returned


@dataclass
class FileOverview:
    vt_state: str
    vt_headline: str = ""
    vt_detail: str = ""
    vt_tone: str = "neutral"
    last_analysis_utc: str = ""
    last_analysis_age: str = ""
    caveats: list[str] = field(default_factory=list)


def compose_overview(
    vt_state: str,
    report: VTReport | None = None,
    error: str = "",
    queried_hash: str = "",
    now: datetime | None = None,
) -> FileOverview:
    ov = FileOverview(vt_state=vt_state)
    ov.caveats.append(
        "A hash identifies a file's exact bytes. It says nothing about whether the file is harmful."
    )
    if vt_state == VT_NOT_CONFIGURED:
        ov.vt_headline = "VirusTotal is not configured, so no reputation data is available."
        ov.vt_detail = "Local hashing still works."
    elif vt_state == VT_NOT_REQUESTED:
        ov.vt_headline = "No VirusTotal lookup has been requested yet."
    elif vt_state == VT_ERROR:
        ov.vt_headline = "The VirusTotal lookup failed, so there is no reputation data."
        ov.vt_detail = (error or "Unknown error.") + " A failed lookup says nothing about the file."
    elif vt_state == VT_NOT_FOUND:
        ov.vt_headline = "VirusTotal has no existing report for this hash."
        ov.vt_detail = ("That is not a verdict. It only means nobody has submitted this exact file, "
                        "which can mean the file is rare, new or private.")
    elif vt_state in (VT_PENDING, VT_REPORT) and report is not None:
        h = file_headline(report)
        ov.vt_headline, ov.vt_detail, ov.vt_tone = h.headline, h.detail, h.tone
        if vt_state == VT_REPORT:
            if report.last_analysis_date:
                ov.last_analysis_utc = format_utc(report.last_analysis_date)
                ov.last_analysis_age = relative_age(report.last_analysis_date, now)
                if is_stale(report.last_analysis_date, now):
                    ov.caveats.append(
                        f"This VirusTotal analysis is more than {STALE_AFTER_DAYS} days old. "
                        "Detection coverage may have improved since."
                    )
            else:
                ov.caveats.append("VirusTotal did not return an analysis date for this report.")
            if hash_match_status(report, queried_hash) is False:
                ov.caveats.append(
                    "WARNING: the hashes VirusTotal returned do not include the hash you looked up. "
                    "Do not treat this report as describing your file."
                )
    return ov


def upload_blocker(size: int) -> str:
    """Reason an upload must not be offered, or '' when it is allowed."""
    if size <= 0:
        return "The file is empty (0 bytes). VirusTotal cannot analyse an empty file."
    if size > UPLOAD_LIMIT_BYTES:
        return (f"The file is {human_size(size)}, above the {human_size(UPLOAD_LIMIT_BYTES)} limit "
                "for uploads from this app (VirusTotal's direct-upload ceiling is 32 MB).")
    return ""


def upload_privacy_notes(size: int) -> list[str]:
    """Plain-language notes shown BEFORE a file is uploaded for a new analysis."""
    return [
        f"The entire file ({human_size(size)}) will be uploaded to VirusTotal, a third-party service.",
        "VirusTotal shares submitted files and their analysis results with its security community, "
        "including security vendors and, for some customers, the file itself. Anything inside the file "
        "may become visible to them.",
        "Do not upload files containing personal, confidential, customer or employer data.",
        "An upload cannot be taken back by this app.",
        "Your original file name is not sent. The file is never executed here.",
        "Uploading uses your VirusTotal API quota (free tier: 4 requests per minute, 500 per day).",
    ]
