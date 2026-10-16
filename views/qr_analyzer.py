from __future__ import annotations

import streamlit as st

from backend.url_analyzer import analyze_url
from components.header import page_header
from config import MAX_UPLOAD_BYTES, MAX_UPLOAD_MB
from views.url_scanner import render_analysis, render_vt_section
from qr_tools.decoder import DecodeError, decode_image_bytes

KIND_NOTES = {
    "url": "A web address. Scanning it with a phone camera would usually offer to open it.",
    "wifi": "Wi-Fi credentials. Scanning would offer to join this network. Only join networks you trust.",
    "email": "An email draft. Scanning would open your mail app pre-filled.",
    "phone": "A phone number. Scanning would offer to call it.",
    "sms": "A text-message draft. Scanning would offer to send an SMS.",
    "text": "Plain text with no automatic action.",
}


def render() -> None:
    page_header("QR Code Security Analyzer",
                "Read a QR code from an image and inspect what it contains without opening anything.")
    upload = st.file_uploader(f"QR code image (PNG, JPG, WebP or BMP, up to {MAX_UPLOAD_MB} MB)",
                              type=["png", "jpg", "jpeg", "webp", "bmp"])
    if upload is None:
        st.info("Upload an image of a QR code. It is decoded locally and never sent anywhere.")
        return
    if upload.size > MAX_UPLOAD_BYTES:
        st.error(f"Image is larger than {MAX_UPLOAD_MB} MB.")
        return

    try:
        result = decode_image_bytes(upload.getvalue())
    except DecodeError as exc:
        st.error(str(exc))
        return
    if not result.found:
        st.warning(result.message + " Try a sharper, well-lit, tightly cropped image.")
        return

    st.subheader("Decoded content")
    st.code(result.text, language=None)
    st.caption(f"Type: {result.kind}. {KIND_NOTES[result.kind]}")
    st.caption("Shown as plain text. Nothing was opened or visited.")

    if result.kind == "url":
        analysis = analyze_url(result.text)
        st.subheader("URL heuristics")
        render_analysis(analysis, "qr")
        if analysis.valid:
            render_vt_section(analysis, "qr")
    else:
        st.info("No URL analysis applies to this content type.")
