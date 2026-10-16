"""Small shared helpers: input limits, redaction, formatting."""

from __future__ import annotations

import re

MAX_URL_LENGTH = 2048
MAX_CHAT_INPUT_CHARS = 1000
MAX_QR_TEXT_CHARS = 1500

_HASH_LENGTHS = {32: "MD5", 40: "SHA-1", 64: "SHA-256"}
_HEX_RE = re.compile(r"^[0-9a-fA-F]+$")

# Patterns for common secret shapes, used to scrub text before it is shown
# or sent to an AI provider.
_SECRET_PATTERNS = [
    re.compile(r"sk-or-[A-Za-z0-9_\-]{10,}"),          # OpenRouter-style keys
    re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),              # generic sk- keys
    re.compile(r"\b[a-fA-F0-9]{64}\b(?=.*api)", re.I),  # 64-hex next to 'api'
    re.compile(r"(?i)(api[_-]?key|token|secret)\s*[:=]\s*\S+"),
]


def clip_text(text: str, limit: int) -> str:
    """Trim whitespace and cap length."""
    return (text or "").strip()[:limit]


def redact_secrets(text: str) -> str:
    out = text or ""
    for pattern in _SECRET_PATTERNS:
        out = pattern.sub("[redacted]", out)
    return out


def identify_hash(value: str) -> str | None:
    """Return 'MD5' / 'SHA-1' / 'SHA-256' for a valid hex digest, else None."""
    v = (value or "").strip()
    if _HEX_RE.match(v):
        return _HASH_LENGTHS.get(len(v))
    return None


def human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"  # pragma: no cover
