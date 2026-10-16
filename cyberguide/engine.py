"""CyberGuide AI answer engine.

Honesty rules enforced here, not just in the prompt:
- Answers are labeled as AI-generated or documentation-based.
- The model is told which services are configured (booleans only) and that
  it cannot run tools or test connections.
- Secret-like text is redacted from user input before it goes anywhere.
- If the AI is unavailable the user still gets the retrieved documentation,
  with the reason stated.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from backend import openrouter_client as orc
from backend.logging_config import get_logger
from backend.security_utils import MAX_CHAT_INPUT_CHARS, clip_text, redact_secrets
from cyberguide.knowledge_base import Section, retrieve

logger = get_logger(__name__)

MAX_HISTORY_TURNS = 6
MAX_DOC_CHARS_PER_SECTION = 1800

SYSTEM_PROMPT = """You are CyberGuide AI, the in-app guide for CyberShield AI, an educational cybersecurity toolkit.

Rules:
- Answer ONLY from the DOCUMENTATION and APP STATUS provided below. If they do not cover the question, say you don't have documentation for it. Do not invent features, settings, page names, or buttons.
- Features marked "planned" are NOT available. Say so plainly.
- You cannot run scans, open URLs, read files, or test API connections. Never say or imply that you did. You only explain how to use the tools. Scan results appear only on the tool pages after the user presses a button.
- APP STATUS tells you whether API keys are detected as set (true/false). That is all you know about configuration. Never ask users for API keys or passwords; if they paste one, tell them to rotate it.
- Never say a URL, file, or QR code is safe or malicious. Zero detections or no heuristic signals do not prove safety.
- Be concise: short steps, plain language, define jargon briefly. The user may be a beginner.
- Your answers are explanations, not scan results."""


@dataclass
class GuideAnswer:
    text: str
    source: str                      # "ai" | "documentation"
    pages: list[str] = field(default_factory=list)
    notice: str = ""                 # why AI was not used, or redaction warning


def _format_docs(sections: list[Section]) -> str:
    return "\n\n".join(f"### {s.title}\n{s.body[:MAX_DOC_CHARS_PER_SECTION]}" for s in sections)


def _status_text(status: dict[str, bool]) -> str:
    return (
        f"OPENROUTER_API_KEY detected: {status.get('openrouter', False)}\n"
        f"VIRUSTOTAL_API_KEY detected: {status.get('virustotal', False)}"
    )


def _documentation_answer(sections: list[Section], reason: str) -> GuideAnswer:
    if not sections:
        return GuideAnswer(
            text=("I couldn't find anything about that in the CyberShield AI documentation. "
                  "Try asking about the QR generator, URL scanner, file hashing, VirusTotal, "
                  "or API configuration."),
            source="documentation", notice=reason,
        )
    top = sections[:2]
    text = "\n\n".join(f"**{s.title}**\n{s.body[:MAX_DOC_CHARS_PER_SECTION]}" for s in top)
    pages = [s.page for s in top if s.page]
    return GuideAnswer(text=text, source="documentation", pages=list(dict.fromkeys(pages)), notice=reason)


def answer(question: str, history: list[dict] | None = None,
           status: dict[str, bool] | None = None) -> GuideAnswer:
    status = status or {}
    cleaned = clip_text(question, MAX_CHAT_INPUT_CHARS)
    redacted = redact_secrets(cleaned)
    redaction_notice = ""
    if redacted != cleaned:
        redaction_notice = ("Part of your message looked like a secret and was removed. "
                            "Never share API keys in chat; rotate any key you pasted.")
    if not redacted:
        return GuideAnswer("Ask me about a tool, a setting, or an error message.", "documentation")

    sections = retrieve(redacted, k=3)
    pages = list(dict.fromkeys(s.page for s in sections if s.page))

    messages = [{"role": "system", "content": (
        f"{SYSTEM_PROMPT}\n\nAPP STATUS:\n{_status_text(status)}\n\nDOCUMENTATION:\n"
        f"{_format_docs(sections) or '(no matching documentation)'}"
    )}]
    for turn in (history or [])[-MAX_HISTORY_TURNS:]:
        if turn.get("role") in ("user", "assistant") and isinstance(turn.get("content"), str):
            messages.append({"role": turn["role"],
                             "content": redact_secrets(clip_text(turn["content"], 2000))})
    messages.append({"role": "user", "content": redacted})

    try:
        text = orc.chat_completion(messages)
    except orc.OpenRouterNotConfiguredError:
        result = _documentation_answer(sections, "AI is not configured (OPENROUTER_API_KEY not set), so this is documentation text.")
    except orc.OpenRouterError as exc:
        result = _documentation_answer(sections, f"AI unavailable: {exc} Showing documentation instead.")
    else:
        result = GuideAnswer(text=text, source="ai", pages=pages)

    if redaction_notice:
        result.notice = (result.notice + " " + redaction_notice).strip()
    return result
