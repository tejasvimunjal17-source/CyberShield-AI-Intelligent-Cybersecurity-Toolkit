"""Vector PDF output for a Scene, written directly (no PDF library, no new dependency).

The page contains real vector paths for modules, position markers and frames; gradients are
PDF shading dictionaries; the label uses the built-in Helvetica fonts (not embedded: every PDF
viewer has them). A logo is the one raster element: it is embedded as an image object. The page
size is the image size at 300 dpi (the same pixel size as the PNG export), so the PDF can be
placed at a predictable physical size and scaled without losing sharpness.

The output is deterministic (no timestamps), so identical settings give identical bytes.
"""

from __future__ import annotations

import io
import zlib

from PIL import Image

from qr_tools import geometry as geo
from qr_tools.render_raster import _rgb
from qr_tools.scene import Box, Poly, Scene, pixel_box

DPI = 300
_n = geo._n


def _color(c: str) -> str:
    r, g, b = _rgb(c)
    return f"{_n(r / 255)} {_n(g / 255)} {_n(b / 255)}"


def _pdf_string(text: str) -> str:
    return "(" + text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") + ")"


class _Writer:
    def __init__(self) -> None:
        self.objects: list[bytes] = []

    def add(self, body: bytes | str) -> int:
        self.objects.append(body.encode("latin-1") if isinstance(body, str) else body)
        return len(self.objects)

    def stream(self, header: str, data: bytes) -> int:
        return self.add(f"<< {header} /Length {len(data)} >>\nstream\n".encode("latin-1") + data + b"\nendstream")

    def reserve(self) -> int:
        self.objects.append(b"")
        return len(self.objects)

    def set(self, num: int, body: bytes | str) -> None:
        self.objects[num - 1] = body.encode("latin-1") if isinstance(body, str) else body

    def dump(self, root: int, info: int) -> bytes:
        out = io.BytesIO()
        out.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = []
        for i, body in enumerate(self.objects, 1):
            offsets.append(out.tell())
            out.write(f"{i} 0 obj\n".encode() + body + b"\nendobj\n")
        xref = out.tell()
        out.write(f"xref\n0 {len(self.objects) + 1}\n0000000000 65535 f \n".encode())
        for off in offsets:
            out.write(f"{off:010d} 00000 n \n".encode())
        out.write(f"trailer\n<< /Size {len(self.objects) + 1} /Root {root} 0 R /Info {info} 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
        return out.getvalue()


def render_pdf(scene: Scene, target_px: int) -> bytes:
    box = pixel_box(scene, target_px)
    s = box * 72.0 / DPI                          # points per module
    Wp, Hp = scene.width * s, scene.height * s
    fx = lambda v: v * s                           # noqa: E731
    fy = lambda v: Hp - v * s                      # noqa: E731
    P = lambda path: geo.pdf_ops(path, fx, fy)     # noqa: E731

    w = _Writer()
    catalog, pages, page, contents = w.reserve(), w.reserve(), w.reserve(), w.reserve()
    f_reg = w.add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    f_bold = w.add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
    info = w.add("<< /Title (QR code) /Producer (CyberShield AI QR Generator) >>")
    resources = [f"/Font << /F1 {f_reg} 0 R /F2 {f_bold} 0 R >>"]
    c: list[str] = []

    if scene.background:
        c.append(f"{_color(scene.background)} rg\n0 0 {_n(Wp)} {_n(Hp)} re\nf")

    for shape in scene.shapes:
        if isinstance(shape, Box):
            if shape.fill:
                c.append(f"{_color(shape.fill)} rg\n{P(geo.rrect_path(shape.x, shape.y, shape.w, shape.h, shape.r))}\nf")
            if shape.stroke and shape.stroke_w:
                c.append(f"{_color(shape.stroke)} RG\n{_n(shape.stroke_w * s)} w\n"
                         f"{P(geo.rrect_path(shape.x, shape.y, shape.w, shape.h, shape.r))}\nS")
        elif isinstance(shape, Poly):
            c.append(f"{_color(shape.fill)} rg\n{P(geo.poly_path(shape.points))}\nf")

    if scene.block_backing:
        bx, by, bw, bh = scene.block
        c.append(f"{_color(scene.block_backing)} rg\n{P(geo.rect_path(bx, by, bw, bh))}\nf")

    if scene.label:
        lb = scene.label
        c.append(f"BT\n/{'F2' if lb.bold else 'F1'} {_n(lb.size * s)} Tf\n{_color(lb.color)} rg\n"
                 f"1 0 0 1 {_n(fx(lb.cx - lb.width / 2))} {_n(fy(lb.cy + geo.baseline_offset(lb.size)))} Tm\n"
                 f"{_pdf_string(lb.text)} Tj\nET")

    module_ops = "\n".join(P(geo.module_path(scene.pattern, x, y)) for x, y in scene.modules)
    if scene.fill.kind == "solid":
        c.append(f"{_color(scene.fill.c1)} rg\n{module_ops}\nf")
    else:
        fl = scene.fill
        x, y, wd, ht = fl.rect
        fn = f"<< /FunctionType 2 /Domain [0 1] /C0 [{_color(fl.c1)}] /C1 [{_color(fl.c2)}] /N 1 >>"
        if fl.kind == "linear":
            shading = f"<< /ShadingType 2 /ColorSpace /DeviceRGB /Coords [{_n(fx(x))} {_n(fy(y))} {_n(fx(x + wd))} {_n(fy(y))}] /Function {fn} /Extend [true true] >>"
        elif fl.kind == "diagonal":
            shading = f"<< /ShadingType 2 /ColorSpace /DeviceRGB /Coords [{_n(fx(x))} {_n(fy(y))} {_n(fx(x + wd))} {_n(fy(y + ht))}] /Function {fn} /Extend [true true] >>"
        else:
            cx, cy = fx(x + wd / 2), fy(y + ht / 2)
            shading = f"<< /ShadingType 3 /ColorSpace /DeviceRGB /Coords [{_n(cx)} {_n(cy)} 0 {_n(cx)} {_n(cy)} {_n(wd * 0.70710678 * s)}] /Function {fn} /Extend [true true] >>"
        sh = w.add(shading)
        resources.append(f"/Shading << /Sh1 {sh} 0 R >>")
        c.append(f"q\n{module_ops}\nW n\n/Sh1 sh\nQ")

    for eye in scene.eyes:
        outer, hole = geo.eye_ring(eye.outer, eye.x, eye.y)
        c.append(f"{_color(eye.outer_color)} rg\n{P(outer)}\n{P(hole)}\nf*")
        c.append(f"{_color(eye.inner_color)} rg\n{P(geo.eye_centre(eye.inner, eye.x, eye.y))}\nf")

    if scene.logo:
        lg = scene.logo
        side = max(2, int(round(lg.side * box)))
        img = Image.open(io.BytesIO(lg.data)).convert("RGBA")
        img.thumbnail((side, side), Image.LANCZOS)
        rgb = zlib.compress(img.convert("RGB").tobytes())
        alpha = zlib.compress(img.getchannel("A").tobytes())
        mask = w.stream(f"/Type /XObject /Subtype /Image /Width {img.width} /Height {img.height} "
                        "/ColorSpace /DeviceGray /BitsPerComponent 8 /Filter /FlateDecode", alpha)
        im = w.stream(f"/Type /XObject /Subtype /Image /Width {img.width} /Height {img.height} /ColorSpace /DeviceRGB "
                      f"/BitsPerComponent 8 /Filter /FlateDecode /SMask {mask} 0 R", rgb)
        resources.append(f"/XObject << /Im1 {im} 0 R >>")
        wpt, hpt = img.width / box * s, img.height / box * s
        cxp, cyp = fx(lg.x + lg.side / 2), fy(lg.y + lg.side / 2)
        c.append(f"q\n{_n(wpt)} 0 0 {_n(hpt)} {_n(cxp - wpt / 2)} {_n(cyp - hpt / 2)} cm\n/Im1 Do\nQ")

    data = zlib.compress("\n".join(c).encode("latin-1"))
    w.set(contents, f"<< /Filter /FlateDecode /Length {len(data)} >>\nstream\n".encode("latin-1") + data + b"\nendstream")
    w.set(page, f"<< /Type /Page /Parent {pages} 0 R /MediaBox [0 0 {_n(Wp)} {_n(Hp)}] "
                f"/Resources << {' '.join(resources)} >> /Contents {contents} 0 R >>")
    w.set(pages, f"<< /Type /Pages /Kids [{page} 0 R] /Count 1 >>")
    w.set(catalog, f"<< /Type /Catalog /Pages {pages} 0 R >>")
    return w.dump(catalog, info)
