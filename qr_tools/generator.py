"""QR code generation: payload builders, rendering, and export.

Design notes
- The `qrcode` package is only used to compute the module matrix
  (make_matrix). Rendering to PNG/JPG/SVG is done here from that matrix, so
  the on-screen preview and every download come from the SAME matrix and the
  SAME QRStyle. There is no separate "download version".
- Supported exports: PNG, JPG, SVG. Logos are PNG/JPG only (SVG export with
  a logo is refused rather than silently dropping the logo).
- A QR code stores text, normally a URL. It cannot contain an arbitrary
  PDF/DOCX; link to a file that is already hosted somewhere public.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass
from urllib.parse import quote, urlsplit

from PIL import Image

from backend.security_utils import MAX_QR_TEXT_CHARS

ERROR_LEVELS = ("L", "M", "Q", "H")
MAX_OUTPUT_PX = 4000
MAX_LOGO_PIXELS = 4_000_000
LOGO_MAX_FRACTION = 0.22  # of the QR width; safe with level-H correction

_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


class QRError(ValueError):
    """User-facing QR problem (bad input or unsupported option)."""


# --------------------------------------------------------------------------
# Payload builders
# --------------------------------------------------------------------------
def build_text_payload(text: str) -> str:
    value = (text or "").strip()
    if not value:
        raise QRError("Enter some text first.")
    if len(value) > MAX_QR_TEXT_CHARS:
        raise QRError(f"Content is longer than {MAX_QR_TEXT_CHARS} characters.")
    return value


def build_url_payload(url: str) -> str:
    value = build_text_payload(url)
    parts = urlsplit(value)
    if parts.scheme.lower() not in ("http", "https") or not parts.netloc:
        raise QRError("Enter a full URL starting with http:// or https://")
    return value


def _wifi_escape(value: str) -> str:
    return re.sub(r'([\\;,:"])', r"\\\1", value)


def build_wifi_payload(ssid: str, password: str = "", security: str = "WPA", hidden: bool = False) -> str:
    ssid = (ssid or "").strip()
    if not ssid:
        raise QRError("Enter the Wi-Fi network name (SSID).")
    if security not in ("WPA", "WEP", "nopass"):
        raise QRError("Security must be WPA, WEP or nopass.")
    if security != "nopass" and not password:
        raise QRError("Enter the Wi-Fi password or choose 'No password'.")
    payload = f"WIFI:T:{security};S:{_wifi_escape(ssid)};"
    if security != "nopass":
        payload += f"P:{_wifi_escape(password)};"
    if hidden:
        payload += "H:true;"
    return payload + ";"


def build_email_payload(address: str, subject: str = "", body: str = "") -> str:
    address = (address or "").strip()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", address):
        raise QRError("Enter a valid email address.")
    payload = f"mailto:{address}"
    params = []
    if subject.strip():
        params.append("subject=" + quote(subject.strip()))
    if body.strip():
        params.append("body=" + quote(body.strip()))
    if params:
        payload += "?" + "&".join(params)
    return build_text_payload(payload)


# --------------------------------------------------------------------------
# Styling
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class QRStyle:
    foreground: str = "#000000"
    background: str = "#FFFFFF"
    target_px: int = 768
    border_modules: int = 4
    error_correction: str = "M"
    logo_bytes: bytes | None = None


def _rgb(color: str) -> tuple[int, int, int]:
    if not _HEX_COLOR.match(color or ""):
        raise QRError("Colors must be hex values like #0B1628.")
    return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)


def _luminance(rgb: tuple[int, int, int]) -> float:
    def channel(c: int) -> float:
        s = c / 255
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(color_a: str, color_b: str) -> float:
    la, lb = _luminance(_rgb(color_a)), _luminance(_rgb(color_b))
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def style_warnings(style: QRStyle) -> list[str]:
    """Non-fatal advice about scannability."""
    warnings = []
    if contrast_ratio(style.foreground, style.background) < 3:
        warnings.append("Low contrast between the two colors. Many scanners will fail to read this code.")
    if _luminance(_rgb(style.foreground)) > _luminance(_rgb(style.background)):
        warnings.append("Light-on-dark (inverted) codes are not read by every scanner. Test before sharing.")
    if style.border_modules < 4:
        warnings.append("The recommended quiet zone is at least 4 modules.")
    if style.logo_bytes and style.error_correction != "H":
        warnings.append("A logo forces error correction to H so the code stays readable.")
    return warnings


# --------------------------------------------------------------------------
# Matrix + rendering
# --------------------------------------------------------------------------
def make_matrix(data: str, error_correction: str = "M") -> list[list[bool]]:
    """Return the QR module matrix (True = dark), without quiet zone."""
    if error_correction not in ERROR_LEVELS:
        raise QRError("Error correction must be L, M, Q or H.")
    data = build_text_payload(data)
    try:
        import qrcode
        from qrcode import constants
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise QRError("The 'qrcode' package is not installed. Run: pip install -r requirements.txt") from exc

    level = {"L": constants.ERROR_CORRECT_L, "M": constants.ERROR_CORRECT_M,
             "Q": constants.ERROR_CORRECT_Q, "H": constants.ERROR_CORRECT_H}[error_correction]
    try:
        qr = qrcode.QRCode(error_correction=level, box_size=1, border=0)
        qr.add_data(data)
        qr.make(fit=True)
    except Exception as exc:  # DataOverflowError and similar
        raise QRError("That content is too large for a QR code at this error-correction level.") from exc
    return [[bool(cell) for cell in row] for row in qr.get_matrix()]


def effective_error_correction(style: QRStyle) -> str:
    return "H" if style.logo_bytes else style.error_correction


def _load_logo(logo_bytes: bytes) -> Image.Image:
    try:
        probe = Image.open(io.BytesIO(logo_bytes))
        if probe.format not in ("PNG", "JPEG"):
            raise QRError("Logo must be a PNG or JPG image.")
        if probe.size[0] * probe.size[1] > MAX_LOGO_PIXELS:
            raise QRError("Logo image is too large. Use one under about 2000 x 2000 pixels.")
        return Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
    except QRError:
        raise
    except Exception as exc:
        raise QRError("The logo file could not be read as an image.") from exc


def render_image(matrix: list[list[bool]], style: QRStyle) -> Image.Image:
    fg, bg = _rgb(style.foreground), _rgb(style.background)
    n = len(matrix)
    border = max(0, min(style.border_modules, 16))
    total_modules = n + 2 * border
    target = max(64, min(style.target_px, MAX_OUTPUT_PX))
    box = max(1, target // total_modules)

    small = Image.new("RGB", (total_modules, total_modules), bg)
    pixels = small.load()
    for y, row in enumerate(matrix):
        for x, dark in enumerate(row):
            if dark:
                pixels[x + border, y + border] = fg
    img = small.resize((total_modules * box, total_modules * box), Image.NEAREST)

    if style.logo_bytes:
        logo = _load_logo(style.logo_bytes)
        qr_width = n * box
        side = max(8, int(qr_width * LOGO_MAX_FRACTION))
        logo.thumbnail((side, side), Image.LANCZOS)
        pad = max(2, box)
        plate = Image.new("RGB", (logo.width + 2 * pad, logo.height + 2 * pad), bg)
        plate.paste(logo, (pad, pad), logo)
        img.paste(plate, ((img.width - plate.width) // 2, (img.height - plate.height) // 2))
    return img


def to_png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def to_jpg_bytes(img: Image.Image, quality: int = 95) -> bytes:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=quality, subsampling=0)
    return buf.getvalue()


def to_svg_bytes(matrix: list[list[bool]], style: QRStyle) -> bytes:
    if style.logo_bytes:
        raise QRError("SVG export does not support logos. Use PNG or JPG, or remove the logo.")
    _rgb(style.foreground), _rgb(style.background)
    n = len(matrix)
    border = max(0, min(style.border_modules, 16))
    size = n + 2 * border
    cells = []
    for y, row in enumerate(matrix):
        for x, dark in enumerate(row):
            if dark:
                cells.append(f"M{x + border},{y + border}h1v1h-1z")
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" '
        f'width="{size * 10}" height="{size * 10}" shape-rendering="crispEdges">'
        f'<rect width="{size}" height="{size}" fill="{style.background}"/>'
        f'<path d="{"".join(cells)}" fill="{style.foreground}"/></svg>'
    )
    return svg.encode("utf-8")
