"""Copy and structure for the landing page. Plain data, no Streamlit.

Only modules that really exist are advertised. Descriptions mirror
knowledge.md and the actual behavior of each page; a test checks that every
linked page is implemented and that no planned module is mentioned.
"""

from __future__ import annotations

from dataclasses import dataclass

HERO_HEADING = "Your Smarter Cybersecurity Toolkit"
HERO_DESCRIPTION = (
    "Analyze suspicious URLs, inspect file hashes, create QR codes, and examine QR content "
    "with practical security tools and optional AI-powered guidance."
)

FEATURES_HEADING = "Everything You Need to Start Investigating"
HOW_HEADING = "How It Works"
ABOUT_HEADING = "Built for Learning, Honest About Limits"
FINAL_HEADING = "Ready to Explore CyberShield AI?"
FINAL_TEXT = "Choose a tool and start learning how to inspect potentially suspicious digital content."

HERO_CHIPS = ("URL checks", "File hashes", "QR tools")


@dataclass(frozen=True)
class Feature:
    key: str                # unique id for widget keys
    icon: str
    title: str
    description: str
    cta: str
    page: str | None        # registry key to open, or None
    open_guide: bool = False


FEATURES: tuple[Feature, ...] = (
    Feature("url_scanner", "🔗", "URL Security Scanner",
            "Checks the structure of a suspicious link with offline heuristics, without ever opening it. "
            "Can optionally add a VirusTotal reputation lookup when a key is configured.",
            "Open scanner →", "url_scanner"),
    Feature("file_analyzer", "🧬", "File Hash Analyzer",
            "Calculates SHA-256, SHA-1 and MD5 hashes locally, compares them with a published hash, "
            "and can optionally look up a hash on VirusTotal.",
            "Open analyzer →", "file_analyzer"),
    Feature("qr_generator", "▦", "QR Code Generator",
            "Creates QR codes for URLs, text, Wi-Fi and email with custom colors and an optional logo. "
            "Download as PNG, JPG or SVG.",
            "Open generator →", "qr_generator"),
    Feature("qr_analyzer", "🔍", "QR Code Security Analyzer",
            "Decodes an uploaded QR image and shows what it contains as plain text. "
            "It never opens a link automatically.",
            "Open analyzer →", "qr_analyzer"),
    Feature("cyberguide", "💬", "CyberGuide AI",
            "A floating assistant inside the app that explains the tools and helps troubleshoot. "
            "AI-written explanations are available when an OpenRouter key is configured.",
            "Meet CyberGuide AI →", None, open_guide=True),
    Feature("learning_center", "📚", "Security Learning Center",
            "Short introductory lessons on phishing, reading URLs, hashes, QR risks and "
            "interpreting VirusTotal results.",
            "Start learning →", "learning_center"),
)

STEPS: tuple[tuple[str, str], ...] = (
    ("Choose a security tool",
     "Pick the tool that fits what you want to inspect: a link, a file hash, or a QR code."),
    ("Analyze or generate",
     "Run the analysis in the app, or generate a QR code. Optional lookups and AI explanations "
     "only run when you ask for them and the services are configured."),
    ("Review and follow the guidance",
     "Read the findings together with the safety guidance shown. Treat results as hints, not verdicts: "
     "heuristics can miss threats."),
)

ABOUT_INTRO = (
    "CyberShield AI is an educational cybersecurity toolkit. It is meant to help you learn how to "
    "inspect suspicious links, files and QR codes, not to replace professional security software."
)

TRUST_NOTES: tuple[str, ...] = (
    "URL analysis uses heuristics. It can miss dangerous links and can flag harmless ones.",
    "AI explanations may be inaccurate. They are explanations, not scan results.",
    "External reputation checks depend on API configuration and availability, and may be rate-limited.",
    "The toolkit does not guarantee that a file, URL or QR code is safe. Zero detections never prove safety.",
)

FOOTER_NOTICE = (
    "For educational use. Results are guidance, not guarantees. "
    "Do not enter passwords or API keys into any field."
)
FOOTER_LINKS: tuple[tuple[str, str], ...] = (
    ("Features", "#features"), ("How it works", "#how-it-works"), ("About", "#about"),
)
