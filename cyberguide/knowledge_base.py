"""Lightweight keyword retrieval over knowledge.md.

No vector database: the document is small, so a title-weighted keyword
overlap score is enough and is easy to test and explain.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

KNOWLEDGE_PATH = Path(__file__).resolve().parent.parent / "knowledge.md"

_STOPWORDS = frozenset(
    "a an and are as at be but by can do does for from how i if in is it its me my no not of on or "
    "so than that the their then there these this to up was we what when where which who why will "
    "with you your".split()
)
_PAGE_RE = re.compile(r"^Page:\s*(\w+)\s*$", re.MULTILINE)
_SYNONYMS = {
    "qr": ("qr",), "vt": ("virustotal",), "scan": ("analyze", "scanner"),
    "phishing": ("suspicious", "url"), "link": ("url",), "website": ("url",),
    "checksum": ("hash",), "sha256": ("hash",), "md5": ("hash",),
    "api": ("key", "configure"), "secret": ("key", "configure"),
    "error": ("troubleshooting",), "broken": ("troubleshooting",),
    "fail": ("troubleshooting",), "failing": ("troubleshooting",),
    "unavailable": ("troubleshooting", "configure"),
}


@dataclass(frozen=True)
class Section:
    title: str
    body: str
    page: str | None

    @property
    def text(self) -> str:
        return f"{self.title}\n{self.body}"


def _tokens(text: str) -> list[str]:
    words = [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOPWORDS and len(w) > 1]
    expanded = list(words)
    for w in words:
        expanded.extend(_SYNONYMS.get(w, ()))
    return expanded


def parse_sections(markdown: str) -> list[Section]:
    sections: list[Section] = []
    for chunk in re.split(r"^## ", markdown, flags=re.MULTILINE)[1:]:
        title, _, body = chunk.partition("\n")
        match = _PAGE_RE.search(body)
        page = match.group(1) if match else None
        body = _PAGE_RE.sub("", body).strip()
        sections.append(Section(title.strip(), body, page))
    return sections


@lru_cache(maxsize=1)
def load_sections() -> tuple[Section, ...]:
    return tuple(parse_sections(KNOWLEDGE_PATH.read_text(encoding="utf-8")))


def retrieve(question: str, k: int = 3, sections: tuple[Section, ...] | None = None) -> list[Section]:
    """Return up to k sections ranked by relevance. Empty list if nothing matches."""
    pool = sections if sections is not None else load_sections()
    q_tokens = _tokens(question)
    if not q_tokens:
        return []
    scored: list[tuple[float, int, Section]] = []
    for index, section in enumerate(pool):
        title_tokens = set(_tokens(section.title))
        body_tokens = _tokens(section.body)
        body_counts: dict[str, int] = {}
        for t in body_tokens:
            body_counts[t] = body_counts.get(t, 0) + 1
        score = 0.0
        for t in set(q_tokens):
            if t in title_tokens:
                score += 3.0
            if t in body_counts:
                score += 1.0 + min(body_counts[t], 4) * 0.25
        if score > 0:
            scored.append((score, -index, section))
    scored.sort(reverse=True)
    return [s for _, _, s in scored[:k]]
