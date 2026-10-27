"""Scene: the single description of a finished QR image.

build_scene(matrix, design) turns a module matrix and a Design into plain data (module
positions, position markers, frame shapes, label text, logo placement) in MODULE UNITS.
The raster, SVG and PDF renderers all consume this same object, so the preview and
every download are guaranteed to be drawn from identical instructions.

All frame/label dimensions are whole modules, so every module lands on a whole pixel
at export time and edges stay crisp for scanners.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from qr_tools import geometry as geo
from qr_tools.design import (Design, TEXT_SIZES, logo_hole_blocks_error, logo_hole_modules)
from qr_tools.generator import QRError

FINDER = ("#######", "#.....#", "#.###.#", "#.###.#", "#.###.#", "#.....#", "#######")


@dataclass(frozen=True)
class Box:
    """Rounded rectangle, optionally filled and/or stroked (units: modules)."""
    x: float
    y: float
    w: float
    h: float
    r: float = 0
    fill: str | None = None
    stroke: str | None = None
    stroke_w: float = 0


@dataclass(frozen=True)
class Poly:
    points: tuple[tuple[float, float], ...]
    fill: str


@dataclass(frozen=True)
class Label:
    cx: float
    cy: float
    text: str
    size: float
    bold: bool
    color: str
    width: float


@dataclass(frozen=True)
class Eye:
    x: float
    y: float
    outer: str
    inner: str
    outer_color: str
    inner_color: str


@dataclass(frozen=True)
class Logo:
    x: float
    y: float
    side: float          # logo drawn inside this square (modules)
    hole: tuple[float, float, float, float]   # cleared, module-aligned area (x, y, w, h); modules are not drawn there
    data: bytes


@dataclass(frozen=True)
class Fill:
    kind: str
    c1: str
    c2: str
    rect: tuple[float, float, float, float]  # gradient extent = the module area


@dataclass
class Scene:
    width: int
    height: int
    background: str | None
    block: tuple[int, int, int, int]            # QR block incl. quiet zone: x, y, w, h
    origin: tuple[int, int]                     # position of module (0, 0)
    n: int
    pattern: str
    modules: list[tuple[int, int]]
    fill: Fill
    eyes: list[Eye]
    shapes: list = field(default_factory=list)  # frame Box/Poly drawn BEFORE the code
    label: Label | None = None
    block_backing: str | None = None
    logo: Logo | None = None


def verify_finders(matrix: list[list[bool]]) -> None:
    """The three position markers must have the standard 7x7 form, or custom marker drawing would corrupt the code."""
    n = len(matrix)
    if n < 21 or any(len(row) != n for row in matrix):
        raise QRError("The QR matrix has an unexpected shape.")
    for ox, oy in ((0, 0), (n - 7, 0), (0, n - 7)):
        for y, row in enumerate(FINDER):
            for x, ch in enumerate(row):
                if bool(matrix[oy + y][ox + x]) != (ch == "#"):
                    raise QRError("The QR matrix does not contain the standard position markers.")


def version_of(n: int) -> int:
    return (n - 17) // 4


def alignment_centers(n: int) -> list[tuple[int, int]]:
    """Centres of the alignment patterns for a QR version, excluding those that sit on a position marker."""
    v = version_of(n)
    if v < 2:
        return []
    count = v // 7 + 2
    step = 26 if v == 32 else ((n - 13) // (count - 1) + 1) // 2 * 2
    coords = [6] + [n - 7 - step * (count - 2 - i) for i in range(count - 1)]
    out = []
    for cy in coords:
        for cx in coords:
            if (cx, cy) in ((6, 6), (coords[-1], 6), (6, coords[-1])):
                continue
            out.append((cx, cy))
    return out


def structures_under(n: int, x: int, y: int, size: int) -> tuple[list[str], list[str]]:
    """What the square (x, y, size) in MATRIX coordinates covers: (fatal structures, softer structures)."""
    def hit(zx, zy, zw, zh):
        return x < zx + zw and zx < x + size and y < zy + zh and zy < y + size
    fatal, soft = [], []
    if hit(0, 0, 9, 9) or hit(n - 8, 0, 8, 9) or hit(0, n - 8, 9, 8):
        fatal.append("a position marker or its format information")
    if hit(8, 6, max(n - 16, 0), 1) or hit(6, 8, 1, max(n - 16, 0)):
        fatal.append("a timing pattern")
    if version_of(n) >= 7 and (hit(n - 11, 0, 3, 6) or hit(0, n - 11, 6, 3)):
        fatal.append("the version information")
    if any(hit(cx - 2, cy - 2, 5, 5) for cx, cy in alignment_centers(n)):
        soft.append("an alignment pattern")
    return fatal, soft


def _frame(design: Design, block: int) -> tuple[int, int, int, int, list, Label | None, str | None]:
    """Layout of frame + label around a block. Returns (W, H, block_x, block_y, shapes, label, block_backing)."""
    d, p, sw = design, design.frame_padding, 1
    if d.frame == "none":
        return block, block, 0, 0, [], None, None

    text = d.cta_text if d.has_label else ""
    frame = d.frame
    if not text and frame in ("badge", "tag", "bubble"):
        frame = "rounded"          # a label-less badge/tag/bubble would be lopsided: show a plain rounded border
    avail = block + 2 * p - 2
    size = float(TEXT_SIZES[d.cta_size])
    if text:
        width = geo.text_width(text, size, d.cta_bold)
        if width > avail:
            size = size * avail / width
            width = geo.text_width(text, size, d.cta_bold)
        if size < 1.2:
            raise QRError("The label text is too long for this code. Shorten it or use a smaller text size.")
    else:
        width = 0.0
    band = (math.ceil(size) + 2) if text else 0
    bg = d.bg if not d.transparent else "#FFFFFF"
    shapes: list = []

    if frame in ("border", "rounded"):
        w = block + 2 * (sw + p)
        h = block + 2 * (sw + p) + ((1 + band) if text else 0)
        r = 0 if frame == "border" else 3
        shapes.append(Box(sw / 2, sw / 2, w - sw, h - sw, r, None, d.frame_color, sw))
        bx = by = sw + p
        label = Label(w / 2, by + block + 1 + band / 2, text, size, d.cta_bold, d.cta_color, width) if text else None
        return w, h, bx, by, shapes, label, None

    if frame == "badge":
        w, h = block + 2 * p, p + block + band
        shapes.append(Box(0, 0, w, h, 2 if band or p > 1 else 0, d.frame_color))
        label = Label(w / 2, p + block + band / 2, text, size, d.cta_bold, d.cta_color, width) if text else None
        return w, h, p, p, shapes, label, bg

    if frame == "tag":
        w, h = block + 2 * p, band + block + p
        shapes.append(Box(0, 0, w, h, 2, d.frame_color))
        label = Label(w / 2, band / 2, text, size, d.cta_bold, d.cta_color, width) if text else None
        return w, h, p, band, shapes, label, bg

    # bubble: a bordered card for the code and a label bubble with a pointer underneath
    w = block + 2 * (sw + p)
    card_h = block + 2 * (sw + p)
    shapes.append(Box(sw / 2, sw / 2, w - sw, card_h - sw, 3, None, d.frame_color, sw))
    label = None
    h = card_h
    if text:
        pill_w = min(w, math.ceil(width) + 4)
        if (w - pill_w) % 2:
            pill_w += 1
        gap, pill_h = 2, band
        pill_y = card_h + gap
        shapes.append(Poly(((w / 2 - 1.5, pill_y), (w / 2 + 1.5, pill_y), (w / 2, card_h)), d.frame_color))
        shapes.append(Box((w - pill_w) / 2, pill_y, pill_w, pill_h, pill_h / 2, d.frame_color))
        label = Label(w / 2, pill_y + pill_h / 2, text, size, d.cta_bold, d.cta_color, width)
        h = pill_y + pill_h + 1
    return w, h, sw + p, sw + p, shapes, label, None


def build_scene(matrix: list[list[bool]], design: Design, logo_data: bytes | None = None) -> Scene:
    """Compose the finished image description. `design` should already be validated."""
    d = design
    verify_finders(matrix)
    n = len(matrix)
    q = d.quiet_zone
    block = n + 2 * q
    W, H, bx, by, shapes, label, backing = _frame(d, block)
    ox, oy = bx + q, by + q

    hole_rect = None
    logo = None
    if d.has_logo:
        logo_hole_blocks_error(n, d)
        hole = logo_hole_modules(n, d)
        fatal, _soft = structures_under(n, (n - hole) // 2, (n - hole) // 2, hole)
        if fatal:
            raise QRError("The logo area would cover " + " and ".join(fatal) + ". Make the logo smaller or reduce its clear space.")
        hx, hy = ox + (n - hole) // 2, oy + (n - hole) // 2
        hole_rect = (hx, hy, hole, hole)
        side = max(1.0, min(n * d.logo_fraction, hole - 2 * d.logo_margin))
        logo = Logo(hx + (hole - side) / 2, hy + (hole - side) / 2, side, hole_rect,
                    logo_data if logo_data is not None else d.logo_bytes)

    finder_cells = set()
    for ex, ey in ((0, 0), (n - 7, 0), (0, n - 7)):
        finder_cells.update((ex + i, ey + j) for i in range(7) for j in range(7))

    modules: list[tuple[int, int]] = []
    for y, row in enumerate(matrix):
        for x, dark in enumerate(row):
            if not dark or (x, y) in finder_cells:
                continue
            if hole_rect and hole_rect[0] <= ox + x < hole_rect[0] + hole_rect[2] and hole_rect[1] <= oy + y < hole_rect[1] + hole_rect[3]:
                continue
            modules.append((ox + x, oy + y))

    outer_c, inner_c = d.eye_colors()
    eyes = [Eye(ox + ex, oy + ey, d.eye_outer, d.eye_inner, outer_c, inner_c) for ex, ey in ((0, 0), (n - 7, 0), (0, n - 7))]
    fill = Fill(d.fill, d.fg, d.fg2 if d.fill != "solid" else d.fg, (ox, oy, n, n))
    return Scene(W, H, None if d.transparent else d.bg, (bx, by, block, block), (ox, oy), n, d.pattern,
                 modules, fill, eyes, shapes, label, backing, logo)


def pixel_box(scene: Scene, target_px: int) -> int:
    """Whole pixels per module for a requested output size (never zero)."""
    return max(1, target_px // max(scene.width, scene.height))
