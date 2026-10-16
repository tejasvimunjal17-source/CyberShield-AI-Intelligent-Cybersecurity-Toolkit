"""Static URL analysis. This module NEVER makes a network request.

Everything here is a *heuristic* based on the text of the URL. A heuristic
signal is not proof of malice, and the absence of signals is not proof of
safety. Verified reputation data only comes from VirusTotal
(backend/virustotal_client.py).
"""

from __future__ import annotations

import base64
import ipaddress
import re
from dataclasses import dataclass, field
from urllib.parse import parse_qsl, urlsplit

from backend.security_utils import MAX_URL_LENGTH

SEVERITY_POINTS = {"info": 0, "low": 1, "medium": 2, "high": 3}

URL_SHORTENERS = frozenset({
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "is.gd", "buff.ly",
    "rebrand.ly", "cutt.ly", "shorturl.at", "tiny.cc", "rb.gy", "lnkd.in",
})

SUSPICIOUS_KEYWORDS = (
    "login", "signin", "verify", "update", "secure", "account", "password",
    "confirm", "banking", "wallet", "invoice", "suspended", "unlock",
)

# A small, illustrative brand list for look-alike checks (not exhaustive).
BRAND_NAMES = (
    "paypal", "google", "microsoft", "apple", "amazon", "facebook",
    "netflix", "instagram", "whatsapp", "linkedin", "dropbox",
)

# TLDs frequently seen in throwaway domains. Many legitimate sites use some
# of these too, so this is only ever a low-severity signal.
RISKY_TLDS = frozenset({"zip", "mov", "tk", "ml", "ga", "cf", "gq", "top", "xyz", "click"})

# Minimal set of two-part public suffixes so "evil.co.uk" is not mistaken for
# a registered domain called "co.uk". Not a full Public Suffix List.
_TWO_PART_SUFFIXES = frozenset({"co.uk", "org.uk", "ac.uk", "com.au", "co.in", "co.jp", "com.br"})

_CONTROL_OR_SPACE = re.compile(r"[\s\x00-\x1f\x7f]")


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str  # info | low | medium | high
    title: str
    detail: str


@dataclass
class UrlAnalysis:
    original: str
    valid: bool
    error: str = ""
    normalized: str = ""
    scheme: str = ""
    hostname: str = ""
    registered_domain: str = ""
    port: int | None = None
    findings: list[Finding] = field(default_factory=list)

    @property
    def score(self) -> int:
        return sum(SEVERITY_POINTS[f.severity] for f in self.findings)

    @property
    def signal_level(self) -> str:
        """Wording deliberately avoids 'safe' / 'malicious'."""
        if not self.valid:
            return "Could not analyze"
        if self.score >= 5:
            return "Many suspicious signals"
        if self.score >= 2:
            return "Some suspicious signals"
        return "No strong heuristic signals"

    @property
    def defanged(self) -> str:
        return defang(self.normalized or self.original)


def defang(url: str) -> str:
    """Make a URL non-clickable for safe display/sharing."""
    return url.replace("http", "hxxp", 1).replace(".", "[.]")


def virustotal_url_id(url: str) -> str:
    """VirusTotal's URL identifier: URL-safe base64 without padding."""
    return base64.urlsafe_b64encode(url.encode("utf-8")).decode("ascii").rstrip("=")


def _registered_domain(hostname: str) -> str:
    labels = hostname.split(".")
    if len(labels) <= 2:
        return hostname
    if ".".join(labels[-2:]) in _TWO_PART_SUFFIXES and len(labels) >= 3:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def _invalid(original: str, error: str) -> UrlAnalysis:
    return UrlAnalysis(original=original, valid=False, error=error)


def analyze_url(raw: str) -> UrlAnalysis:
    original = (raw or "").strip()
    if not original:
        return _invalid(original, "Enter a URL to analyze.")
    if len(original) > MAX_URL_LENGTH:
        return _invalid(original[:80] + "...", f"URL is longer than {MAX_URL_LENGTH} characters.")
    if _CONTROL_OR_SPACE.search(original):
        return _invalid(original, "URL contains spaces or control characters.")

    findings: list[Finding] = []
    candidate = original
    if "://" not in candidate:
        if re.match(r"^[A-Za-z][A-Za-z0-9+.\-]*:", candidate) and not re.match(r"^[^/]+:\d+(/|$)", candidate):
            return _invalid(original, "Only http and https URLs are analyzed.")
        candidate = "http://" + candidate
        findings.append(Finding(
            "no_scheme", "info", "No scheme supplied",
            "http:// was assumed so the address could be parsed. Nothing was opened.",
        ))

    try:
        parts = urlsplit(candidate)
        port = parts.port  # may raise ValueError
    except ValueError:
        return _invalid(original, "URL could not be parsed (malformed host or port).")

    scheme = parts.scheme.lower()
    if scheme not in ("http", "https"):
        return _invalid(original, "Only http and https URLs are analyzed.")

    hostname = (parts.hostname or "").lower().rstrip(".")
    if not hostname:
        return _invalid(original, "URL has no hostname.")

    # --- scheme / transport ------------------------------------------------
    if scheme == "http":
        findings.append(Finding(
            "http", "low", "Connection is not encrypted",
            "The URL uses http. Data sent to the site (including passwords) is not protected in transit.",
        ))

    # --- credentials in the URL ---------------------------------------------
    if parts.username is not None or "@" in parts.netloc:
        findings.append(Finding(
            "userinfo", "high", "Credentials or '@' in the address",
            "Text before an '@' is ignored when choosing the destination, which attackers use to "
            "make a link look like a trusted site. The real host here is '" + hostname + "'.",
        ))

    # --- host type -----------------------------------------------------------
    is_ip = False
    try:
        ip = ipaddress.ip_address(hostname)
        is_ip = True
        findings.append(Finding(
            "ip_host", "medium", "Address uses an IP instead of a domain name",
            "Legitimate public services rarely ask users to visit a bare IP address.",
        ))
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            findings.append(Finding(
                "private_ip", "info", "Private or local IP address",
                "This points at a private network address, not a public website.",
            ))
    except ValueError:
        pass

    if not is_ip:
        labels = hostname.split(".")
        if any(label.startswith("xn--") for label in labels):
            findings.append(Finding(
                "punycode", "medium", "Punycode (internationalized) hostname",
                "Hostnames starting with 'xn--' encode non-ASCII characters and can imitate "
                "well-known names (homograph attacks). Not every punycode domain is malicious.",
            ))
        elif not hostname.isascii():
            findings.append(Finding(
                "non_ascii", "medium", "Non-ASCII characters in hostname",
                "Look-alike characters from other alphabets can imitate trusted domains.",
            ))

        if hostname in URL_SHORTENERS:
            findings.append(Finding(
                "shortener", "medium", "URL shortener",
                "The final destination is hidden. Expand it with a trusted tool before trusting it.",
            ))

        if len(labels) > 4:
            findings.append(Finding(
                "many_subdomains", "low", "Unusually many subdomains",
                f"The host has {len(labels)} parts. Long chains can bury the real domain.",
            ))
        if hostname.count("-") >= 3:
            findings.append(Finding(
                "many_hyphens", "low", "Many hyphens in hostname",
                "Hostnames stuffed with hyphens are common in throwaway look-alike domains.",
            ))
        if labels[-1] in RISKY_TLDS:
            findings.append(Finding(
                "risky_tld", "low", f"Top-level domain '.{labels[-1]}' is often abused",
                "Many legitimate sites also use it, so this is only a weak signal.",
            ))

        registered = _registered_domain(hostname)
        reg_label = registered.split(".")[0]
        sub_part = hostname[: -len(registered)] if hostname.endswith(registered) else ""
        for brand in BRAND_NAMES:
            if brand in sub_part or (brand in reg_label and reg_label != brand):
                findings.append(Finding(
                    "brand_lookalike", "medium", f"Brand name '{brand}' appears in an unrelated domain",
                    f"The registered domain looks like '{registered}', not the official {brand} domain. "
                    "Look-alike domains are a common phishing technique.",
                ))
                break
    else:
        registered = hostname

    # --- keywords ---------------------------------------------------------------
    host_hits = [k for k in SUSPICIOUS_KEYWORDS if k in hostname]
    path_hits = [k for k in SUSPICIOUS_KEYWORDS if k in (parts.path or "").lower()]
    if host_hits:
        findings.append(Finding(
            "keywords_host", "low", "Account-related wording in the hostname",
            "Words like " + ", ".join(sorted(host_hits)) + " are common in phishing hosts but also in real services.",
        ))
    elif path_hits:
        findings.append(Finding(
            "keywords_path", "low", "Account-related wording in the path",
            "Words like " + ", ".join(sorted(path_hits)) + " appear in the path. Common on real sites too.",
        ))

    # --- shape --------------------------------------------------------------------
    if port not in (None, 80, 443):
        findings.append(Finding(
            "odd_port", "low", f"Non-standard port {port}",
            "Most public websites use the default web ports.",
        ))
    if len(candidate) > 150:
        findings.append(Finding(
            "long_url", "low", "Very long URL",
            f"The URL is {len(candidate)} characters long. Length can hide the destination.",
        ))
    if candidate.count("%") > 5:
        findings.append(Finding(
            "heavy_encoding", "low", "Heavy percent-encoding",
            "Lots of %XX sequences can be used to obscure the real path or parameters.",
        ))
    for _, value in parse_qsl(parts.query, keep_blank_values=True):
        if re.match(r"^https?://", value, re.I):
            findings.append(Finding(
                "embedded_url", "low", "Another URL inside the query string",
                "Parameters that contain full URLs are used for redirects. Check where it leads.",
            ))
            break

    return UrlAnalysis(
        original=original,
        valid=True,
        normalized=candidate,
        scheme=scheme,
        hostname=hostname,
        registered_domain=registered,
        port=port,
        findings=findings,
    )
