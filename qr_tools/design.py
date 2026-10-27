"""QR design settings: one immutable object that drives preview AND every export.

`Design` holds only plain values (colors, shapes, sizes, optional logo bytes) so it can
be hashed, compared and memoised. `validate()` raises QRError for anything unsafe or
unsupported; `warnings()` returns non-fatal scannability advice. Nothing here renders.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, replace

from PIL import Image

from qr_tools import geometry as geo
from qr_tools.generator import ERROR_LEVELS, MAX_LOGO_PIXELS, QRError, _luminance, _rgb, contrast_ratio  # noqa: PLC2701 - same luminance maths as the existing checker

SIZES = (512, 768, 1024, 2048, 4096)
FILLS = ("solid", "linear", "diagonal", "radial")
FILL_LABELS = {"solid": "Solid color", "linear": "Linear gradient (left to right)",
               "diagonal": "Diagonal gradient", "radial": "Radial gradient (centre outwards)"}
FRAMES = ("none", "border", "rounded", "badge", "tag", "bubble")
FRAME_LABELS = {"none": "No frame", "border": "Simple border", "rounded": "Rounded rectangle",
                "badge": "Badge (label under the code)", "tag": "Tag (label above the code)",
                "bubble": "Speech bubble"}
TEXT_SIZES = {"small": 2, "medium": 3, "large": 4}
EC_CAPACITY = {"L": 0.07, "M": 0.15, "Q": 0.25, "H": 0.30}
EC_LABELS = {"L": "L: about 7% recoverable", "M": "M: about 15% recoverable",
             "Q": "Q: about 25% recoverable", "H": "H: about 30% recoverable"}
MIN_LOGO_FRACTION, MAX_LOGO_FRACTION = 0.05, 0.22
MAX_LOGO_BYTES = 1024 * 1024
MAX_LOGO_SIDE = 2000

_HEX = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def normalize_hex(value: str, what: str = "Color") -> str:
    """'#abc' or '#aabbcc' -> '#AABBCC'. Anything else is rejected (no names, no rgb())."""
    text = (value or "").strip()
    if not _HEX.match(text):
        raise QRError(f"{what} must be a hex value like #0B1628.")
    if len(text) == 4:
        text = "#" + "".join(c * 2 for c in text[1:])
    return text.upper()


@dataclass(frozen=True)
class Design:
    # data pattern and position markers
    pattern: str = "square"
    eye_outer: str = "square"
    eye_inner: str = "square"
    eye_outer_color: str | None = None     # None = same as foreground
    eye_inner_color: str | None = None
    # colors
    fg: str = "#000000"
    fg2: str = "#0B1628"                   # second gradient color
    fill: str = "solid"
    bg: str = "#FFFFFF"
    transparent: bool = False
    # technical
    error_correction: str = "M"
    quiet_zone: int = 4
    target_px: int = 1024
    # logo
    logo_bytes: bytes | None = None
    logo_fraction: float = 0.12
    logo_margin: int = 1
    # frame and call to action
    frame: str = "none"
    cta_text: str = ""
    cta_color: str = "#FFFFFF"
    cta_size: str = "medium"
    cta_bold: bool = True
    frame_color: str = "#0B1628"
    frame_padding: int = 2

    def validate(self) -> "Design":
        """Return a normalised copy (hex upper-cased, CTA trimmed) or raise QRError."""
        checks = ((self.pattern, geo.PATTERNS, "pattern"), (self.eye_outer, geo.EYE_OUTER, "outer marker shape"),
                  (self.eye_inner, geo.EYE_INNER, "inner marker shape"), (self.fill, FILLS, "fill"),
                  (self.frame, FRAMES, "frame"), (self.cta_size, tuple(TEXT_SIZES), "text size"),
                  (self.error_correction, ERROR_LEVELS, "error correction level"))
        for value, allowed, name in checks:
            if value not in allowed:
                raise QRError(f"Unsupported {name}.")
        if self.target_px not in SIZES:
            raise QRError("Choose one of the listed output sizes.")
        if not isinstance(self.quiet_zone, int) or not 1 <= self.quiet_zone <= 10:
            raise QRError("The quiet zone must be between 1 and 10 modules.")
        if not isinstance(self.frame_padding, int) or not 1 <= self.frame_padding <= 6:
            raise QRError("Frame padding must be between 1 and 6 modules.")
        if not MIN_LOGO_FRACTION <= self.logo_fraction <= MAX_LOGO_FRACTION:
            raise QRError(f"Logo size must be between {MIN_LOGO_FRACTION:.0%} and {MAX_LOGO_FRACTION:.0%} of the code width.")
        if not isinstance(self.logo_margin, int) or not 0 <= self.logo_margin <= 3:
            raise QRError("Logo clear space must be between 0 and 3 modules.")
        text = (self.cta_text or "").strip()
        if len(text) > geo.CTA_MAX_CHARS:
            raise QRError(f"Label text can be at most {geo.CTA_MAX_CHARS} characters.")
        if not geo.cta_text_ok(text):
            raise QRError("Label text supports letters, digits and basic punctuation (no accents or emoji).")
        if self.logo_bytes is not None:
            check_logo(self.logo_bytes)
        return replace(
            self, fg=normalize_hex(self.fg, "Foreground"), fg2=normalize_hex(self.fg2, "Second gradient color"),
            bg=normalize_hex(self.bg, "Background"), cta_color=normalize_hex(self.cta_color, "Label color"),
            frame_color=normalize_hex(self.frame_color, "Frame color"), cta_text=text,
            eye_outer_color=normalize_hex(self.eye_outer_color, "Outer marker color") if self.eye_outer_color else None,
            eye_inner_color=normalize_hex(self.eye_inner_color, "Inner marker color") if self.eye_inner_color else None,
        )

    # --- derived values ---
    def module_colors(self) -> list[str]:
        return [self.fg] + ([self.fg2] if self.fill != "solid" else [])

    def eye_colors(self) -> tuple[str, str]:
        return self.eye_outer_color or self.fg, self.eye_inner_color or self.fg

    @property
    def has_logo(self) -> bool:
        return self.logo_bytes is not None

    @property
    def has_label(self) -> bool:
        return self.frame != "none" and bool(self.cta_text)


def check_logo(data: bytes) -> tuple[str, tuple[int, int]]:
    """Validate a logo by its CONTENT (not its name). Returns (format, size). Never executes anything."""
    if len(data) > MAX_LOGO_BYTES:
        raise QRError("The logo file is larger than 1 MB.")
    try:
        with Image.open(io.BytesIO(data)) as img:
            fmt, size = img.format, img.size
            img.verify()  # detects truncated / corrupt files without rendering them
    except Exception as exc:
        raise QRError("The logo file could not be read as an image.") from exc
    if fmt not in ("PNG", "JPEG"):
        raise QRError("The logo must be a PNG or JPG image (checked from the file content, not the name).")
    if size[0] * size[1] > MAX_LOGO_PIXELS or max(size) > MAX_LOGO_SIDE:
        raise QRError(f"The logo is too large. Use an image up to {MAX_LOGO_SIDE} x {MAX_LOGO_SIDE} pixels.")
    if min(size) < 16:
        raise QRError("The logo is too small. Use an image at least 16 x 16 pixels.")
    return fmt, size


# --------------------------------------------------------------------------
# Presets
# --------------------------------------------------------------------------
COLOR_PRESETS: dict[str, dict | None] = {
    "Classic black and white": dict(fg="#000000", fill="solid", bg="#FFFFFF", eye_outer_color=None, eye_inner_color=None),
    "Cybersecurity blue": dict(fg="#0B3C8C", fill="solid", bg="#FFFFFF", eye_outer_color="#0B1628", eye_inner_color="#0B3C8C"),
    "Cyan and navy": dict(fg="#0B1628", fill="solid", bg="#D6F6FB", eye_outer_color="#0E7490", eye_inner_color="#0B1628"),
    "Teal and dark blue": dict(fg="#0F766E", fg2="#0B1F4D", fill="diagonal", bg="#FFFFFF",
                               eye_outer_color="#0B1F4D", eye_inner_color="#0F766E"),
    "Purple and blue": dict(fg="#6D28D9", fg2="#1D4ED8", fill="diagonal", bg="#FFFFFF",
                            eye_outer_color="#4C1D95", eye_inner_color="#1E3A8A"),
    "Navy on white": dict(fg="#0B1628", fill="solid", bg="#FFFFFF", eye_outer_color=None, eye_inner_color=None),
    "Teal on white": dict(fg="#0F766E", fill="solid", bg="#FFFFFF", eye_outer_color=None, eye_inner_color=None),
    "Custom brand colors": None,
}
STYLE_PRESETS: dict[str, dict | None] = {
    "Classic": dict(pattern="square", eye_outer="square", eye_inner="square"),
    "Rounded": dict(pattern="rounded", eye_outer="rounded", eye_inner="rounded"),
    "Circular": dict(pattern="dots", eye_outer="rounded", eye_inner="circle"),
    "Modern geometric": dict(pattern="diamond", eye_outer="square", eye_inner="rounded"),
    "Custom": None,
}
STYLE_PRESET_NOTES = {
    "Classic": "Square modules and square markers. The most reliable choice.",
    "Rounded": "Rounded modules with slightly rounded markers.",
    "Circular": "Round dots with circular marker centres. The outer marker keeps near-square corners because "
                "a fully round ring was not readable in testing.",
    "Modern geometric": "Diamond modules, square outer markers and rounded centres.",
}


# --------------------------------------------------------------------------
# Warnings (advice, never a guarantee)
# --------------------------------------------------------------------------
def auto_label_color(frame: str, frame_color: str, bg: str, transparent: bool = False) -> str:
    """White or navy, whichever reads better where the label text will sit."""
    sits_on = frame_color if frame in ("badge", "tag", "bubble") else ("#FFFFFF" if transparent else bg)
    return max(("#FFFFFF", "#0B1628"), key=lambda c: contrast_ratio(c, sits_on))


def logo_hole_modules(n: int, design: Design) -> int:
    """Side of the centred, module-aligned area cleared for the logo (same parity as n so it is centred)."""
    side = n * design.logo_fraction
    hole = int(-(-(side + 2 * design.logo_margin) // 1))
    if (n - hole) % 2:
        hole += 1
    return max(1, hole)


def logo_coverage(n: int, design: Design) -> float:
    hole = logo_hole_modules(n, design)
    return (hole * hole) / float(n * n)


def scan_warnings(design: Design, n: int | None = None) -> list[str]:
    """Plain-language advice about scannability. An empty list does NOT mean the code will scan."""
    d = design
    out: list[str] = []
    surface = "#FFFFFF"
    bg = d.bg if not d.transparent else surface
    colors = d.module_colors() + [c for c in d.eye_colors()]
    worst = min(contrast_ratio(c, bg) for c in colors)
    if worst < 3:
        out.append("Low contrast between the code and the background. Many scanners will fail to read it.")
    elif worst < 4.5:
        out.append("Contrast is modest. Prefer a darker foreground or a lighter background for reliable scanning.")
    if _luminance(_rgb(d.fg)) > _luminance(_rgb(bg)):
        out.append("Light-on-dark (inverted) codes are not read by every scanner. Test before sharing.")
    if d.transparent:
        out.append("With a transparent background, readability depends on the surface behind the code. "
                   "Place it on a plain, light surface.")
    if d.quiet_zone < 4:
        out.append("The recommended quiet zone is at least 4 modules of blank space. A smaller one can stop scanners "
                   "from finding the code.")
    if d.eye_outer == "circle":
        out.append("A circular outer marker is decorative and unverified: the built-in decoder cannot read it, and some "
                   "phone scanners may not either. Choose 'Slightly rounded' or 'Square' for dependable scanning.")
    if d.pattern != "square" or d.eye_outer != "square" or d.eye_inner != "square" or d.fill != "solid":
        out.append("Decorative shapes and gradients can reduce scan reliability. Test-scan the downloaded file on the "
                   "phones you care about.")
    if d.has_logo:
        if d.error_correction in ("L", "M"):
            out.append("A logo hides part of the code. Error correction Q or H is recommended with a logo.")
        if d.logo_fraction > 0.18:
            out.append("A large logo can make the code unreadable. Keep it under about 15% of the width.")
        if n:
            from qr_tools.scene import structures_under   # local import: scene imports this module
            hole = logo_hole_modules(n, d)
            _fatal, soft = structures_under(n, (n - hole) // 2, (n - hole) // 2, hole)
            if soft:
                out.append("The logo covers " + " and ".join(soft) + ". Error correction usually compensates, but check "
                           "that the code still scans.")
            cov = logo_coverage(n, d)
            if cov > EC_CAPACITY[d.error_correction] / 2:
                out.append(f"The logo clears about {cov:.0%} of the modules. Level {d.error_correction} recovers at most about "
                           f"{EC_CAPACITY[d.error_correction]:.0%}, and only under ideal conditions. Shrink the logo or raise the level.")
    if d.has_label:
        band = d.frame_color if d.frame in ("badge", "tag", "bubble") else (d.bg if not d.transparent else surface)
        if contrast_ratio(d.cta_color, band) < 3:
            out.append("The label text has low contrast against its background.")
    if d.frame in ("badge", "tag", "bubble") and d.transparent:
        out.append("Transparency applies outside the frame only. The code itself keeps its background color so the "
                   "quiet zone stays clear.")
    return out


def logo_hole_blocks_error(n: int, design: Design) -> None:
    """Refuse a logo that clears more of the code than the chosen level could ever recover."""
    if design.has_logo and logo_coverage(n, design) > EC_CAPACITY[design.error_correction]:
        raise QRError(
            f"The logo clears about {logo_coverage(n, design):.0%} of this code, more than level "
            f"{design.error_correction} can recover. Make the logo smaller, reduce its clear space, or use a higher level."
        )
