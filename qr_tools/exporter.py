"""One pipeline from payload + Design to every output.

    payload --make_matrix--> matrix --build_scene--> Scene --> PNG / JPG / TIFF / SVG / PDF / preview

The preview and every download come from the same Scene, so they cannot disagree about colors,
pattern, logo, error correction, quiet zone or frame. verify() re-reads the finished picture:
it samples every module to prove the data pattern survived the styling, then tries to decode
the picture with OpenCV. A failed decode is reported honestly as "could not be read by the
built-in decoder", never as proof about real phones either way.

Nothing here touches the network and nothing opens the payload.
"""

from __future__ import annotations

import base64
import html
import io
from dataclasses import dataclass, replace
from functools import lru_cache

import numpy as np
from PIL import Image

from qr_tools import generator as gen
from qr_tools.design import Design, scan_warnings
from qr_tools.generator import QRError
from qr_tools.render_pdf import render_pdf
from qr_tools.render_raster import render_raster
from qr_tools.render_svg import render_svg
from qr_tools.scene import FINDER, Scene, build_scene

DPI = 300
HTML_EMBED_MAX_BYTES = 400_000


@dataclass(frozen=True)
class Format:
    id: str
    label: str
    ext: str
    mime: str
    vector: bool
    transparency: bool
    blurb: str


FORMATS: dict[str, Format] = {f.id: f for f in (
    Format("png", "PNG", "png", "image/png", False, True,
           "Sharp raster image. Supports a transparent background. Best for websites and slides."),
    Format("jpg", "JPG", "jpg", "image/jpeg", False, False,
           "Small raster image for simple sharing. JPG cannot be transparent."),
    Format("tiff", "TIFF", "tiff", "image/tiff", False, True,
           "Lossless raster for print and archive workflows (LZW compressed)."),
    Format("svg", "SVG", "svg", "image/svg+xml", True, True,
           "Scalable vector. Stays sharp at any size. Best for print and design tools."),
    Format("pdf", "PDF", "pdf", "application/pdf", True, True,
           "Vector PDF sized as the PNG at 300 dpi. Print-friendly and scalable."),
)}
NOT_OFFERED = {"eps": "EPS is not offered: this build has no PostScript interpreter to check an EPS file, and the image library "
                      "can only write bitmap EPS. Use SVG or PDF for vector output."}


@dataclass(frozen=True)
class Export:
    data: bytes
    fmt: str
    mime: str
    filename: str
    width_px: int
    height_px: int
    notes: tuple[str, ...]


@dataclass(frozen=True)
class Verification:
    status: str          # ok | unreadable | mismatch | unavailable
    message: str
    structure_ok: bool = False
    decoder: str = ""


def format_notes(design: Design, fmt: str) -> list[str]:
    """Limits of a format for THIS design, shown before download. Fallbacks are explained, never silent."""
    f = FORMATS[fmt]
    notes: list[str] = []
    if design.transparent and not f.transparency:
        flat = design.bg if design.bg else "#FFFFFF"
        notes.append(f"{f.label} cannot be transparent, so the background is filled with {flat}.")
    if design.has_logo and f.vector:
        notes.append("The logo is embedded as a bitmap inside the vector file; everything else stays vector.")
    if f.id == "svg" and design.has_label:
        notes.append("The label is live text. Viewers without Helvetica/Arial substitute another sans-serif font; "
                     "its width is fixed so the layout does not change.")
    if f.id == "pdf" and design.has_label:
        notes.append("The label uses the PDF built-in Helvetica font.")
    if f.id == "jpg":
        notes.append("JPG compression adds slight noise around edges. Use PNG or SVG when the code must scan from small prints.")
    return notes


# --------------------------------------------------------------------------
# Matrix and scene
# --------------------------------------------------------------------------
@lru_cache(maxsize=16)
def _matrix(payload: str, ec: str) -> tuple[tuple[bool, ...], ...]:
    return tuple(tuple(r) for r in gen.make_matrix(payload, ec))     # looked up at call time so tests can substitute it


def clear_cache() -> None:
    _matrix.cache_clear()


def prepare(payload: str, design: Design) -> tuple[Scene, Design, list[list[bool]]]:
    """Validate and compose. Raises QRError with a user-readable message."""
    d = design.validate()
    if not (payload or "").strip():
        raise QRError("Enter some content first.")
    matrix = [list(r) for r in _matrix(payload, d.error_correction)]
    return build_scene(matrix, d), d, matrix


def warnings_for(payload: str, design: Design) -> list[str]:
    d = design.validate()
    n = None
    try:
        n = len(_matrix(payload, d.error_correction))
    except QRError:
        pass
    return scan_warnings(d, n)


# --------------------------------------------------------------------------
# Rendering to files
# --------------------------------------------------------------------------
def _flatten(img: Image.Image, color: tuple[int, int, int]) -> Image.Image:
    base = Image.new("RGB", img.size, color)
    base.paste(img, mask=img.getchannel("A"))
    return base


def _hex_rgb(c: str) -> tuple[int, int, int]:
    return int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)


def export(payload: str, design: Design, fmt: str) -> Export:
    if fmt not in FORMATS:
        raise QRError(NOT_OFFERED.get(fmt, "That download format is not supported."))
    scene, d, _ = prepare(payload, design)
    f = FORMATS[fmt]
    if fmt == "svg":
        data = render_svg(scene, d.target_px).encode("utf-8")
        w, h = _svg_size(scene, d)
    elif fmt == "pdf":
        data = render_pdf(scene, d.target_px)
        w, h = _svg_size(scene, d)
    else:
        img = render_raster(scene, d.target_px)
        w, h = img.size
        buf = io.BytesIO()
        if fmt == "png":
            img.save(buf, "PNG", optimize=True, dpi=(DPI, DPI))
        elif fmt == "jpg":
            _flatten(img, _hex_rgb(d.bg) if not d.transparent else (255, 255, 255)).save(
                buf, "JPEG", quality=95, subsampling=0, optimize=True, dpi=(DPI, DPI))
        else:
            img.save(buf, "TIFF", compression="tiff_lzw", dpi=(DPI, DPI))
        data = buf.getvalue()
    return Export(data, fmt, f.mime, f"cybershield_qr.{f.ext}", w, h, tuple(format_notes(d, fmt)))


def _svg_size(scene: Scene, d: Design) -> tuple[int, int]:
    from qr_tools.scene import pixel_box
    box = pixel_box(scene, d.target_px)
    return scene.width * box, scene.height * box


def preview_png(payload: str, design: Design, max_px: int = 1024) -> tuple[bytes, int, int]:
    """PNG bytes for on-screen preview. Transparency is shown on a checkerboard so it is visible."""
    scene, d, _ = prepare(payload, design)
    img = render_raster(scene, min(d.target_px, max_px))
    alpha = np.asarray(img.getchannel("A"))
    if alpha.min() < 255:                       # draw a checkerboard under transparent areas so they are visible
        h, w = alpha.shape
        yy, xx = np.mgrid[0:h, 0:w]
        cell = max(8, w // 40)
        check = np.where(((yy // cell) + (xx // cell)) % 2 == 0, 238, 214).astype(np.uint8)
        base = Image.fromarray(np.stack([check] * 3, axis=-1), "RGB")
        base.paste(img, mask=img.getchannel("A"))
        img = base
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "PNG")
    return buf.getvalue(), img.width, img.height


def embed_html(payload: str, design: Design, alt: str) -> str:
    """A copy-paste <img> tag with the vector SVG inlined as a data URI. Alt text is escaped; no scripts, no network."""
    ex = export(payload, design, "svg")
    if len(ex.data) > HTML_EMBED_MAX_BYTES:
        raise QRError("This design is too large for an inline embed. Host the SVG file and link to it instead.")
    uri = "data:image/svg+xml;base64," + base64.b64encode(ex.data).decode("ascii")
    return (f'<img src="{uri}" width="{ex.width_px // 2}" height="{ex.height_px // 2}" '
            f'alt="{html.escape((alt or "QR code").strip()[:120], quote=True)}">')


# --------------------------------------------------------------------------
# Verification
# --------------------------------------------------------------------------
def _luma(arr: np.ndarray) -> np.ndarray:
    return arr[..., 0] * 0.299 + arr[..., 1] * 0.587 + arr[..., 2] * 0.114


def structure_check(scene: Scene, image: Image.Image, design: Design) -> tuple[int, int]:
    """Sample every module centre in the finished picture. Returns (mismatches, modules checked).

    This proves, independently of any QR decoder, that the styling kept the data pattern: each cell
    that should be dark is dark, each that should be light is light (logo area excluded), and the three
    position markers still show the 1:1:3:1:1 pattern through their centre lines.
    """
    from qr_tools.scene import pixel_box
    box = pixel_box(scene, design.target_px)
    bg = _hex_rgb(design.bg) if not design.transparent else (255, 255, 255)
    flat = np.asarray(_flatten(image, bg), dtype=np.float32)
    lum = _luma(flat)
    b = _luma(np.array(bg, dtype=np.float32))
    fgs = [_luma(np.array(_hex_rgb(c), dtype=np.float32)) for c in design.module_colors()]
    lo, hi = min(fgs), max(fgs)

    def is_dark(px: float) -> bool:
        d_fg = 0.0 if lo <= px <= hi else min(abs(px - lo), abs(px - hi))
        return d_fg < abs(px - b)

    ox, oy = scene.origin
    n = scene.n
    dark = set(scene.modules)
    eye_cells = set()
    for ex, ey in ((0, 0), (n - 7, 0), (0, n - 7)):
        eye_cells.update((ox + ex + i, oy + ey + j) for i in range(7) for j in range(7))
    hole = scene.logo.hole if scene.logo else None
    bad = total = 0
    for y in range(n):
        for x in range(n):
            gx, gy = ox + x, oy + y
            if (gx, gy) in eye_cells:
                continue
            if hole and hole[0] <= gx < hole[0] + hole[2] and hole[1] <= gy < hole[1] + hole[3]:
                continue
            px = lum[int((gy + 0.5) * box), int((gx + 0.5) * box)]
            total += 1
            bad += is_dark(px) != ((gx, gy) in dark)
    for eye in scene.eyes:                       # centre row and centre column of each marker
        for k in range(7):
            for cx, cy in ((eye.x + k, eye.y + 3), (eye.x + 3, eye.y + k)):
                want = FINDER[3][k] == "#"
                px = lum[int((cy + 0.5) * box), int((cx + 0.5) * box)]
                total += 1
                bad += is_dark(px) != want
    return int(bad), int(total)


def _decoders():
    import cv2
    out = [("OpenCV", lambda g: cv2.QRCodeDetector().detectAndDecode(g)[0])]
    if hasattr(cv2, "QRCodeDetectorAruco"):
        out.append(("OpenCV-ArUco", lambda g: cv2.QRCodeDetectorAruco().detectAndDecode(g)[0]))
    return cv2, out


def try_decode(image: Image.Image, light_surface: bool = True) -> tuple[str, str]:
    """(decoded text, decoder name). Empty text when nothing could be read."""
    try:
        cv2, decoders = _decoders()
    except ImportError:
        return "", "unavailable"
    rgb = _flatten(image, (255, 255, 255) if light_surface else (0, 0, 0))
    gray = np.array(rgb.convert("L"))
    if not light_surface:
        gray = 255 - gray
    for pad in (False, True):
        g = cv2.copyMakeBorder(gray, 40, 40, 40, 40, cv2.BORDER_CONSTANT, value=255) if pad else gray
        for name, fn in decoders:
            try:
                text = fn(g)
            except Exception:
                text = ""
            if text:
                return text, name
    return "", ""


def verify(payload: str, design: Design) -> Verification:
    """Re-read the styled picture: structure sampling first, then an actual decode."""
    scene, d, _ = prepare(payload, design)
    img = render_raster(scene, min(d.target_px, 1024))
    probe = replace(d, target_px=min(d.target_px, 1024))
    bad, total = structure_check(scene, img, probe)
    structure_ok = bad == 0
    fg_light = sum(int(d.fg[i:i + 2], 16) for i in (1, 3, 5)) > 384
    text, which = try_decode(img, light_surface=not (d.transparent and fg_light))
    if which == "unavailable":
        return Verification("unavailable", "The built-in decoder (OpenCV) is not available, so the code could not be test-read.",
                            structure_ok)
    intended = gen.build_text_payload(payload)
    if text and text.replace("\r\n", "\n") == intended.replace("\r\n", "\n"):
        return Verification("ok", f"Test-read OK: the built-in decoder ({which}) read back exactly the intended content. "
                                  "This is not a guarantee for every phone or scanner.", structure_ok, which)
    if text:
        return Verification("mismatch", "The picture decoded to DIFFERENT content than intended. Do not use this download; "
                                        "choose a simpler design.", structure_ok, which)
    why = ("Every module of the data pattern is intact, so the limit is probably the decoder's tolerance for this styling."
           if structure_ok else f"{bad} of {total} sampled modules differ from the intended pattern.")
    return Verification("unreadable", "The built-in decoder could not read this design. " + why +
                        " Many phone scanners are more tolerant, but test-scan before sharing or switch to a simpler style.",
                        structure_ok)
