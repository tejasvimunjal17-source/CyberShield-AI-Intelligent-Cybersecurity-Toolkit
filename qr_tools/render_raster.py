"""Raster rendering of a Scene (used for the preview, PNG, JPG and TIFF).

Pixels per module is a whole number so module edges stay crisp. Curved shapes are drawn on
supersampled masks and averaged down; the large module grid and gradients use NumPy.
Memory is bounded: the biggest allocations are a few canvases of at most 4096 x 4096.
"""

from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from qr_tools import geometry as geo
from qr_tools.scene import Box, Label, Poly, Scene, pixel_box

_FONTS = {
    False: ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/dejavu/DejaVuSans.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"),
    True: ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
           "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"),
}


def _rgb(color: str) -> tuple[int, int, int]:
    return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)


def _font(bold: bool, px: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in _FONTS[bold]:
        try:
            return ImageFont.truetype(name, px)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=px)        # Pillow >= 10.1: scalable built-in font
    except TypeError:                                  # pragma: no cover - very old Pillow
        return ImageFont.load_default()


def _supersample(px_w: int, px_h: int) -> int:
    return max(1, min(4, 4096 // max(px_w, px_h, 1)))


def _mask(paths: list[tuple[list, int]], w: int, h: int, f: int) -> Image.Image:
    """Anti-aliased L mask. `paths` are (path in pixel units, value) drawn in order (value 0 punches holes)."""
    big = Image.new("L", (w * f, h * f), 0)
    draw = ImageDraw.Draw(big)
    for path, value in paths:
        scaled = geo.transform_path(path, lambda v: v * f, lambda v: v * f)
        for poly in geo.flatten(scaled):
            if len(poly) >= 3:
                draw.polygon(poly, fill=value)
    return big if f == 1 else big.resize((w, h), Image.BOX)


def _paint(canvas: Image.Image, mask: Image.Image, color: tuple[int, int, int], dest: tuple[int, int] = (0, 0)) -> None:
    layer = Image.new("RGBA", mask.size, color + (0,))
    layer.putalpha(mask)
    canvas.alpha_composite(layer, dest=dest)


def _scale(path: list, box: int) -> list:
    return geo.transform_path(path, lambda v: v * box, lambda v: v * box)


def _box_paths(b: Box, box: int) -> tuple[list, list]:
    """(fill paths, stroke paths) in pixel units for a Box."""
    fill, stroke = [], []
    if b.fill:
        fill.append((_scale(geo.rrect_path(b.x, b.y, b.w, b.h, b.r), box), 255))
    if b.stroke and b.stroke_w:
        hw = b.stroke_w / 2
        stroke.append((_scale(geo.rrect_path(b.x - hw, b.y - hw, b.w + b.stroke_w, b.h + b.stroke_w, b.r + hw if b.r else 0), box), 255))
        stroke.append((_scale(geo.rrect_path(b.x + hw, b.y + hw, b.w - b.stroke_w, b.h - b.stroke_w, max(b.r - hw, 0)), box), 0))
    return fill, stroke


def _gradient(scene: Scene, size: int) -> Image.Image:
    f = scene.fill
    c1, c2 = np.array(_rgb(f.c1), np.float32), np.array(_rgb(f.c2), np.float32)
    idx = (np.arange(size, dtype=np.float32) + 0.5) / size
    if f.kind == "linear":
        t = np.broadcast_to(idx[None, :], (size, size))
    elif f.kind == "diagonal":
        t = (idx[None, :] + idx[:, None]) / 2
    else:  # radial: centre colour c1, corners of the module area reach c2
        t = np.sqrt((idx[None, :] - 0.5) ** 2 + (idx[:, None] - 0.5) ** 2) / 0.70710678
    t = np.clip(t, 0, 1)
    out = np.empty((size, size, 3), np.uint8)
    for ch in range(3):
        out[..., ch] = (c1[ch] + (c2[ch] - c1[ch]) * t + 0.5).astype(np.uint8)
    return Image.fromarray(out, "RGB")


def render_raster(scene: Scene, target_px: int) -> Image.Image:
    """Return an RGBA image of the scene, width/height = whole modules * pixels per module."""
    box = pixel_box(scene, target_px)
    W, H = scene.width * box, scene.height * box
    f = _supersample(W, H)
    canvas = Image.new("RGBA", (W, H), _rgb(scene.background) + (255,) if scene.background else (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    # 1. frame shapes (all outside the QR block and its quiet zone)
    for shape in scene.shapes:
        if isinstance(shape, Poly):
            _paint(canvas, _mask([(_scale(geo.poly_path(shape.points), box), 255)], W, H, f), _rgb(shape.fill))
        elif isinstance(shape, Box):
            fill, stroke = _box_paths(shape, box)
            if fill:
                _paint(canvas, _mask(fill, W, H, f), _rgb(shape.fill))
            if stroke:
                _paint(canvas, _mask(stroke, W, H, f), _rgb(shape.stroke))

    # 2. the QR block keeps its own background so the quiet zone is never tinted by the frame
    if scene.block_backing:
        bx, by, bw, bh = scene.block
        draw.rectangle((bx * box, by * box, (bx + bw) * box - 1, (by + bh) * box - 1), fill=_rgb(scene.block_backing) + (255,))

    # 3. label
    if scene.label:
        _draw_label(canvas, scene.label, box)

    # 4. data modules (one mask for the whole grid, painted through the fill)
    ox, oy = scene.origin
    side = scene.n * box
    flags = np.zeros((scene.n, scene.n), np.uint8)
    for x, y in scene.modules:
        flags[y - oy, x - ox] = 1
    if scene.pattern == "square":
        tile = np.full((box, box), 255, np.uint8)
    else:
        tf = max(1, min(4, 256 // box))
        tile = np.asarray(_mask([(_scale(geo.module_path(scene.pattern, 0, 0), box), 255)], box, box, tf), np.uint8)
    grid = np.kron(flags, tile).astype(np.uint8)
    mask = Image.fromarray(grid, "L")
    if scene.fill.kind == "solid":
        _paint(canvas, mask, _rgb(scene.fill.c1), (ox * box, oy * box))
    else:
        layer = _gradient(scene, side).convert("RGBA")
        layer.putalpha(mask)
        canvas.alpha_composite(layer, dest=(ox * box, oy * box))

    # 5. position markers, drawn independently of the data pattern
    for eye in scene.eyes:
        size = 7 * box
        outer, hole = geo.eye_ring(eye.outer, 0, 0)
        ring = _mask([(_scale(outer, box), 255), (_scale(hole, box), 0)], size, size, _supersample(size, size))
        _paint(canvas, ring, _rgb(eye.outer_color), (eye.x * box, eye.y * box))
        centre = _mask([(_scale(geo.eye_centre(eye.inner, 0, 0), box), 255)], size, size, _supersample(size, size))
        _paint(canvas, centre, _rgb(eye.inner_color), (eye.x * box, eye.y * box))

    # 6. logo, centred in the cleared area
    if scene.logo:
        _draw_logo(canvas, scene, box)
    return canvas


def _draw_label(canvas: Image.Image, label: Label, box: int) -> None:
    target_w = label.width * box
    px = max(6, int(round(label.size * box)))
    font = _font(label.bold, px)
    measured = font.getlength(label.text)
    if measured > 0 and abs(measured - target_w) > 1:      # match the Helvetica-based layout width exactly
        font = _font(label.bold, max(6, int(round(px * target_w / measured))))
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    left = label.cx * box - font.getlength(label.text) / 2
    baseline = (label.cy + geo.baseline_offset(label.size)) * box
    ImageDraw.Draw(layer).text((left, baseline), label.text, font=font, fill=_rgb(label.color) + (255,), anchor="ls")
    canvas.alpha_composite(layer)


def _draw_logo(canvas: Image.Image, scene: Scene, box: int) -> None:
    logo = scene.logo
    side = max(2, int(round(logo.side * box)))
    img = Image.open(io.BytesIO(logo.data)).convert("RGBA")
    img.thumbnail((side, side), Image.LANCZOS)
    cx, cy = (logo.x + logo.side / 2) * box, (logo.y + logo.side / 2) * box
    canvas.alpha_composite(img, dest=(int(round(cx - img.width / 2)), int(round(cy - img.height / 2))))


def logo_png_for_vector(scene: Scene, box: int) -> tuple[bytes, int, int]:
    """Logo re-encoded as a clean PNG at export resolution (used by SVG/PDF; strips any metadata)."""
    side = max(2, int(round(scene.logo.side * box)))
    img = Image.open(io.BytesIO(scene.logo.data)).convert("RGBA")
    img.thumbnail((side, side), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue(), img.width, img.height
