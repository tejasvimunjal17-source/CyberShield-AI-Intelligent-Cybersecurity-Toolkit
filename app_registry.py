"""Single source of truth for modules/pages.

Used by the sidebar, dashboard, CyberGuide AI navigation actions, and the
tests that keep knowledge.md in sync with what is really implemented.
Only entries with status == "implemented" have a page module.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Module:
    key: str
    title: str
    icon: str
    group: str
    status: str            # "implemented" | "planned"
    summary: str
    uses: tuple[str, ...] = ()   # optional external services: openrouter / virustotal


MODULES: tuple[Module, ...] = (
    Module("dashboard", "Overview Dashboard", "🛡️", "Platform", "implemented",
           "Service status, module list, and quick start."),
    Module("url_scanner", "URL Security Scanner", "🔗", "Analysis", "implemented",
           "Offline URL heuristics, optional VirusTotal lookup, optional AI explanation.",
           ("virustotal", "openrouter")),
    Module("file_analyzer", "File Hash Analyzer", "🧬", "Analysis", "implemented",
           "Local SHA-256/SHA-1/MD5 hashing, hash comparison, optional VirusTotal hash lookup.",
           ("virustotal",)),
    Module("qr_generator", "QR Code Generator", "▦", "QR Tools", "implemented",
           "Create URL, text, Wi-Fi and email QR codes with colors, logo, and PNG/JPG/SVG export."),
    Module("qr_analyzer", "QR Code Security Analyzer", "🔍", "QR Tools", "implemented",
           "Decode an uploaded QR image and inspect its content without opening it.",
           ("virustotal",)),
    Module("settings", "Settings & API Configuration", "⚙️", "System", "implemented",
           "Shows which services are configured and how to configure them."),
    Module("learning_center", "Security Learning Center", "📚", "Learn", "implemented",
           "Beginner lessons on phishing, URLs, hashes, QR risks, and VirusTotal results."),
    Module("about", "About CyberShield AI", "ℹ️", "System", "implemented",
           "Purpose, privacy, data sharing, and limitations."),
    # ---- planned: no page module exists yet ----
    Module("ai_assistant", "AI Security Assistant", "💬", "Planned", "planned",
           "A full-page assistant. CyberGuide AI (floating chat) covers app guidance today."),
    Module("phishing_lab", "Phishing Awareness Lab", "🎣", "Planned", "planned",
           "Interactive phishing-recognition exercises."),
    Module("reports", "Security Reports", "📄", "Planned", "planned",
           "Exportable summaries of analyses run in a session."),
)

DEFAULT_PAGE = "dashboard"


def implemented() -> tuple[Module, ...]:
    return tuple(m for m in MODULES if m.status == "implemented")


def planned() -> tuple[Module, ...]:
    return tuple(m for m in MODULES if m.status == "planned")


def get_module(key: str) -> Module | None:
    return next((m for m in MODULES if m.key == key), None)


def implemented_keys() -> list[str]:
    return [m.key for m in implemented()]
