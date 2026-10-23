from __future__ import annotations

import hashlib
import hmac

import streamlit as st

from backend.file_hashing import FileTooLargeError, hash_stream
from backend.security_utils import human_size, identify_hash
from backend import file_report
from backend import virustotal_client as vt
from components import file_report_ui, vt_report
from components.header import page_header
from config import MAX_UPLOAD_BYTES, MAX_UPLOAD_MB


def _vt_state(stored: dict) -> str:
    if stored.get("error") or stored.get("report") is None:
        return file_report.VT_ERROR
    report = stored["report"]
    if not report.found:
        return file_report.VT_NOT_FOUND
    if report.pending:
        return file_report.VT_PENDING
    return file_report.VT_REPORT


def _render_upload(hash_value: str, key: str, uploaded) -> None:
    """Opt-in upload of the file for a NEW analysis. Nothing is sent until the user confirms."""
    size = int(getattr(uploaded, "size", 0) or 0)
    confirm_key = f"{key}_up_confirm"
    # Consent is per file: never carry a ticked box over to a different file.
    if st.session_state.get(f"{confirm_key}_hash") != hash_value:
        st.session_state[confirm_key] = False
        st.session_state[f"{confirm_key}_hash"] = hash_value
    sub_key, status_key = f"{key}_up_sub", f"{key}_up_status"

    with st.expander("Upload this file to VirusTotal (new analysis, shares the file)"):
        blocker = file_report.upload_blocker(size)
        if blocker:
            st.error(blocker)
            return
        st.markdown("**Before you upload, understand what happens:**")
        for note in file_report.upload_privacy_notes(size):
            st.markdown(f"- {note}")
        confirmed = st.checkbox("I understand and want to upload this file to VirusTotal.", key=confirm_key)
        if st.button("Upload file to VirusTotal", key=f"{key}_up_btn", disabled=not confirmed):
            if confirmed:  # belt and braces: the client also refuses without confirmed=True
                data = uploaded.getvalue()
                if hashlib.sha256(data).hexdigest() != hash_value:
                    st.session_state[sub_key] = {
                        "hash": hash_value, "analysis_id": "",
                        "error": "The selected file changed since it was hashed. Choose it again."}
                else:
                    with st.spinner("Uploading to VirusTotal..."):
                        result, err = vt_report.safe_call(vt.submit_file, data, confirmed=True)
                    st.session_state[sub_key] = {"hash": hash_value, "error": err,
                                                 "analysis_id": result.analysis_id if result else ""}
                st.session_state.pop(status_key, None)

        sub = st.session_state.get(sub_key)
        if not sub or sub.get("hash") != hash_value:
            return
        if sub.get("error"):
            st.error(sub["error"])
            return
        st.success("VirusTotal accepted the file for analysis. This is not a verdict yet.")
        st.caption(f"Analysis ID: {sub['analysis_id']}")
        if st.button("Check analysis status", key=f"{key}_up_status_btn"):
            status, err = vt_report.safe_call(vt.get_analysis, sub["analysis_id"])
            st.session_state[status_key] = {"hash": hash_value, "status": status, "error": err}
        shown = st.session_state.get(status_key)
        if shown and shown.get("hash") == hash_value:
            if shown.get("error"):
                st.error(shown["error"])
            elif shown.get("status") is not None:
                file_report_ui.render_analysis_status(shown["status"])


def _lookup_block(hash_value: str, key: str, uploaded=None) -> None:
    """VirusTotal section. `uploaded` is only passed for a real uploaded file; a typed
    hash has no file, so no upload option is offered for it."""
    st.subheader("VirusTotal lookup")
    if not vt_report.vt_available():
        vt_report.not_configured_notice()
        return
    st.caption("External data from a third party, separate from the local hashes above. "
               "'Look up existing report' sends only the hash to VirusTotal to read a report that "
               "already exists. It never uploads the file.")
    state_key = f"{key}_result"
    if st.button("Look up existing report", key=f"{key}_btn"):
        report, err = vt_report.safe_call(vt.lookup_hash, hash_value)
        st.session_state[state_key] = {"hash": hash_value, "report": report, "error": err}
    stored = st.session_state.get(state_key)
    if not stored or stored.get("hash") != hash_value:
        return
    file_report_ui.render_file_report(stored.get("report"), _vt_state(stored),
                                      error=stored.get("error", ""), queried_hash=hash_value)
    if uploaded is not None:
        _render_upload(hash_value, key, uploaded)
    else:
        st.caption("To request a new analysis, choose the file itself in the uploader above. "
                   "A pasted hash cannot be uploaded.")


def render() -> None:
    page_header("File Hash Analyzer",
                "Calculate hashes locally. Files are read as bytes and never executed. A file is uploaded only if you explicitly confirm it.")
    uploaded = st.file_uploader(f"Choose a file (up to {MAX_UPLOAD_MB} MB)")
    if uploaded is not None:
        # file_id changes when the user picks a different file, even one with the same name and size.
        cache_key = (uploaded.name, uploaded.size, getattr(uploaded, "file_id", None))
        if st.session_state.get("hash_cache_key") != cache_key:
            try:
                if uploaded.size > MAX_UPLOAD_BYTES:
                    raise FileTooLargeError(f"File exceeds the {MAX_UPLOAD_MB} MB limit.")
                uploaded.seek(0)  # hash from the start regardless of any earlier read
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
            if result.size == 0:
                st.info("This file is empty (0 bytes). The hashes below are those of an empty file.")
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
            _lookup_block(result.sha256, "file_vt", uploaded)

    st.divider()
    st.subheader("Look up a hash without a file")
    typed = st.text_input("MD5, SHA-1 or SHA-256", max_chars=64, key="typed_hash")
    if typed.strip():
        if identify_hash(typed) is None:
            st.error("Enter a valid hex hash (32, 40 or 64 characters).")
        else:
            _lookup_block(typed.strip().lower(), "typed_vt")
