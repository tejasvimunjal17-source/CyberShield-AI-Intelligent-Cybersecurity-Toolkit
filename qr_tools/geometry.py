"""Shared geometry for the QR renderers: shape paths and text metrics.

Every shape is defined ONCE here as a list of path operations in module units:
    ("M", x, y)  ("L", x, y)  ("C", x1, y1, x2, y2, x, y)  ("Z",)
The raster renderer flattens these into polygons; the SVG and PDF renderers write
them out as real vector path commands. Using one definition is what keeps the
preview, PNG, SVG and PDF looking the same.
"""

from __future__ import annotations

from typing import Callable, Iterable

Path = list[tuple]
KAPPA = 0.5522847498  # bezier handle length for a quarter circle


def rect_path(x: float, y: float, w: float, h: float) -> Path:
    return [("M", x, y), ("L", x + w, y), ("L", x + w, y + h), ("L", x, y + h), ("Z",)]


def rrect_path(x: float, y: float, w: float, h: float, r: float) -> Path:
    r = max(0.0, min(r, w / 2, h / 2))
    if r == 0:
        return rect_path(x, y, w, h)
    k = r * KAPPA
    return [
        ("M", x + r, y), ("L", x + w - r, y), ("C", x + w - r + k, y, x + w, y + r - k, x + w, y + r),
        ("L", x + w, y + h - r), ("C", x + w, y + h - r + k, x + w - r + k, y + h, x + w - r, y + h),
        ("L", x + r, y + h), ("C", x + r - k, y + h, x, y + h - r + k, x, y + h - r),
        ("L", x, y + r), ("C", x, y + r - k, x + r - k, y, x + r, y), ("Z",),
    ]


def circle_path(cx: float, cy: float, r: float) -> Path:
    k = r * KAPPA
    return [
        ("M", cx + r, cy), ("C", cx + r, cy + k, cx + k, cy + r, cx, cy + r),
        ("C", cx - k, cy + r, cx - r, cy + k, cx - r, cy), ("C", cx - r, cy - k, cx - k, cy - r, cx, cy - r),
        ("C", cx + k, cy - r, cx + r, cy - k, cx + r, cy), ("Z",),
    ]


def poly_path(points: Iterable[tuple[float, float]]) -> Path:
    pts = list(points)
    return [("M", *pts[0]), *[("L", *p) for p in pts[1:]], ("Z",)]


# ---- data-module shapes (unit cell at x, y) --------------------------------
ROUND_RADIUS = 0.3     # corner radius of a "rounded" module (cell = 1)
DOT_RADIUS = 0.46      # radius of a "dots" module
EYE_ROUND_RADIUS = 0.6 # corner radius of a "rounded" outer marker. Measured: 48/48 decode up to 0.7, first failure at 0.8,
                       # and 2/12 at the old 2.0 (see tests/test_qr_reliability.py). 0.6 keeps a margin below the first failure.
PATTERNS = ("square", "rounded", "dots", "diamond")
PATTERN_LABELS = {"square": "Square", "rounded": "Rounded squares", "dots": "Circular dots", "diamond": "Diamonds"}


def module_path(pattern: str, x: float, y: float) -> Path:
    if pattern == "square":
        return rect_path(x, y, 1, 1)
    if pattern == "rounded":
        return rrect_path(x, y, 1, 1, ROUND_RADIUS)
    if pattern == "dots":
        return circle_path(x + 0.5, y + 0.5, DOT_RADIUS)
    if pattern == "diamond":
        return poly_path([(x + 0.5, y + 0.03), (x + 0.97, y + 0.5), (x + 0.5, y + 0.97), (x + 0.03, y + 0.5)])
    raise ValueError(f"unknown pattern {pattern!r}")


# ---- position markers ("eyes"): a 7x7 ring around a 3x3 centre --------------
EYE_OUTER = ("square", "rounded", "circle")
EYE_OUTER_LABELS = {"square": "Square (most reliable)", "rounded": "Slightly rounded",
                    "circle": "Circular ring (decorative, unverified)"}
EYE_INNER_LABELS = {"square": "Square", "rounded": "Rounded", "circle": "Circle"}
EYE_INNER = ("square", "rounded", "circle")


def eye_ring(kind: str, x: float, y: float) -> tuple[Path, Path]:
    """(outer shape, hole) of the 7x7 ring; the ring is one module thick so the 1:1:3:1:1 ratio is kept."""
    if kind == "square":
        return rect_path(x, y, 7, 7), rect_path(x + 1, y + 1, 5, 5)
    if kind == "rounded":
        return rrect_path(x, y, 7, 7, EYE_ROUND_RADIUS), rrect_path(x + 1, y + 1, 5, 5, max(EYE_ROUND_RADIUS - 1, 0))
    if kind == "circle":
        return circle_path(x + 3.5, y + 3.5, 3.5), circle_path(x + 3.5, y + 3.5, 2.5)
    raise ValueError(f"unknown eye outer shape {kind!r}")


def eye_centre(kind: str, x: float, y: float) -> Path:
    if kind == "square":
        return rect_path(x + 2, y + 2, 3, 3)
    if kind == "rounded":
        return rrect_path(x + 2, y + 2, 3, 3, 0.9)
    if kind == "circle":
        return circle_path(x + 3.5, y + 3.5, 1.5)
    raise ValueError(f"unknown eye inner shape {kind!r}")


# ---- path utilities ----------------------------------------------------------
def transform_path(path: Path, fx: Callable[[float], float], fy: Callable[[float], float]) -> Path:
    out: Path = []
    for op in path:
        if op[0] == "Z":
            out.append(op)
        else:
            vals = list(op[1:])
            out.append((op[0], *[(fx if i % 2 == 0 else fy)(v) for i, v in enumerate(vals)]))
    return out


def flatten(path: Path, steps: int = 14) -> list[list[tuple[float, float]]]:
    """Polylines for each subpath (beziers sampled), used by the raster renderer."""
    polys: list[list[tuple[float, float]]] = []
    cur: list[tuple[float, float]] = []
    for op in path:
        if op[0] == "M":
            if cur:
                polys.append(cur)
            cur = [(op[1], op[2])]
        elif op[0] == "L":
            cur.append((op[1], op[2]))
        elif op[0] == "C":
            x0, y0 = cur[-1]
            _, x1, y1, x2, y2, x3, y3 = op
            for i in range(1, steps + 1):
                t = i / steps
                u = 1 - t
                cur.append((u**3 * x0 + 3 * u * u * t * x1 + 3 * u * t * t * x2 + t**3 * x3,
                            u**3 * y0 + 3 * u * u * t * y1 + 3 * u * t * t * y2 + t**3 * y3))
        elif op[0] == "Z" and cur:
            polys.append(cur)
            cur = []
    if cur:
        polys.append(cur)
    return polys


def _n(v: float) -> str:
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def svg_d(path: Path) -> str:
    parts = []
    for op in path:
        parts.append("Z" if op[0] == "Z" else op[0] + " ".join(_n(v) for v in op[1:]))
    return "".join(parts)


def pdf_ops(path: Path, fx: Callable[[float], float], fy: Callable[[float], float]) -> str:
    """PDF path operators (m, l, c, h) with coordinates mapped by fx / fy."""
    out = []
    for op in path:
        if op[0] == "Z":
            out.append("h")
            continue
        vals = [(fx if i % 2 == 0 else fy)(v) for i, v in enumerate(op[1:])]
        out.append(" ".join(_n(v) for v in vals) + " " + {"M": "m", "L": "l", "C": "c"}[op[0]])
    return "\n".join(out)


# ---- text: Helvetica metrics (units per 1000 em) -----------------------------
# Printable ASCII only. The same widths lay out the raster, SVG and PDF text so it is centred identically.
_REG = ("278 278 355 556 556 889 667 191 333 333 389 584 278 333 278 278 "
        "556 556 556 556 556 556 556 556 556 556 278 278 584 584 584 556 "
        "1015 667 667 722 722 667 611 778 722 278 500 667 556 833 722 778 "
        "667 778 722 667 611 722 667 944 667 667 611 278 278 278 469 556 "
        "333 556 556 500 556 556 278 556 556 222 222 500 222 833 556 556 "
        "556 556 333 500 278 556 500 722 500 500 500 334 260 334 584").split()
_BOLD = ("278 333 474 556 556 889 722 238 333 333 389 584 278 333 278 278 "
         "556 556 556 556 556 556 556 556 556 556 333 333 584 584 584 611 "
         "975 722 722 722 722 667 611 778 722 278 556 722 611 833 722 778 "
         "667 778 722 667 611 722 667 944 667 667 611 333 278 333 584 556 "
         "333 556 611 556 611 556 333 611 611 278 278 556 278 889 611 611 "
         "611 611 389 556 333 611 556 778 556 556 500 389 280 389 584").split()
WIDTHS = {False: [int(v) for v in _REG], True: [int(v) for v in _BOLD]}
CTA_MAX_CHARS = 30


def cta_text_ok(text: str) -> bool:
    return all(32 <= ord(c) <= 126 for c in text)


def text_width(text: str, size: float, bold: bool) -> float:
    """Width of `text` set in Helvetica / Helvetica-Bold at `size` (same unit as size)."""
    table = WIDTHS[bool(bold)]
    return sum(table[ord(c) - 32] for c in text) / 1000.0 * size


def baseline_offset(size: float) -> float:
    """Distance from the vertical centre of capital letters down to the baseline."""
    return 0.36 * size

