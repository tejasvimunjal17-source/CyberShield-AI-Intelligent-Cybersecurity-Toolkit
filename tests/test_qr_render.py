"""Rendering and export tests: raster, SVG, PDF, formats, preview/export consistency.

A real QR matrix comes from OpenCV (tests/qr_matrix.py) because the `qrcode` package is not always installed;
the renderers only see a boolean matrix. Real-Chromium and poppler checks are optional and skip when unavailable.
"""

import base64
import io
import os
import re
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zlib
from unittest import mock

import numpy as np
from PIL import Image

from qr_tools import exporter as ex
from qr_tools import generator as gen
from qr_tools.design import COLOR_PRESETS, STYLE_PRESETS, Design
from qr_tools.generator import QRError
from qr_tools.render_pdf import render_pdf
from qr_tools.render_raster import render_raster
from qr_tools.render_svg import render_svg
from qr_tools.scene import build_scene, pixel_box
from tests.qr_matrix import cv2_matrix

try:
    from playwright.sync_api import sync_playwright
    HAVE_PLAYWRIGHT = True
except ImportError:                                      # pragma: no cover
    HAVE_PLAYWRIGHT = False

PAYLOAD = "https://cybershield.example/qr?ref=demo"


def png(color=(220, 30, 90, 255), size=(80, 80)):
    buf = io.BytesIO()
    Image.new("RGBA", size, color).save(buf, "PNG")
    return buf.getvalue()


def fake_matrix(data, error_correction="M"):
    return cv2_matrix(gen.build_text_payload(data), error_correction)


class Base(unittest.TestCase):
    def setUp(self):
        ex.clear_cache()
        patcher = mock.patch.object(gen, "make_matrix", side_effect=fake_matrix)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(ex.clear_cache)

    def scene(self, **kw):
        d = Design(**kw).validate()
        return build_scene(cv2_matrix(PAYLOAD, d.error_correction), d), d

    @staticmethod
    def px(img, scene, box, x, y):
        return img.getpixel((int((scene.origin[0] + x + 0.5) * box), int((scene.origin[1] + y + 0.5) * box)))


class RasterTests(Base):
    def test_output_dimensions_follow_the_selected_size(self):
        for target in (512, 768, 1024, 2048):
            s, d = self.scene(target_px=target)
            img = render_raster(s, target)
            box = pixel_box(s, target)
            self.assertEqual(img.size, (s.width * box, s.height * box))
            self.assertLessEqual(img.width, target)
            self.assertGreater(img.width, target - s.width)       # never more than one module-width short

    def test_4096_px_renders_within_bounds(self):
        s, d = self.scene(target_px=4096, pattern="rounded", fill="diagonal", fg="#0B3C8C", fg2="#0F766E")
        img = render_raster(s, 4096)
        self.assertLessEqual(max(img.size), 4096)
        self.assertGreater(max(img.size), 4096 - s.width)

    def test_solid_colors_and_background(self):
        s, d = self.scene(fg="#0B3C8C", bg="#FFEECC")
        img = render_raster(s, 768)
        box = pixel_box(s, 768)
        x, y = s.modules[0]
        self.assertEqual(img.getpixel((int((x + .5) * box), int((y + .5) * box))), (0x0B, 0x3C, 0x8C, 255))
        self.assertEqual(img.getpixel((2, 2)), (0xFF, 0xEE, 0xCC, 255))

    def test_every_pattern_draws_differently_but_keeps_the_same_modules(self):
        shots = {}
        for pattern in ("square", "rounded", "dots", "diamond"):
            s, d = self.scene(pattern=pattern)
            shots[pattern] = np.asarray(render_raster(s, 768))
            self.assertEqual(len(s.modules), len(self.scene()[0].modules))
        names = list(shots)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                self.assertFalse(np.array_equal(shots[a], shots[b]), f"{a} == {b}")

    def test_transparent_background_is_really_transparent(self):
        s, d = self.scene(transparent=True)
        img = render_raster(s, 768)
        box = pixel_box(s, 768)
        self.assertEqual(img.mode, "RGBA")
        self.assertEqual(img.getpixel((1, 1))[3], 0)                              # quiet zone
        x, y = s.modules[0]
        self.assertEqual(img.getpixel((int((x + .5) * box), int((y + .5) * box)))[3], 255)   # a module is opaque
        self.assertEqual(Image.open(io.BytesIO(ex.export(PAYLOAD, d, "png").data)).getpixel((1, 1))[3], 0)
        opaque, _ = self.scene()
        self.assertEqual(render_raster(opaque, 768).getchannel("A").getextrema(), (255, 255))

    def test_gradients_change_color_across_the_code(self):
        def dark_colors(img, s, box):
            return [img.getpixel((int((x + .5) * box), int((y + .5) * box)))[:3] for x, y in s.modules]
        for kind in ("linear", "diagonal", "radial"):
            s, d = self.scene(fill=kind, fg="#FF0000", fg2="#0000FF")
            img = render_raster(s, 1024)
            box = pixel_box(s, 1024)
            cols = dark_colors(img, s, box)
            self.assertGreater(len({c for c in cols}), 20, kind)                       # many distinct colors
            ox, oy = s.origin
            left = [c for (x, y), c in zip(s.modules, cols) if x - ox < 6]
            right = [c for (x, y), c in zip(s.modules, cols) if x - ox > s.n - 7]
            centre = [c for (x, y), c in zip(s.modules, cols) if abs(x - ox - s.n / 2) < 4 and abs(y - oy - s.n / 2) < 4]
            if kind in ("linear", "diagonal"):
                self.assertGreater(np.mean([c[0] for c in left]), np.mean([c[0] for c in right]) + 40, kind)  # red -> blue
            else:
                self.assertGreater(np.mean([c[0] for c in centre]), 150, kind)            # centre starts red
                corner = [c for (x, y), c in zip(s.modules, cols) if (x - ox > s.n - 6 and y - oy > s.n - 6)]
                self.assertGreater(np.mean([c[2] for c in corner]), 100, kind)

    def test_marker_colors_are_independent_of_the_data_pattern(self):
        s, d = self.scene(fg="#000000", eye_outer_color="#FF0000", eye_inner_color="#00AA00")
        img = render_raster(s, 1024)
        box = pixel_box(s, 1024)
        for eye in s.eyes:
            self.assertEqual(img.getpixel((int((eye.x + .5) * box), int((eye.y + 3.5) * box)))[:3], (255, 0, 0))
            self.assertEqual(img.getpixel((int((eye.x + 3.5) * box), int((eye.y + 3.5) * box)))[:3], (0, 170, 0))
        x, y = s.modules[0]
        self.assertEqual(img.getpixel((int((x + .5) * box), int((y + .5) * box)))[:3], (0, 0, 0))

    def test_logo_is_drawn_centred_and_clears_modules(self):
        s, d = self.scene(logo_bytes=png(), error_correction="H", pattern="rounded")
        img = render_raster(s, 1024)
        box = pixel_box(s, 1024)
        cx, cy = s.origin[0] + s.n / 2, s.origin[1] + s.n / 2
        self.assertEqual(img.getpixel((int(cx * box), int(cy * box)))[:3], (220, 30, 90))
        hx, hy, hw, hh = s.logo.hole
        self.assertAlmostEqual(hx + hw / 2, cx)
        self.assertAlmostEqual(hy + hh / 2, cy)
        no_logo, _ = self.scene(error_correction="H", pattern="rounded")
        self.assertFalse(np.array_equal(np.asarray(img), np.asarray(render_raster(no_logo, 1024))))

    def test_label_text_is_drawn_inside_the_frame_only(self):
        s, d = self.scene(frame="badge", cta_text="Scan Me", cta_color="#FFFFFF", frame_color="#0B1628")
        img = np.asarray(render_raster(s, 1024).convert("RGB")).astype(int)
        box = pixel_box(s, 1024)
        lb = s.label
        band_h = int(np.ceil(lb.size)) + 2                                        # the navy label band, in modules
        y0, y1 = int((lb.cy - band_h / 2 + 0.3) * box), int((lb.cy + band_h / 2 - 0.3) * box)   # strictly inside the band
        x0, x1 = int((lb.cx - lb.width / 2 - 1) * box), int((lb.cx + lb.width / 2 + 1) * box)
        band = img[y0:y1, x0:x1]
        self.assertTrue(((band == [11, 22, 40]).all(axis=2)).mean() > 0.5)         # the window really is on the navy badge
        self.assertGreater((band.sum(axis=2) > 700).sum(), 200)                    # and white text pixels are present in it
        bx, by, bw, bh = s.block
        code = img[by * box:(by + bh) * box, bx * box:(bx + bw) * box]
        self.assertFalse(((code == [11, 22, 40]).all(axis=2)).any(), "frame color leaked into the code's quiet zone")


class ExportFormatTests(Base):
    MAGIC = {"png": b"\x89PNG\r\n\x1a\n", "jpg": b"\xff\xd8\xff", "svg": b"<?xml", "pdf": b"%PDF-"}

    def test_every_offered_format_is_genuine_and_correctly_labelled(self):
        self.assertEqual(set(ex.FORMATS), {"png", "jpg", "tiff", "svg", "pdf"})
        d = Design(pattern="rounded")
        for fmt, spec in ex.FORMATS.items():
            e = ex.export(PAYLOAD, d, fmt)
            self.assertEqual(e.filename, f"cybershield_qr.{spec.ext}")
            self.assertEqual(e.mime, spec.mime)
            if fmt in self.MAGIC:
                self.assertTrue(e.data.startswith(self.MAGIC[fmt]), fmt)
        tiff = ex.export(PAYLOAD, d, "tiff").data
        self.assertIn(tiff[:4], (b"II*\x00", b"MM\x00*"))
        self.assertEqual({f.mime for f in ex.FORMATS.values()},
                         {"image/png", "image/jpeg", "image/tiff", "image/svg+xml", "application/pdf"})

    def test_raster_files_open_as_their_own_format_with_reported_dimensions(self):
        for fmt, pil_name in (("png", "PNG"), ("jpg", "JPEG"), ("tiff", "TIFF")):
            e = ex.export(PAYLOAD, Design(target_px=768), fmt)
            im = Image.open(io.BytesIO(e.data))
            self.assertEqual(im.format, pil_name)
            self.assertEqual(im.size, (e.width_px, e.height_px))
            self.assertLessEqual(im.width, 768)

    def test_jpg_has_no_transparency_and_is_filled_with_the_background(self):
        e = ex.export(PAYLOAD, Design(transparent=True, bg="#FFEECC"), "jpg")
        im = Image.open(io.BytesIO(e.data))
        self.assertEqual(im.mode, "RGB")
        self.assertTrue(any("cannot be transparent" in n for n in e.notes))
        r, g, b = im.getpixel((1, 1))
        self.assertTrue(r > 240 and g > 240 and b > 240)                           # white fill for a transparent design

    def test_transparent_tiff_and_png_keep_alpha(self):
        for fmt in ("png", "tiff"):
            im = Image.open(io.BytesIO(ex.export(PAYLOAD, Design(transparent=True), fmt).data))
            self.assertEqual(im.mode, "RGBA")
            self.assertEqual(im.getpixel((1, 1))[3], 0)

    def test_unsupported_formats_are_rejected(self):
        for bad in ("eps", "gif", "bmp", "webp", "exe", "", None):
            with self.assertRaises(QRError, msg=bad):
                ex.export(PAYLOAD, Design(), bad)
        with self.assertRaisesRegex(QRError, "EPS is not offered"):
            ex.export(PAYLOAD, Design(), "eps")
        self.assertIn("eps", ex.NOT_OFFERED)

    def test_empty_or_invalid_input_never_produces_a_file(self):
        for payload in ("", "   ", None):
            with self.assertRaises(QRError):
                ex.export(payload, Design(), "png")
        with self.assertRaises(QRError):
            ex.export(PAYLOAD, Design(fg="red"), "png")
        with self.assertRaises(QRError):
            ex.export(PAYLOAD, Design(logo_bytes=b"not an image"), "png")

    def test_format_notes_explain_every_fallback(self):
        d = Design(transparent=True, logo_bytes=png(), error_correction="H", frame="badge", cta_text="Hi").validate()
        self.assertTrue(any("cannot be transparent" in n for n in ex.format_notes(d, "jpg")))
        self.assertTrue(any("bitmap" in n for n in ex.format_notes(d, "svg")))
        self.assertTrue(any("bitmap" in n for n in ex.format_notes(d, "pdf")))
        self.assertTrue(any("Helvetica" in n for n in ex.format_notes(d, "pdf")))
        self.assertEqual(ex.format_notes(Design().validate(), "png"), [])


class ConsistencyTests(Base):
    def test_preview_and_png_export_are_the_same_picture(self):
        d = Design(pattern="dots", fill="diagonal", fg="#6D28D9", fg2="#1D4ED8", frame="tag", cta_text="Follow Us",
                   target_px=768, logo_bytes=png(), error_correction="H")
        preview, w, h = ex.preview_png(PAYLOAD, d)
        export = Image.open(io.BytesIO(ex.export(PAYLOAD, d, "png").data)).convert("RGB")
        self.assertEqual((w, h), export.size)
        self.assertTrue(np.array_equal(np.asarray(Image.open(io.BytesIO(preview)).convert("RGB")), np.asarray(export)))

    def test_large_exports_match_the_preview_scene(self):
        d = Design(pattern="rounded", target_px=2048)
        preview, w, h = ex.preview_png(PAYLOAD, d, max_px=1024)
        big = Image.open(io.BytesIO(ex.export(PAYLOAD, d, "png").data)).convert("RGB")
        small = np.asarray(Image.open(io.BytesIO(preview)).convert("RGB"), dtype=int)
        shrunk = np.asarray(big.resize((w, h), Image.BOX), dtype=int)
        self.assertLess(np.abs(small - shrunk).mean(), 6)

    def test_svg_and_pdf_are_drawn_from_the_same_scene(self):
        s, d = Base.scene(self, pattern="dots", frame="bubble", cta_text="Visit Website", logo_bytes=png(), error_correction="H")
        svg = render_svg(s, 1024)
        path = re.search(r'<path fill="[^"]+"[^>]* d="([^"]+)"', svg).group(1)
        self.assertEqual(path.count("M"), len(s.modules))                           # one SVG subpath per scene module
        box = pixel_box(s, 1024)
        self.assertIn(f'width="{s.width * box}" height="{s.height * box}"', svg)
        pdf = render_pdf(s, 1024)
        content = b"".join(zlib.decompress(m.group(1)) for m in re.finditer(rb"stream\n(.*?)\nendstream", pdf, flags=re.S)
                           if m.group(1)[:1] == b"x")
        self.assertGreaterEqual(content.count(b"\nh"), len(s.modules))              # at least one closed PDF path per module
        self.assertIn(b"/Im1 Do", content)                                          # the logo is placed
        m = re.search(rb"/MediaBox \[0 0 ([\d.]+) ([\d.]+)\]", pdf)
        self.assertAlmostEqual(float(m.group(1)), s.width * box * 72 / 300, delta=0.01)   # same scene -> same proportions

    def test_every_setting_change_changes_the_output(self):
        base = Design(target_px=768)
        ref = ex.export(PAYLOAD, base, "png").data
        from dataclasses import replace
        for change in (dict(fg="#0B3C8C"), dict(bg="#FFEECC"), dict(pattern="dots"), dict(eye_inner="circle"), dict(fill="radial"),
                       dict(quiet_zone=6), dict(error_correction="H"), dict(transparent=True), dict(frame="border"),
                       dict(logo_bytes=png(), error_correction="H"), dict(target_px=1024)):
            self.assertNotEqual(ex.export(PAYLOAD, replace(base, **change), "png").data, ref, change)
        self.assertNotEqual(ex.export(PAYLOAD + "x", base, "png").data, ref)
        sizes = {t: ex.export(PAYLOAD, replace(base, target_px=t), "png") for t in (512, 1024)}
        self.assertLess(sizes[512].width_px, sizes[1024].width_px)

    def test_content_change_changes_the_matrix_actually_encoded(self):
        a = ex.prepare("https://a.example/1", Design())[2]
        b = ex.prepare("https://b.example/2", Design())[2]
        self.assertNotEqual(a, b)

    def test_error_correction_level_reaches_the_matrix(self):
        sizes = {lvl: len(ex.prepare(PAYLOAD, Design(error_correction=lvl))[2]) for lvl in "LMQH"}
        self.assertLessEqual(sizes["L"], sizes["M"])
        self.assertLessEqual(sizes["M"], sizes["Q"])
        self.assertLessEqual(sizes["Q"], sizes["H"])
        self.assertLess(sizes["L"], sizes["H"])

    def test_exports_are_deterministic(self):
        d = Design(pattern="rounded", frame="badge", cta_text="Scan Me")
        for fmt in ("png", "svg", "pdf"):
            self.assertEqual(ex.export(PAYLOAD, d, fmt).data, ex.export(PAYLOAD, d, fmt).data, fmt)


class SvgSafetyTests(Base):
    ALLOWED = {"svg", "title", "defs", "linearGradient", "radialGradient", "stop", "rect", "polygon", "text", "path", "image"}

    def svg(self, **kw):
        s, d = self.scene(**kw)
        return render_svg(s, d.target_px)

    def test_well_formed_with_only_allowed_elements_and_no_scripts(self):
        text = self.svg(pattern="rounded", fill="radial", fg="#6D28D9", fg2="#1D4ED8", frame="bubble", cta_text="Hi",
                        logo_bytes=png(), error_correction="H")
        root = ET.fromstring(text.encode())
        tags = {el.tag.split("}")[1] for el in root.iter()}
        self.assertLessEqual(tags, self.ALLOWED)
        low = text.lower()
        for bad in ("<script", "onload", "onclick", "javascript:", "<foreignobject", "<iframe", "http://www.evil"):
            self.assertNotIn(bad, low)
        hrefs = [v for el in root.iter() for k, v in el.attrib.items() if k.endswith("href")]
        self.assertTrue(hrefs)
        for h in hrefs:
            self.assertTrue(h.startswith("data:image/png;base64,"))

    def test_label_text_is_xml_escaped(self):
        s, d = self.scene(frame="badge", cta_text="<b>&\"'", cta_color="#FFFFFF")
        text = render_svg(s, 768)
        self.assertNotIn("<b>", text)
        root = ET.fromstring(text.encode())
        label = [el.text for el in root.iter() if el.tag.endswith("text")][0]
        self.assertEqual(label, "<b>&\"'")                                         # escaped on the wire, literal once parsed

    def test_plain_codes_are_pure_vector_with_no_embedded_bitmap(self):
        text = self.svg(pattern="dots", fill="linear", fg="#0B3C8C", fg2="#0F766E")
        self.assertNotIn("<image", text)
        self.assertIn("<linearGradient", text)
        self.assertNotIn("base64", text)
        self.assertIn("<radialGradient", self.svg(fill="radial", fg="#6D28D9", fg2="#1D4ED8"))

    def test_transparent_svg_has_no_background_rect_and_opaque_has_one(self):
        self.assertNotIn('<rect width=', self.svg(transparent=True))
        self.assertIn('<rect width=', self.svg())


class PdfTests(Base):
    def pdf(self, **kw):
        s, d = self.scene(**kw)
        return render_pdf(s, d.target_px), s, d

    def test_valid_structure_and_xref(self):
        data, s, d = self.pdf(pattern="rounded", frame="badge", cta_text="Scan Me (now)", logo_bytes=png(), error_correction="H",
                              fill="diagonal", fg="#6D28D9", fg2="#1D4ED8")
        self.assertTrue(data.startswith(b"%PDF-1.4"))
        self.assertTrue(data.rstrip().endswith(b"%%EOF"))
        startxref = int(re.search(rb"startxref\n(\d+)\n%%EOF", data).group(1))
        self.assertEqual(data[startxref:startxref + 4], b"xref")
        count = int(re.search(rb"xref\n0 (\d+)\n", data).group(1))
        offsets = re.findall(rb"(\d{10}) 00000 n ", data)
        self.assertEqual(len(offsets), count - 1)
        for i, off in enumerate(offsets, 1):
            self.assertTrue(data[int(off):].startswith(f"{i} 0 obj".encode()), i)

    def test_page_size_is_the_png_size_at_300_dpi(self):
        data, s, d = self.pdf(target_px=1024)
        box = pixel_box(s, 1024)
        expect = s.width * box * 72 / 300
        m = re.search(rb"/MediaBox \[0 0 ([\d.]+) ([\d.]+)\]", data)
        self.assertAlmostEqual(float(m.group(1)), expect, delta=0.01)
        self.assertAlmostEqual(float(m.group(2)), s.height * box * 72 / 300, delta=0.01)

    def test_contains_nothing_active(self):
        data, *_ = self.pdf(logo_bytes=png(), error_correction="H", frame="tag", cta_text="Hi")
        for bad in (b"/JS", b"/JavaScript", b"/OpenAction", b"/Launch", b"/URI", b"/AA", b"/EmbeddedFile", b"/SubmitForm"):
            self.assertNotIn(bad, data)

    def test_label_text_is_escaped_in_the_content_stream(self):
        import zlib
        data, *_ = self.pdf(frame="badge", cta_text="A (b) \\ c", cta_color="#FFFFFF")
        streams = [zlib.decompress(m.group(1)) for m in re.finditer(rb"stream\n(.*?)\nendstream", data, flags=re.S)
                   if m.group(1)[:1] == b"x"]
        self.assertTrue(any(b"(A \\(b\\) \\\\ c) Tj" in s for s in streams))

    def test_transparent_pdf_has_no_page_fill_and_gradient_uses_shading(self):
        import zlib
        def stream(data):
            return b"".join(zlib.decompress(m.group(1)) for m in re.finditer(rb"stream\n(.*?)\nendstream", data, flags=re.S)
                            if m.group(1)[:1] == b"x")
        opaque, so, _ = self.pdf(bg="#FFEECC")
        transparent, st, _ = self.pdf(transparent=True, bg="#FFEECC")
        page_fill = rb"^[\d. ]+ rg\n0 0 [\d.]+ [\d.]+ re\nf"
        self.assertRegex(stream(opaque), page_fill)                                  # opaque: first operation paints the page
        self.assertNotRegex(stream(transparent), page_fill)                          # transparent: the page is left unpainted
        grad, *_ = self.pdf(fill="radial", fg="#6D28D9", fg2="#1D4ED8")
        self.assertIn(b"/ShadingType 3", grad)
        self.assertIn(b"/ShadingType 2", self.pdf(fill="linear", fg="#6D28D9", fg2="#1D4ED8")[0])

    def test_deterministic_bytes(self):
        a, *_ = self.pdf(pattern="dots")
        b, *_ = self.pdf(pattern="dots")
        self.assertEqual(a, b)


class HtmlEmbedTests(Base):
    def test_snippet_is_escaped_inert_and_round_trips_to_the_svg(self):
        d = Design(pattern="rounded")
        snippet = ex.embed_html(PAYLOAD, d, 'x" onload="alert(1)"><script>')
        self.assertNotIn("<script>", snippet)
        self.assertNotIn('" onload="', snippet)
        self.assertIn("&quot;", snippet)
        self.assertTrue(snippet.startswith('<img src="data:image/svg+xml;base64,'))
        b64 = re.search(r"base64,([^\"]+)\"", snippet).group(1)
        self.assertEqual(base64.b64decode(b64), ex.export(PAYLOAD, d, "svg").data)
        from html.parser import HTMLParser

        class Grab(HTMLParser):
            tags, attrs = [], {}

            def handle_starttag(self, tag, attrs):
                Grab.tags.append(tag)
                Grab.attrs = dict(attrs)

        Grab().feed(snippet)
        self.assertEqual(Grab.tags, ["img"])                                         # exactly one element, nothing injected
        self.assertEqual(set(Grab.attrs), {"src", "width", "height", "alt"})         # no onload/onerror attributes appeared
        self.assertEqual(Grab.attrs["alt"], 'x" onload="alert(1)"><script>')         # the text survives, as text only

    def test_oversized_designs_are_refused_instead_of_truncated(self):
        with mock.patch.object(ex, "HTML_EMBED_MAX_BYTES", 100):
            with self.assertRaises(QRError):
                ex.embed_html(PAYLOAD, Design(pattern="dots"), "x")


@unittest.skipUnless(HAVE_PLAYWRIGHT, "Playwright not installed (optional)")
class ChromiumSvgTests(Base):
    """The SVG is rendered by a real browser engine and compared with the raster renderer for the same scene."""

    @classmethod
    def setUpClass(cls):
        try:
            cls.pw = sync_playwright().start()
            cls.browser = cls.pw.chromium.launch()
        except Exception as exc:                                                  # pragma: no cover
            if hasattr(cls, "pw"):
                cls.pw.stop()
            raise unittest.SkipTest(f"Chromium cannot be launched: {exc}")

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def test_svg_matches_raster_and_decodes(self):
        import cv2
        page = self.browser.new_page(viewport={"width": 900, "height": 900})
        designs = [Design(), Design(**STYLE_PRESETS["Rounded"], fg="#0B3C8C"),
                   Design(**STYLE_PRESETS["Circular"], **COLOR_PRESETS["Teal and dark blue"]),
                   Design(fill="radial", fg="#6D28D9", fg2="#0EA5E9"),
                   Design(frame="bubble", cta_text="Visit <Us> & more", frame_color="#0F766E", logo_bytes=png(),
                          error_correction="H", pattern="rounded")]
        for d in designs:
            s, d = self.scene(**{k: v for k, v in d.__dict__.items()})
            svg, ras = render_svg(s, 768), render_raster(s, 768)
            w, h = ras.size
            b64 = base64.b64encode(svg.encode()).decode()
            page.set_content(f'<body style="margin:0;background:#fff"><img id=i src="data:image/svg+xml;base64,{b64}" width={w} height={h}></body>')
            page.wait_for_timeout(100)
            shot = Image.open(io.BytesIO(page.locator("#i").screenshot())).convert("RGB")
            flat = Image.new("RGB", ras.size, (255, 255, 255))
            flat.paste(ras, mask=ras.getchannel("A"))
            diff = np.abs(np.asarray(flat, dtype=int) - np.asarray(shot.resize((w, h)), dtype=int))
            self.assertLess((diff.max(axis=2) > 96).mean(), 0.02, d.frame)           # < 2% of pixels differ (text edges)
            gray = np.array(shot.convert("L"))
            ok = (cv2.QRCodeDetector().detectAndDecode(gray)[0] == PAYLOAD
                  or cv2.QRCodeDetectorAruco().detectAndDecode(gray)[0] == PAYLOAD)
            self.assertTrue(ok, f"Chromium-rendered SVG did not decode ({d.pattern}, {d.fill}, {d.frame})")
        page.close()


@unittest.skipUnless(shutil.which("pdftoppm") and shutil.which("pdfinfo"), "poppler (pdftoppm/pdfinfo) not installed (optional)")
class PopplerPdfTests(Base):
    """The PDF is rendered by poppler, an independent PDF implementation, and compared with the raster renderer."""

    def test_pdf_renders_like_the_raster_and_decodes(self):
        import cv2
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        for d in (Design(), Design(**STYLE_PRESETS["Circular"], **COLOR_PRESETS["Purple and blue"]), Design(fill="linear", fg="#0B3C8C", fg2="#0F766E"),
                  Design(frame="badge", cta_text="Scan Me", pattern="rounded"),
                  Design(frame="bubble", cta_text="Visit Website", logo_bytes=png(), error_correction="H", pattern="rounded")):
            s, d = self.scene(**d.__dict__)
            f = os.path.join(tmp, "a.pdf")
            with open(f, "wb") as fh:
                fh.write(render_pdf(s, 1024))
            info = subprocess.run(["pdfinfo", f], capture_output=True, text=True).stdout
            self.assertIn("Pages:", info)
            subprocess.run(["pdftoppm", "-r", "300", "-png", "-singlefile", f, os.path.join(tmp, "p")], check=True, capture_output=True)
            shot = Image.open(os.path.join(tmp, "p.png")).convert("RGB")
            ras = render_raster(s, 1024)
            flat = Image.new("RGB", ras.size, (255, 255, 255))
            flat.paste(ras, mask=ras.getchannel("A"))
            diff = np.abs(np.asarray(flat, dtype=int) - np.asarray(shot.resize(ras.size), dtype=int))
            self.assertLess((diff.max(axis=2) > 96).mean(), 0.03)
            gray = np.array(shot.convert("L"))
            self.assertTrue(cv2.QRCodeDetector().detectAndDecode(gray)[0] == PAYLOAD
                            or cv2.QRCodeDetectorAruco().detectAndDecode(gray)[0] == PAYLOAD)
        text = subprocess.run(["pdftotext", f, "-"], capture_output=True, text=True).stdout
        self.assertIn("Visit Website", text)                                       # the label is real, extractable text


if __name__ == "__main__":
    unittest.main()
