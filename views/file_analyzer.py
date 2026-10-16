from __future__ import annotations

import hmac

import streamlit as st

from backend.file_hashing import FileTooLargeError, hash_stream
from backend.security_utils import human_size, identify_hash
from components import vt_report
from components.header import page_header
from config import MAX_UPLOAD_BYTES, MAX_UPLOAD_MB


def _lookup_block(hash_value: str, key: str) -> None:
    st.subheader("VirusTotal lookup")
    if not vt_report.vt_available():
        vt_report.not_configured_notice()
        return
    st.caption("Only the hash is sent to VirusTotal, never the file. This app does not upload files.")
    if st.button("Look up on VirusTotal", key=f"{key}_btn"):
        st.session_state[key] = (hash_value, vt_report.run_lookup("file", hash_value))
    stored = st.session_state.get(key)
    if stored and stored[0] == hash_value and stored[1] is not None:
        vt_report.render_report(stored[1])


def render() -> None:
    page_header("File Hash Analyzer",
                "Calculate hashes locally. Files are read as bytes, never executed, and never uploaded.")
    uploaded = st.file_uploader(f"Choose a file (up to {MAX_UPLOAD_MB} MB)")
    if uploaded is not None:
        cache_key = (uploaded.name, uploaded.size)
        if st.session_state.get("hash_cache_key") != cache_key:
            try:
                st.session_state["hash_result"] = hash_stream(uploaded, MAX_UPLOAD_BYTES)
                st.session_state["hash_cache_key"] = cache_key
                st.session_state["hash_error"] = ""
            except FileTooLargeError as exc:
                st.session_state["hash_result"] = None
                st.session_state["hash_cache_key"] = cache_key
                st.session_state["hash_error"] = str(exc)
        if st.session_state.get("hash_error"):
            st.error(st.session_state["hash_error"])
        result = st.session_state.get("hash_result")
        if result is not None:
            st.caption(f"Size: {human_size(result.size)}")
            st.markdown("**SHA-256** (primary identifier)")
            st.code(result.sha256, language=None)
            st.markdown("**SHA-1**")
            st.code(result.sha1, language=None)
            st.markdown("**MD5**")
            st.code(result.md5, language=None)
            st.caption("A hash identifies content. It does not show whether a file is harmless or malicious.")

            st.subheader("Compare with a known hash")
            known = st.text_input("Hash published by the vendor", max_chars=64, key="known_hash")
            if known.strip():
                algo = identify_hash(known)
                if algo is None:
                    st.error("That is not a valid MD5, SHA-1 or SHA-256 hex string.")
                else:
                    mine = {"MD5": result.md5, "SHA-1": result.sha1, "SHA-256": result.sha256}[algo]
                    if hmac.compare_digest(mine, known.strip().lower()):
                        st.success(f"{algo} matches. The file is identical to what the publisher hashed.")
                    else:
                        st.error(f"{algo} does NOT match. Do not trust this file; download it again from the official source.")
            _lookup_block(result.sha256, "file_vt")

    st.divider()
    st.subheader("Look up a hash without a file")
    typed = st.text_input("MD5, SHA-1 or SHA-256", max_chars=64, key="typed_hash")
    if typed.strip():
        if identify_hash(typed) is None:
            st.error("Enter a valid hex hash (32, 40 or 64 characters).")
        else:
            _lookup_block(typed.strip().lower(), "typed_vt")
