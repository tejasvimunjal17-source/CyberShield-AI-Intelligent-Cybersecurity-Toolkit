"""QR Code Generator page.

Single column so it works on a phone: Content, then the Preview, then collapsed setting groups,
then Export. The preview and every download come from the same pipeline (qr_tools.exporter), so
what you see is what you download. Everything runs locally: nothing is sent to any service and no
URL in the content is ever opened.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date, time

import streamlit as st

from components.compat import BUTTON_STRETCH
from components.header import page_header
from qr_tools import exporter as ex
from qr_tools import geometry as geo
from qr_tools import payloads as pl
from qr_tools.design import (COLOR_PRESETS, EC_LABELS, FILL_LABELS, FRAME_LABELS, MAX_LOGO_FRACTION, MIN_LOGO_FRACTION,
                             STYLE_PRESET_NOTES, STYLE_PRESETS, TEXT_SIZES, Design, auto_label_color, check_logo,
                             normalize_hex)
from qr_tools.generator import ERROR_LEVELS, QRError

MAX_LOGO_BYTES = 1024 * 1024
SIZE_LABELS = {"Small (512 px)": 512, "Medium (768 px)": 768, "Large (1024 px)": 1024,
               "Extra large (2048 px)": 2048, "Print (4096 px)": 4096}
CTA_CHOICES = ("Scan Me", "Visit Website", "View Menu", "Contact Us", "Follow Us", "Custom text")
K = "qrg_"                                    # widget key prefix


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------
def _memo(slot: str, key, fn):
    """Remember the latest result per slot so unrelated reruns do not regenerate anything."""
    cache = st.session_state.setdefault(K + "memo", {})
    if cache.get(slot, (None,))[0] != key:
        cache[slot] = (key, fn())
    return cache[slot][1]


def _color(label: str, default: str, key: str) -> str:
    """Color picker plus an optional hex box that overrides it. Invalid hex is reported next to the field."""
    picked = st.color_picker(label, default, key=K + key)
    typed = st.text_input(f"{label}: hex value (optional)", key=K + key + "_hex", max_chars=7, placeholder="#RRGGBB")
    if typed.strip():
        try:
            return normalize_hex(typed, label)
        except QRError as exc:
            st.error(str(exc) + " The color picker value is used until this is fixed.")
    return picked


def _field(f: pl.Field, type_id: str):
    key = f"{K}f_{type_id}_{f.key}"
    if f.kind == "area":
        return st.text_area(f.label, key=key, max_chars=f.max_chars, help=f.help or None)
    if f.kind == "password":
        return st.text_input(f.label, key=key, type="password", max_chars=f.max_chars, help=f.help or None)
    if f.kind == "select":
        opts = list(f.options)
        return st.selectbox(f.label, opts, index=opts.index(f.default) if f.default in opts else 0, key=key)
    if f.kind == "check":
        return st.checkbox(f.label, key=key, help=f.help or None)
    if f.kind == "date":
        return st.date_input(f.label, value=date.today(), key=key)
    if f.kind == "time":
        return st.time_input(f.label, value=time(10, 0) if f.key == "end_time" else time(9, 0), key=key)
    return st.text_input(f.label, key=key, max_chars=f.max_chars, placeholder=f.placeholder or None, help=f.help or None)


def _content() -> tuple[str, str, str, list[str]]:
    """Render the content form. Returns (payload, type label, error message, notes)."""
    category = st.selectbox("Category", pl.CATEGORIES, key=K + "category")
    types = [t for t in pl.CONTENT_TYPES if t.category == category]
    labels = [t.label for t in types]
    # One key per category: a stale selection from another category can never be fed to this list.
    picked = st.selectbox("Content type", labels, key=f"{K}type_{category}")
    chosen = types[labels.index(picked)] if picked in labels else types[0]
    if chosen.note:
        st.info(chosen.note)
    values: dict = {}
    all_day = False
    for f in chosen.fields:
        if chosen.id == "calendar" and f.key in ("start_time", "end_time", "utc") and all_day:
            continue
        values[f.key] = _field(f, chosen.id)
        if chosen.id == "calendar" and f.key == "all_day":
            all_day = bool(values[f.key])
    typed_anything = any(isinstance(v, str) and v.strip() for v in values.values())
    if not typed_anything:                      # nothing entered yet: no error, and no code
        return "", chosen.label, "", []
    try:
        payload, notes = pl.build(chosen.id, values)
        return payload, chosen.label, "", notes
    except QRError as exc:
        return "", chosen.label, str(exc), []


# --------------------------------------------------------------------------
# Setting groups
# --------------------------------------------------------------------------
def _design_group() -> dict:
    with st.expander("Design & Appearance"):
        preset = st.selectbox("Style preset", list(STYLE_PRESETS), key=K + "style_preset",
                              help="Presets use only shapes that were read back successfully in testing.")
        if STYLE_PRESETS[preset]:
            st.caption(STYLE_PRESET_NOTES[preset])
            return dict(STYLE_PRESETS[preset])
        pattern = st.selectbox("Data module shape", list(geo.PATTERNS), format_func=geo.PATTERN_LABELS.get, key=K + "pattern")
        outer = st.selectbox("Outer marker (corner frame)", list(geo.EYE_OUTER), format_func=geo.EYE_OUTER_LABELS.get,
                             key=K + "eye_outer")
        inner = st.selectbox("Inner marker (centre)", list(geo.EYE_INNER), format_func=geo.EYE_INNER_LABELS.get,
                             key=K + "eye_inner")
        st.caption("The three position markers always stay in their corners so the code remains recognisable. "
                   "Decorative shapes can reduce scan reliability; the check below tells you what was read back.")
        return dict(pattern=pattern, eye_outer=outer, eye_inner=inner)


def _color_group() -> dict:
    with st.expander("Colors & Gradients"):
        preset = st.selectbox("Color preset", list(COLOR_PRESETS), key=K + "color_preset")
        if COLOR_PRESETS[preset] is not None:
            vals = dict(COLOR_PRESETS[preset])
        else:
            fill = st.selectbox("Foreground fill", list(FILL_LABELS), format_func=FILL_LABELS.get, key=K + "fill")
            fg = _color("Foreground", "#000000", "fg")
            fg2 = _color("Second gradient color", "#0B1F4D", "fg2") if fill != "solid" else fg
            bg = _color("Background", "#FFFFFF", "bg")
            vals = dict(fill=fill, fg=fg, fg2=fg2, bg=bg, eye_outer_color=None, eye_inner_color=None)
            if not st.checkbox("Markers use the foreground color", value=True, key=K + "eyes_match"):
                vals["eye_outer_color"] = _color("Outer marker color", fg, "eye_o")
                vals["eye_inner_color"] = _color("Inner marker color", fg, "eye_i")
        vals["transparent"] = st.checkbox("Transparent background (PNG, TIFF, SVG, PDF)", key=K + "transparent",
                                          help="JPG cannot be transparent: it is filled with the background color.")
        st.caption("Keep strong contrast: dark modules on a light background scan best. Background images are not offered "
                   "because they cannot be made reliably scannable.")
        return vals


def _logo_group() -> dict:
    with st.expander("Logo & Branding"):
        up = st.file_uploader("Logo (optional, PNG or JPG, up to 1 MB)", type=["png", "jpg", "jpeg"], key=K + "logo")
        out: dict = dict(logo_bytes=None)
        if up is None:
            return out
        if up.size > MAX_LOGO_BYTES:
            st.error("Logo is larger than 1 MB.")
            return out
        data = up.getvalue()
        try:
            fmt, size = check_logo(data)                 # judged by file CONTENT, not the file name
        except QRError as exc:
            st.error(str(exc))
            return out
        st.image(data, caption=f"{fmt}, {size[0]} x {size[1]} px", width=96)
        pct = st.slider("Logo size (% of code width)", int(MIN_LOGO_FRACTION * 100), int(MAX_LOGO_FRACTION * 100), 12,
                        key=K + "logo_pct", help="Around 10 to 15% is usually safe. Larger logos can make the code unreadable.")
        margin = st.slider("Clear space around the logo (modules)", 0, 3, 1, key=K + "logo_margin")
        out.update(logo_bytes=data, logo_fraction=pct / 100.0, logo_margin=margin)
        st.caption("The logo is centred. Modules under it are removed, and error correction has to cover them.")
        return out


def _frame_group() -> dict:
    with st.expander("Frames & CTA"):
        frame = st.selectbox("Frame", list(FRAME_LABELS), format_func=FRAME_LABELS.get, key=K + "frame")
        out: dict = dict(frame=frame)
        if frame == "none":
            return out
        choice = st.selectbox("Label", CTA_CHOICES, key=K + "cta_choice")
        text = st.text_input("Custom label text", key=K + "cta_custom", max_chars=geo.CTA_MAX_CHARS) \
            if choice == "Custom text" else choice
        size = st.selectbox("Label size", list(TEXT_SIZES), index=1, format_func=str.title, key=K + "cta_size")
        bold = st.checkbox("Bold label", value=True, key=K + "cta_bold")
        frame_color = _color("Frame color", "#0B1628", "frame_color")
        padding = st.slider("Frame padding (modules)", 1, 6, 2, key=K + "frame_pad")
        out.update(cta_text=text, cta_size=size, cta_bold=bold, frame_color=frame_color, frame_padding=padding)
        if st.checkbox("Choose the label color automatically", value=True, key=K + "cta_auto"):
            out["cta_color"] = None
        else:
            out["cta_color"] = _color("Label color", "#FFFFFF", "cta_color")
        st.caption("The frame and label sit outside the code and its quiet zone, so they never cover it.")
        return out


def _tech_group(has_logo: bool) -> dict:
    with st.expander("Technical Settings"):
        ec = st.selectbox("Error correction", list(ERROR_LEVELS), index=1, format_func=EC_LABELS.get, key=K + "ec",
                          help="Higher levels add redundancy and make denser codes. They do not guarantee a successful scan.")
        raise_ec = False
        if has_logo and ec in ("L", "M"):
            raise_ec = st.checkbox("Use level H because a logo is set (recommended)", value=True, key=K + "ec_auto")
            if not raise_ec:
                st.warning("A logo hides part of the code. Level Q or H is recommended.")
        quiet = st.slider("Quiet zone (blank border, in modules)", 1, 10, 4, key=K + "quiet",
                          help="Scanners need blank space around the code to find its edges. 4 modules is the standard.")
        st.caption("The quiet zone is blank space around the code. Cutting it below 4 modules can stop scanners from finding the code.")
        size_label = st.selectbox("Output size", list(SIZE_LABELS), index=1, key=K + "size")
        return dict(error_correction="H" if raise_ec else ec, quiet_zone=quiet, target_px=SIZE_LABELS[size_label])


def _reset_to_safe() -> None:
    """Callback: return style and color widgets to the most reliable settings (content and logo are kept)."""
    ss = st.session_state
    ss[K + "style_preset"] = "Classic"
    ss[K + "color_preset"] = "Classic black and white"
    ss[K + "transparent"] = False
    ss[K + "frame"] = "none"


def build_design() -> Design:
    """Collect every setting group into one Design (not yet validated)."""
    parts: dict = {}
    parts.update(_design_group())
    parts.update(_color_group())
    logo = _logo_group()
    parts.update(logo)
    frame = _frame_group()
    parts.update(_tech_group(logo.get("logo_bytes") is not None))
    cta_color = frame.pop("cta_color", None)
    parts.update(frame)
    design = Design(**parts)
    if frame.get("frame", "none") != "none":
        color = cta_color or auto_label_color(design.frame, design.frame_color, design.bg, design.transparent)
        design = replace(design, cta_color=color)
    return design


# --------------------------------------------------------------------------
# Page
# --------------------------------------------------------------------------
def render() -> None:
    page_header("QR Code Generator",
                "Everything here runs locally. The preview and the download use the same settings.")
    st.caption("A QR code holds text, usually a URL. It cannot contain a PDF or DOCX; link to a hosted copy instead.")

    st.subheader("Content")
    payload, type_label, payload_error, notes = _content()
    if payload:
        st.caption(f"Content type: {type_label} · {len(payload)} characters")
        st.code(pl.readable_preview(payload), language=None)
    for n in notes:
        st.caption(n)
    if payload_error:
        st.error(payload_error)

    st.subheader("Preview")
    preview_box = st.container()          # filled below, once the settings are known

    try:
        design = build_design().validate()
    except QRError as exc:
        preview_box.error(str(exc))
        return

    with preview_box:
        if not payload:
            st.info(payload_error or "Enter your content above to see the QR code.")
            return
        try:
            png, w, h = _memo("preview", (payload, design), lambda: ex.preview_png(payload, design))
        except QRError as exc:
            st.error(str(exc))
            return
        st.image(png, caption=f"{w} x {h} px preview, error correction {design.error_correction}, "
                              f"quiet zone {design.quiet_zone} modules")
        for msg in ex.warnings_for(payload, design):
            st.warning(msg)
        result = _memo("verify", (payload, design), lambda: ex.verify(payload, design))
        {"ok": st.success, "unreadable": st.warning, "mismatch": st.error, "unavailable": st.info}[result.status](result.message)
        decorated = (design.pattern != "square" or design.fill != "solid" or design.frame != "none"
                     or design.transparent or design.eye_outer != "square")
        if result.status in ("unreadable", "mismatch") and decorated:
            st.button("Use the most reliable style and colors", on_click=_reset_to_safe, key=K + "safe", **BUTTON_STRETCH)

    st.subheader("Export & Download")
    fmt_labels = {f.label: f.id for f in ex.FORMATS.values()}
    chosen = fmt_labels[st.selectbox("Download format", list(fmt_labels), key=K + "format")]
    st.caption(ex.FORMATS[chosen].blurb)
    st.caption(ex.NOT_OFFERED["eps"])
    for n in ex.format_notes(design, chosen):
        st.caption(n)

    ready = True
    if design.target_px >= 4096 and not ex.FORMATS[chosen].vector:
        st.caption("A 4096 px raster file is large, so it is only built when you ask for it.")
        if st.button("Prepare 4096 px file", key=K + "prepare"):
            st.session_state[K + "prepared"] = (payload, design, chosen)
        ready = st.session_state.get(K + "prepared") == (payload, design, chosen)
    if ready:
        try:
            export = _memo("export", (payload, design, chosen), lambda: ex.export(payload, design, chosen))
        except QRError as exc:
            st.error(str(exc))
            return
        st.download_button(f"Download {ex.FORMATS[chosen].label}", data=export.data, file_name=export.filename,
                           mime=export.mime, type="primary", **BUTTON_STRETCH)
        st.caption(f"{export.width_px} x {export.height_px} px · {len(export.data) / 1024:.0f} KB. "
                   "Always test-scan the downloaded file with a phone before sharing it.")

    if st.checkbox("Show HTML embed code", key=K + "embed"):
        alt = st.text_input("Alt text for the image", value="QR code", max_chars=120, key=K + "alt")
        try:
            st.code(ex.embed_html(payload, design, alt), language="html")
            st.caption("Paste this <img> tag into a web page. The vector QR code is inside the tag, so it needs no hosting.")
        except QRError as exc:
            st.info(str(exc))
