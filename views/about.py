from __future__ import annotations

import streamlit as st

from components.header import page_header
from config import APP_NAME, APP_TAGLINE


def render() -> None:
    page_header(f"About {APP_NAME}", APP_TAGLINE)
    st.write("CyberShield AI is an educational cybersecurity toolkit built with Python and Streamlit. "
             "It brings practical analysis tools and learning material into one app.")

    st.subheader("What stays on this server and what leaves it")
    st.table([
        {"Action": "URL heuristics, hashing, QR generate/decode", "Sent to third parties": "Nothing"},
        {"Action": "VirusTotal lookup (button)", "Sent to third parties": "A hash, or an encoded form of the URL, to VirusTotal"},
        {"Action": "VirusTotal new analysis (button + confirmation box)", "Sent to third parties": "The URL text, or the uploaded file itself, to VirusTotal, which shares it with its security community"},
        {"Action": "CyberGuide AI / AI explanation", "Sent to third parties": "Your message (secret-like text removed), recent chat, documentation excerpts, or a hostname plus finding titles, to OpenRouter"},
        {"Action": "Uploaded files and QR images", "Sent to third parties": "QR images: never. Files: never, unless you confirm a VirusTotal upload of that file"},
    ])

    st.subheader("Limitations")
    st.markdown(
        "- URL analysis is heuristic and offline. It never opens links. No signals does not mean safe.\n"
        "- A hash identifies content; it does not say whether it is malicious.\n"
        "- VirusTotal results can lag behind new threats, and the app reads existing reports, requesting a new URL analysis only when you explicitly confirm it.\n"
        "- AI explanations can be wrong and are not scan results.\n"
        "- This toolkit does not provide complete protection or any guarantee of safety."
    )
    st.caption("Do not enter passwords or API keys into any field.")
