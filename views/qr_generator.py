from __future__ import annotations

import streamlit as st

from components.compat import BUTTON_STRETCH

from components.header import page_header
from qr_tools import generator as gen
from qr_tools.decoder import DecodeError, decode_image_bytes

PRESETS = {
    "Classic (black on white)": ("#000000", "#FFFFFF"),
    "Navy on white": ("#0B1628", "#FFFFFF"),
    "Teal on white": ("#0F766E", "#FFFFFF"),
    "Custom": None,
}
MAX_LOGO_BYTES = 1024 * 1024
SIZES = {"Small (512 px)": 512, "Medium (768 px)": 768, "Large (1024 px)": 1024, "Extra large (2048 px)": 2048}
FORMATS = {"PNG": ("png", "image/png"), "JPG": ("jpg", "image/jpeg"), "SVG": ("svg", "image/svg+xml")}


def _payload_form() -> str:
    kind = st.selectbox("Content type", ["URL", "Text", "Wi-Fi", "Email"])
    if kind == "URL":
        return gen.build_url_payload(st.text_input("URL", placeholder="https://example.com", max_chars=1500))
    if kind == "Text":
        return gen.build_text_payload(st.text_area("Text", max_chars=gen.MAX_QR_TEXT_CHARS))
    if kind == "Wi-Fi":
        ssid = st.text_input("Network name (SSID)", max_chars=32)
        security = st.selectbox("Security", ["WPA", "WEP", "No password"])
        password = "" if security == "No password" else st.text_input("Password", type="password", max_chars=63)
        hidden = st.checkbox("Hidden network")
        return gen.build_wifi_payload(ssid, password, "nopass" if security == "No password" else security, hidden)
    return gen.build_email_payload(
        st.text_input("Email address"),
        st.text_input("Subject (optional)", max_chars=200),
        st.text_area("Body (optional)", max_chars=500),
    )


def render() -> None:
    page_header("QR Code Generator",
                "Everything here runs locally. The preview and the download use the same settings.")
    st.caption("A QR code holds text, usually a URL. It cannot contain a PDF or DOCX; link to a hosted copy instead.")

    left, right = st.columns([1, 1])
    with left:
        st.subheader("Content")
        try:
            payload = _payload_form()
            payload_error = ""
        except gen.QRError as exc:
            payload, payload_error = "", str(exc)

        st.subheader("Style")
        preset = st.selectbox("Color preset", list(PRESETS))
        if PRESETS[preset] is None:
            fg = st.color_picker("Foreground", "#000000")
            bg = st.color_picker("Background", "#FFFFFF")
        else:
            fg, bg = PRESETS[preset]
        size_label = st.selectbox("Output size", list(SIZES), index=1)
        border = st.slider("Quiet-zone border (modules)", 1, 10, 4)
        logo_file = st.file_uploader("Logo (optional, PNG or JPG, up to 1 MB)", type=["png", "jpg", "jpeg"])
        logo_bytes = None
        if logo_file is not None:
            if logo_file.size > MAX_LOGO_BYTES:
                st.error("Logo is larger than 1 MB.")
            else:
                logo_bytes = logo_file.getvalue()
        ec = st.selectbox("Error correction", list(gen.ERROR_LEVELS), index=1, disabled=logo_bytes is not None,
                          help="Higher levels survive more damage but make denser codes. A logo forces H.")
        fmt_options = ["PNG", "JPG"] + ([] if logo_bytes else ["SVG"])
        fmt = st.selectbox("Download format", fmt_options)
        if logo_bytes:
            st.caption("SVG is unavailable while a logo is set (logos are PNG/JPG only).")

    style = gen.QRStyle(foreground=fg, background=bg, target_px=SIZES[size_label],
                        border_modules=border, error_correction=ec, logo_bytes=logo_bytes)

    with right:
        st.subheader("Preview")
        if payload_error:
            st.info(payload_error)
            return
        try:
            matrix = gen.make_matrix(payload, gen.effective_error_correction(style))
            image = gen.render_image(matrix, style)
            ext, mime = FORMATS[fmt]
            data = {"PNG": lambda: gen.to_png_bytes(image), "JPG": lambda: gen.to_jpg_bytes(image),
                    "SVG": lambda: gen.to_svg_bytes(matrix, style)}[fmt]()
        except gen.QRError as exc:
            st.error(str(exc))
            return

        png_preview = gen.to_png_bytes(image)
        st.image(png_preview, caption=f"{image.width} x {image.height} px, error correction "
                                     f"{gen.effective_error_correction(style)}")
        for w in gen.style_warnings(style):
            st.warning(w)

        # Decode check on the real output (SVG is checked via its PNG rendering).
        try:
            result = decode_image_bytes(data if fmt != "SVG" else png_preview)
            if result.found and result.text == payload:
                note = " (checked on the PNG rendering of the same matrix)" if fmt == "SVG" else ""
                st.success(f"Decode check passed{note}: the image decodes to exactly your content.")
            elif result.found:
                st.error("Decode check FAILED: the image decodes to different content. Do not use it.")
            else:
                st.warning("Decode check could not read this image. Try higher contrast or error correction, "
                           "and test-scan before sharing.")
        except DecodeError as exc:
            st.info(f"Decode check unavailable: {exc}")

        st.download_button(f"Download {fmt}", data=data, file_name=f"cybershield_qr.{ext}", mime=mime,
                           type="primary", **BUTTON_STRETCH)
        st.caption("Always test-scan the downloaded file with a phone before sharing it.")
