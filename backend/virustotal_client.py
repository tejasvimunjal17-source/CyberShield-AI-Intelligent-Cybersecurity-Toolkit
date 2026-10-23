"""VirusTotal API v3 client (lookups only).

Implemented from the public v3 reference:
  GET {base}/files/{sha256|sha1|md5}
  GET {base}/urls/{url_id}   (url_id = URL-safe base64 of the URL, no padding)
Auth header: x-apikey. The free public API allows 4 requests/minute and
500/day and may not be used in commercial products.

Also implemented (Part 6), URL only and always opt-in:
  POST {base}/urls            (submit a URL for a NEW analysis; form field "url")
  GET  {base}/analyses/{id}   (poll that analysis)
submit_url() refuses to run unless the caller passes confirmed=True, because
the URL text is shared with VirusTotal and its security community.

Part 7 adds opt-in FILE submission:
  POST {base}/files           (multipart upload, direct limit 32 MB)
submit_file() refuses unless confirmed=True, never sends the original file
name, and never logs content. Lookups only share the lookup identifier (a
hash, or the base64 form of the URL for URL lookups). This client never
fetches or visits a URL itself; it only talks to the configured VirusTotal
base URL.

Not implemented: comments, votes, uploads above the 32 MB direct limit.

Never raises raw requests exceptions; error messages are safe to display
and never contain the API key.
"""

from __future__ import annotations

import re
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Callable

import requests

from backend.logging_config import get_logger
from backend.security_utils import MAX_URL_LENGTH, identify_hash
from backend.url_analyzer import virustotal_url_id
from config import get_virustotal_config

logger = get_logger(__name__)

REQUEST_TIMEOUT_SECONDS = 15
PUBLIC_API_PER_MINUTE = 4
MAX_ENGINE_ROWS = 20
UPLOAD_TIMEOUT_SECONDS = 120
VT_MAX_UPLOAD_BYTES = 32 * 1024 * 1024   # VirusTotal's direct-upload ceiling
MAX_ALL_RESULT_ROWS = 150
MAX_LIST_ITEMS = 30
MAX_TEXT_CHARS = 300
_ANALYSIS_ID_RE = re.compile(r"^[A-Za-z0-9_=\-]{8,200}$")


class VirusTotalError(RuntimeError):
    """Base error. str(exc) is user-safe."""


class VirusTotalNotConfiguredError(VirusTotalError):
    pass


class VirusTotalAuthError(VirusTotalError):
    pass


class VirusTotalRateLimitError(VirusTotalError):
    pass


class VirusTotalNetworkError(VirusTotalError):
    pass


class VirusTotalInputError(VirusTotalError):
    pass


@dataclass
class VTReport:
    kind: str                      # "file" | "url"
    identifier: str
    found: bool
    malicious: int = 0
    suspicious: int = 0
    harmless: int = 0
    undetected: int = 0
    timeout: int = 0
    last_analysis_date: int | None = None
    permalink: str = ""
    flagged_engines: list[tuple[str, str, str]] = field(default_factory=list)
    # --- Part 6: optional URL-report details. Every one is "not returned"
    # (empty/None) unless VirusTotal actually sent it. ---
    report_id: str = ""
    all_results: list[tuple[str, str, str]] = field(default_factory=list)  # (engine, category, label)
    final_url: str = ""
    title: str = ""
    http_status: int | None = None
    content_type: str = ""
    categories: list[tuple[str, str]] = field(default_factory=list)  # (vendor, category)
    tags: list[str] = field(default_factory=list)
    redirection_chain: list[str] = field(default_factory=list)
    first_submission_date: int | None = None
    last_submission_date: int | None = None
    times_submitted: int | None = None
    reputation: int | None = None
    threat_names: list[str] = field(default_factory=list)
    # --- Part 7: optional FILE-report details (empty unless returned) ---
    file_type: str = ""
    file_size: int | None = None
    meaningful_name: str = ""
    names: list[str] = field(default_factory=list)
    magic: str = ""
    sha256: str = ""
    sha1: str = ""
    md5: str = ""
    threat_label: str = ""

    @property
    def total_engines(self) -> int:
        return self.malicious + self.suspicious + self.harmless + self.undetected + self.timeout

    @property
    def pending(self) -> bool:
        """Report exists but contains no engine results yet."""
        return self.found and self.total_engines == 0


class _MinuteLimiter:
    """Process-wide guard so the app doesn't burn the shared 4/min quota."""

    def __init__(self, per_minute: int = PUBLIC_API_PER_MINUTE,
                 clock: Callable[[], float] = time.monotonic):
        self.per_minute = per_minute
        self._clock = clock
        self._stamps: deque[float] = deque()

    def acquire(self) -> None:
        now = self._clock()
        while self._stamps and now - self._stamps[0] >= 60:
            self._stamps.popleft()
        if len(self._stamps) >= self.per_minute:
            wait = int(60 - (now - self._stamps[0])) + 1
            raise VirusTotalRateLimitError(
                f"Local rate guard: the free VirusTotal API allows {self.per_minute} lookups per "
                f"minute. Try again in about {wait} seconds."
            )
        self._stamps.append(now)


_limiter = _MinuteLimiter()


@dataclass
class VTSubmission:
    """Result of asking VirusTotal to analyse a URL (not yet a verdict)."""
    analysis_id: str


@dataclass
class VTAnalysis:
    """State of a submitted analysis (GET /analyses/{id})."""
    analysis_id: str
    status: str                     # queued | in-progress | completed | other text from VT
    malicious: int = 0
    suspicious: int = 0
    harmless: int = 0
    undetected: int = 0
    timeout: int = 0
    date: int | None = None
    results: list[tuple[str, str, str]] = field(default_factory=list)

    @property
    def completed(self) -> bool:
        return self.status == "completed"

    @property
    def total_engines(self) -> int:
        return self.malicious + self.suspicious + self.harmless + self.undetected + self.timeout


def _get(path: str) -> requests.Response:
    cfg = get_virustotal_config()
    if not cfg.is_configured:
        raise VirusTotalNotConfiguredError(
            "VIRUSTOTAL_API_KEY is not set. Add it to Streamlit secrets or your environment."
        )
    _limiter.acquire()
    try:
        return requests.get(
            f"{cfg.base_url.rstrip('/')}/{path.lstrip('/')}",
            headers={"x-apikey": cfg.api_key, "accept": "application/json"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.exceptions.Timeout as exc:
        raise VirusTotalNetworkError("VirusTotal did not respond in time. Try again shortly.") from exc
    except requests.exceptions.RequestException as exc:
        raise VirusTotalNetworkError("Could not reach VirusTotal. Check your connection.") from exc


def _post_form(path: str, data: dict | None = None, files: dict | None = None,
               timeout: int = REQUEST_TIMEOUT_SECONDS) -> requests.Response:
    cfg = get_virustotal_config()
    if not cfg.is_configured:
        raise VirusTotalNotConfiguredError(
            "VIRUSTOTAL_API_KEY is not set. Add it to Streamlit secrets or your environment."
        )
    _limiter.acquire()
    try:
        return requests.post(
            f"{cfg.base_url.rstrip('/')}/{path.lstrip('/')}",
            headers={"x-apikey": cfg.api_key, "accept": "application/json"},
            **({"data": data} if data is not None else {}),
            **({"files": files} if files is not None else {}),
            timeout=timeout,
        )
    except requests.exceptions.Timeout as exc:
        raise VirusTotalNetworkError("VirusTotal did not respond in time. Try again shortly.") from exc
    except requests.exceptions.RequestException as exc:
        raise VirusTotalNetworkError("Could not reach VirusTotal. Check your connection.") from exc


def _raise_for_status(status: int) -> None:
    """Map non-success HTTP statuses to user-safe errors (404 handled by callers)."""
    if status in (401, 403):
        logger.error("VirusTotal auth failure (status %s)", status)
        raise VirusTotalAuthError("VirusTotal rejected the API key. Check VIRUSTOTAL_API_KEY.")
    if status == 429:
        raise VirusTotalRateLimitError(
            "VirusTotal rate limit reached (free tier: 4/minute, 500/day). Wait and retry."
        )
    if status == 400:
        raise VirusTotalInputError("VirusTotal could not accept that input.")
    if status == 413:
        raise VirusTotalInputError("VirusTotal rejected the upload as too large.")
    if status >= 400:
        logger.error("VirusTotal request failed (status %s)", status)
        raise VirusTotalError(f"VirusTotal returned an error (HTTP {status}).")


def _clip(value, limit: int = MAX_TEXT_CHARS) -> str:
    return str(value)[:limit] if value is not None else ""


def _int_or_none(value) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _str_list(value, limit: int = MAX_LIST_ITEMS) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_clip(v) for v in value if isinstance(v, (str, int)) and str(v).strip()][:limit]


def _hex_or_empty(value, length: int) -> str:
    v = str(value).strip().lower() if isinstance(value, str) else ""
    return v if len(v) == length and all(c in "0123456789abcdef" for c in v) else ""


def _threat_classification(value) -> tuple[str, list[str]]:
    """(suggested label, popular threat names) from popular_threat_classification."""
    if not isinstance(value, dict):
        return "", []
    label = _clip(value.get("suggested_threat_label"), 120)
    names: list[str] = []
    popular = value.get("popular_threat_name")
    if isinstance(popular, list):
        for item in popular:
            if isinstance(item, dict) and isinstance(item.get("value"), str) and item["value"].strip():
                names.append(_clip(item["value"], 120))
    return label, names[:10]


def _engine_rows(results) -> list[tuple[str, str, str]]:
    """(engine, category, label) rows; tolerant of malformed entries."""
    rows: list[tuple[str, str, str]] = []
    if isinstance(results, dict):
        for engine, info in results.items():
            if isinstance(info, dict):
                rows.append((_clip(engine, 80), _clip(info.get("category") or "unknown", 40),
                             _clip(info.get("result") or "", 120)))
    order = {"malicious": 0, "suspicious": 1}
    rows.sort(key=lambda r: (order.get(r[1], 2), r[0].lower()))
    return rows[:MAX_ALL_RESULT_ROWS]


def _content_type(attrs: dict) -> str:
    headers = attrs.get("last_http_response_headers")
    if isinstance(headers, dict):
        for key, value in headers.items():
            if str(key).lower() == "content-type":
                return _clip(value, 120)
    return ""


def _parse(kind: str, identifier: str, response: requests.Response) -> VTReport:
    status = response.status_code
    if status == 404:
        return VTReport(kind=kind, identifier=identifier, found=False)
    _raise_for_status(status)

    try:
        data = response.json()["data"]
        attrs = data.get("attributes", {})
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise VirusTotalError("VirusTotal returned an unexpected response.") from exc
    if not isinstance(attrs, dict):
        raise VirusTotalError("VirusTotal returned an unexpected response.")

    stats = attrs.get("last_analysis_stats") or {}
    if not isinstance(stats, dict):
        raise VirusTotalError("VirusTotal returned an unexpected response.")

    def _n(key: str) -> int:
        value = stats.get(key, 0)
        return value if isinstance(value, int) else 0

    flagged: list[tuple[str, str, str]] = []
    results = attrs.get("last_analysis_results") or {}
    if isinstance(results, dict):
        for engine, info in results.items():
            if isinstance(info, dict) and info.get("category") in ("malicious", "suspicious"):
                flagged.append((str(engine), str(info["category"]), str(info.get("result") or "")))
    flagged.sort(key=lambda row: (row[1] != "malicious", row[0].lower()))

    object_id = str(data.get("id") or identifier)
    gui = "file" if kind == "file" else "url"
    date = attrs.get("last_analysis_date")
    extra: dict = {
        "report_id": _clip(object_id, 128),
        "all_results": _engine_rows(results),
        "tags": _str_list(attrs.get("tags")),
        "first_submission_date": _int_or_none(attrs.get("first_submission_date")),
        "last_submission_date": _int_or_none(attrs.get("last_submission_date")),
        "times_submitted": _int_or_none(attrs.get("times_submitted")),
        "reputation": _int_or_none(attrs.get("reputation")),
    }
    if kind == "url":
        cats = attrs.get("categories")
        extra.update(
            final_url=_clip(attrs.get("last_final_url"), 2048),
            title=_clip(attrs.get("title")),
            http_status=_int_or_none(attrs.get("last_http_response_code")),
            content_type=_content_type(attrs),
            categories=sorted(
                ((_clip(k, 80), _clip(v, 120)) for k, v in cats.items() if v),
                key=lambda kv: kv[0].lower(),
            )[:MAX_LIST_ITEMS] if isinstance(cats, dict) else [],
            redirection_chain=_str_list(attrs.get("redirection_chain"), 20),
            threat_names=_str_list(attrs.get("threat_names")),
        )
    else:
        label, names = _threat_classification(attrs.get("popular_threat_classification"))
        extra.update(
            file_type=_clip(attrs.get("type_description"), 80),
            file_size=_int_or_none(attrs.get("size")),
            meaningful_name=_clip(attrs.get("meaningful_name"), 200),
            names=_str_list(attrs.get("names"), 10),
            magic=_clip(attrs.get("magic"), 200),
            sha256=_hex_or_empty(attrs.get("sha256"), 64),
            sha1=_hex_or_empty(attrs.get("sha1"), 40),
            md5=_hex_or_empty(attrs.get("md5"), 32),
            threat_label=label,
            threat_names=names,
        )
    return VTReport(
        kind=kind,
        identifier=identifier,
        found=True,
        malicious=_n("malicious"),
        suspicious=_n("suspicious"),
        harmless=_n("harmless"),
        undetected=_n("undetected"),
        timeout=_n("timeout"),
        last_analysis_date=date if isinstance(date, int) else None,
        permalink=f"https://www.virustotal.com/gui/{gui}/{object_id}",
        flagged_engines=flagged[:MAX_ENGINE_ROWS],
        **extra,
    )


def lookup_hash(file_hash: str) -> VTReport:
    value = (file_hash or "").strip().lower()
    if identify_hash(value) is None:
        raise VirusTotalInputError("Enter a valid MD5, SHA-1 or SHA-256 hash (hex characters only).")
    return _parse("file", value, _get(f"files/{value}"))


def lookup_url(url: str) -> VTReport:
    value = (url or "").strip()
    if not value.lower().startswith(("http://", "https://")):
        raise VirusTotalInputError("VirusTotal URL lookups need a full http:// or https:// URL.")
    return _parse("url", value, _get(f"urls/{virustotal_url_id(value)}"))


def submit_url(url: str, *, confirmed: bool = False) -> VTSubmission:
    """Ask VirusTotal to analyse a URL (a NEW analysis, shared with a third party).

    Refuses unless confirmed=True. The caller must obtain that from an explicit
    user action after explaining the privacy implications. This function sends
    the URL text to VirusTotal only; nothing here ever requests the URL itself.
    """
    if confirmed is not True:
        raise VirusTotalInputError(
            "Submitting a URL needs explicit confirmation because it is shared with VirusTotal."
        )
    value = (url or "").strip()
    if not value.lower().startswith(("http://", "https://")):
        raise VirusTotalInputError("VirusTotal URL submission needs a full http:// or https:// URL.")
    if len(value) > MAX_URL_LENGTH:
        raise VirusTotalInputError(f"URL is longer than {MAX_URL_LENGTH} characters.")
    response = _post_form("urls", {"url": value})
    return _submission_from(response)


def _submission_from(response: requests.Response) -> VTSubmission:
    _raise_for_status(response.status_code)
    try:
        analysis_id = response.json()["data"]["id"]
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise VirusTotalError("VirusTotal returned an unexpected response.") from exc
    if not isinstance(analysis_id, str) or not _ANALYSIS_ID_RE.match(analysis_id):
        raise VirusTotalError("VirusTotal returned an unexpected response.")
    return VTSubmission(analysis_id=analysis_id)


_SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def submit_file(content: bytes, *, confirmed: bool = False, filename: str = "sample") -> VTSubmission:
    """Upload a file to VirusTotal for a NEW analysis (shared with a third party).

    Refuses unless confirmed=True: the caller must obtain that from an explicit
    user action after explaining the privacy implications. The user's original
    file name is never sent; `filename` is only a neutral label and anything
    that is not a short plain name is replaced by "sample". The content is
    never logged. Files above VT_MAX_UPLOAD_BYTES (VirusTotal's direct-upload
    limit) are refused without any request.
    """
    if confirmed is not True:
        raise VirusTotalInputError(
            "Uploading a file needs explicit confirmation because it is shared with VirusTotal."
        )
    if not isinstance(content, (bytes, bytearray)):
        raise VirusTotalInputError("File content must be provided as bytes.")
    if len(content) == 0:
        raise VirusTotalInputError("The file is empty; VirusTotal cannot analyse an empty file.")
    if len(content) > VT_MAX_UPLOAD_BYTES:
        raise VirusTotalInputError(
            f"The file is larger than VirusTotal's {VT_MAX_UPLOAD_BYTES // (1024 * 1024)} MB direct-upload limit."
        )
    name = filename if isinstance(filename, str) and _SAFE_NAME_RE.match(filename) else "sample"
    response = _post_form("files", files={"file": (name, bytes(content))}, timeout=UPLOAD_TIMEOUT_SECONDS)
    return _submission_from(response)


def get_analysis(analysis_id: str) -> VTAnalysis:
    """Read the state of a previously submitted analysis (read-only)."""
    value = (analysis_id or "").strip()
    if not _ANALYSIS_ID_RE.match(value):  # also blocks path tricks like '../'
        raise VirusTotalInputError("That is not a valid VirusTotal analysis identifier.")
    response = _get(f"analyses/{value}")
    if response.status_code == 404:
        raise VirusTotalError("VirusTotal has no analysis with that identifier (it may have expired).")
    _raise_for_status(response.status_code)
    try:
        attrs = response.json()["data"]["attributes"]
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise VirusTotalError("VirusTotal returned an unexpected response.") from exc
    if not isinstance(attrs, dict) or not isinstance(attrs.get("status"), str):
        raise VirusTotalError("VirusTotal returned an unexpected response.")
    stats = attrs.get("stats") or {}
    if not isinstance(stats, dict):
        raise VirusTotalError("VirusTotal returned an unexpected response.")

    def _n(key: str) -> int:
        v = stats.get(key, 0)
        return v if isinstance(v, int) and not isinstance(v, bool) else 0

    return VTAnalysis(
        analysis_id=value,
        status=_clip(attrs["status"], 40),
        malicious=_n("malicious"), suspicious=_n("suspicious"), harmless=_n("harmless"),
        undetected=_n("undetected"), timeout=_n("timeout"),
        date=_int_or_none(attrs.get("date")),
        results=_engine_rows(attrs.get("results")),
    )
