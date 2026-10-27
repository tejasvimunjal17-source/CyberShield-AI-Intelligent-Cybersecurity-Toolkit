"""SVG output for a Scene: real vector paths, gradients and text.

Modules, position markers, frame shapes and gradients stay vector at any zoom. Two parts are
not vector and are documented as such: a logo is embedded as a re-encoded PNG (the user's logo
is a bitmap), and the label is live <text> whose width is pinned with textLength so it matches
the raster and PDF layout even if the viewer substitutes a different sans-serif font.

Every user-controlled string is XML-escaped; colors were validated as #RRGGBB beforehand.
"""

from __future__ import annotations

import base64
from xml.sax.saxutils import escape, quoteattr

from qr_tools import geometry as geo
from qr_tools.render_raster import logo_png_for_vector
from qr_tools.scene import Box, Poly, Scene, pixel_box

GRADIENT_ID = "cs-qr-gradient"
_n = geo._n


def _rect(b: Box) -> str:
    attrs = [f'x="{_n(b.x)}"', f'y="{_n(b.y)}"', f'width="{_n(b.w)}"', f'height="{_n(b.h)}"']
    if b.r:
        attrs += [f'rx="{_n(b.r)}"', f'ry="{_n(b.r)}"']
    attrs.append(f'fill="{b.fill}"' if b.fill else 'fill="none"')
    if b.stroke and b.stroke_w:
        attrs += [f'stroke="{b.stroke}"', f'stroke-width="{_n(b.stroke_w)}"']
    return "<rect " + " ".join(attrs) + "/>"


def _gradient_def(scene: Scene) -> str:
    f = scene.fill
    x, y, w, h = f.rect
    stops = f'<stop offset="0" stop-color="{f.c1}"/><stop offset="1" stop-color="{f.c2}"/>'
    if f.kind == "linear":
        return (f'<linearGradient id="{GRADIENT_ID}" gradientUnits="userSpaceOnUse" x1="{_n(x)}" y1="{_n(y)}" '
                f'x2="{_n(x + w)}" y2="{_n(y)}">{stops}</linearGradient>')
    if f.kind == "diagonal":
        return (f'<linearGradient id="{GRADIENT_ID}" gradientUnits="userSpaceOnUse" x1="{_n(x)}" y1="{_n(y)}" '
                f'x2="{_n(x + w)}" y2="{_n(y + h)}">{stops}</linearGradient>')
    return (f'<radialGradient id="{GRADIENT_ID}" gradientUnits="userSpaceOnUse" cx="{_n(x + w / 2)}" cy="{_n(y + h / 2)}" '
            f'r="{_n(w * 0.70710678)}">{stops}</radialGradient>')


def render_svg(scene: Scene, target_px: int) -> str:
    box = pixel_box(scene, target_px)
    W, H = scene.width, scene.height
    out = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" '
        f'width="{W * box}" height="{H * box}" viewBox="0 0 {W} {H}">',
        "<title>QR code</title>",
    ]
    if scene.fill.kind != "solid":
        out.append("<defs>" + _gradient_def(scene) + "</defs>")
    if scene.background:
        out.append(f'<rect width="{W}" height="{H}" fill="{scene.background}"/>')

    for shape in scene.shapes:
        if isinstance(shape, Box):
            out.append(_rect(shape))
        elif isinstance(shape, Poly):
            pts = " ".join(f"{_n(x)},{_n(y)}" for x, y in shape.points)
            out.append(f'<polygon points="{pts}" fill="{shape.fill}"/>')

    if scene.block_backing:
        bx, by, bw, bh = scene.block
        out.append(f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" fill="{scene.block_backing}"/>')

    if scene.label:
        lb = scene.label
        out.append(
            f'<text x="{_n(lb.cx - lb.width / 2)}" y="{_n(lb.cy + geo.baseline_offset(lb.size))}" '
            f'font-family="Helvetica, Arial, sans-serif" font-size="{_n(lb.size)}" '
            f'font-weight="{"bold" if lb.bold else "normal"}" fill="{lb.color}" textLength="{_n(lb.width)}" '
            f'lengthAdjust="spacingAndGlyphs">{escape(lb.text)}</text>'
        )

    fill_ref = f"url(#{GRADIENT_ID})" if scene.fill.kind != "solid" else scene.fill.c1
    d = "".join(geo.svg_d(geo.module_path(scene.pattern, x, y)) for x, y in scene.modules)
    crisp = ' shape-rendering="crispEdges"' if scene.pattern == "square" else ""
    out.append(f'<path fill="{fill_ref}"{crisp} d="{d}"/>')

    for eye in scene.eyes:
        outer, hole = geo.eye_ring(eye.outer, eye.x, eye.y)
        out.append(f'<path fill="{eye.outer_color}" fill-rule="evenodd" d="{geo.svg_d(outer)}{geo.svg_d(hole)}"/>')
        out.append(f'<path fill="{eye.inner_color}" d="{geo.svg_d(geo.eye_centre(eye.inner, eye.x, eye.y))}"/>')

    if scene.logo:
        data, pw, ph = logo_png_for_vector(scene, box)
        lg = scene.logo
        cx, cy = lg.x + lg.side / 2, lg.y + lg.side / 2
        w, h = pw / box, ph / box
        href = "data:image/png;base64," + base64.b64encode(data).decode("ascii")
        out.append(f'<image x="{_n(cx - w / 2)}" y="{_n(cy - h / 2)}" width="{_n(w)}" height="{_n(h)}" '
                   f'xlink:href={quoteattr(href)}/>')
    out.append("</svg>")
    return "\n".join(out)
