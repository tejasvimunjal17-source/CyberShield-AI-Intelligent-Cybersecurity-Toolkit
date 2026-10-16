from __future__ import annotations

import streamlit as st

from components.cards import badge, info_card
from components.header import page_header
from config import (MAX_UPLOAD_MB, get_app_env, get_openrouter_config,
                    get_virustotal_config)
from backend.virustotal_client import PUBLIC_API_PER_MINUTE


def render() -> None:
    page_header("Settings & API Configuration",
                "Keys are read from environment variables or Streamlit secrets only. They cannot be entered or shown here.")
    orc, vtc = get_openrouter_config(), get_virustotal_config()

    c1, c2 = st.columns(2)
    with c1:
        info_card("OpenRouter", "Secret name: OPENROUTER_API_KEY",
                  badge("key detected" if orc.is_configured else "not configured",
                        "ok" if orc.is_configured else "warn"))
        st.caption(f"Model in use: {orc.model}  (set OPENROUTER_MODEL to change)")
    with c2:
        info_card("VirusTotal", "Secret name: VIRUSTOTAL_API_KEY",
                  badge("key detected" if vtc.is_configured else "not configured",
                        "ok" if vtc.is_configured else "warn"))
        st.caption(f"Free tier: {PUBLIC_API_PER_MINUTE} lookups/minute, 500/day, non-commercial use only.")
    st.caption("'Detected' means a value exists. It does not prove the key is valid; that is only learned when a request is made.")

    st.subheader("How to set a key")
    st.markdown(
        "- **Local:** copy `.env.example` to `.env` (or `.streamlit/secrets.toml.example` to "
        "`.streamlit/secrets.toml`) and fill in the values. Both files are git-ignored.\n"
        "- **Streamlit Community Cloud:** App settings, then Secrets. Paste the same names and values, save, and reboot the app.\n"
        "- Names must match exactly. Remove stray spaces and quotes.\n"
        "- Never commit real keys to GitHub. If a key was exposed, revoke it and create a new one."
    )

    st.subheader("Current limits")
    st.markdown(f"- Upload limit: {MAX_UPLOAD_MB} MB (files and QR images)\n"
                "- URL length: 2048 characters\n- CyberGuide AI input: 1000 characters per message\n"
                f"- Environment: {get_app_env()}")

    st.subheader("Troubleshooting")
    with st.expander("VirusTotal buttons are disabled or failing"):
        st.markdown("Check the status above. If 'not configured', the secret name is wrong or the app was not rebooted. "
                    "'Rejected the API key' means the key is invalid. Rate-limit messages mean the free quota is used up.")
    with st.expander("CyberGuide AI says it is showing documentation"):
        st.markdown("The AI was not used. The note under the answer states why (missing key, rejected key, "
                    "invalid model id, rate limit, or network). Local documentation answers still work.")
