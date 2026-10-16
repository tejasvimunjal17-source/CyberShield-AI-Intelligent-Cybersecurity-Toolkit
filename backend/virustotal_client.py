"""VirusTotal API v3 client (lookups only).

Implemented from the public v3 reference:
  GET {base}/files/{sha256|sha1|md5}
  GET {base}/urls/{url_id}   (url_id = URL-safe base64 of the URL, no padding)
Auth header: x-apikey. The free public API allows 4 requests/minute and
500/day and may not be used in commercial products.

Not implemented: file upload, URL submission, comments, votes. This client
only reads existing reports, so nothing the user types is shared beyond the
lookup identifier itself (a hash, or the URL string for URL lookups).

Never raises raw requests exceptions; error messages are safe to display
and never contain the API key.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Callable

import requests

from backend.logging_config import get_logger
from backend.security_utils import identify_hash
from backend.url_analyzer import virustotal_url_id
from config import get_virustotal_config

logger = get_logger(__name__)

REQUEST_TIMEOUT_SECONDS = 15
PUBLIC_API_PER_MINUTE = 4
MAX_ENGINE_ROWS = 20


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


def _parse(kind: str, identifier: str, response: requests.Response) -> VTReport:
    status = response.status_code
    if status == 404:
        return VTReport(kind=kind, identifier=identifier, found=False)
    if status in (401, 403):
        logger.error("VirusTotal auth failure (status %s)", status)
        raise VirusTotalAuthError("VirusTotal rejected the API key. Check VIRUSTOTAL_API_KEY.")
    if status == 429:
        raise VirusTotalRateLimitError(
            "VirusTotal rate limit reached (free tier: 4/minute, 500/day). Wait and retry."
        )
    if status == 400:
        raise VirusTotalInputError("VirusTotal could not accept that input.")
    if status >= 400:
        logger.error("VirusTotal request failed (status %s)", status)
        raise VirusTotalError(f"VirusTotal returned an error (HTTP {status}).")

    try:
        data = response.json()["data"]
        attrs = data.get("attributes", {})
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise VirusTotalError("VirusTotal returned an unexpected response.") from exc

    stats = attrs.get("last_analysis_stats") or {}

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
