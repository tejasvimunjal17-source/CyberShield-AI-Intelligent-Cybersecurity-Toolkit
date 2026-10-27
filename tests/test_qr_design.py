"""Design validation, presets, warnings, logo validation and scene geometry (no qrcode package needed)."""

import io
import unittest
from dataclasses import replace

from PIL import Image

from qr_tools import geometry as geo
from qr_tools import scene as sc
from qr_tools.design import (COLOR_PRESETS, EC_CAPACITY, FRAMES, MAX_LOGO_FRACTION, SIZES, STYLE_PRESETS, Design,
                             auto_label_color, check_logo, logo_coverage, logo_hole_modules, normalize_hex, scan_warnings)
from qr_tools.generator import QRError, contrast_ratio
from tests.qr_matrix import cv2_matrix


def png(size=(64, 64), color=(200, 30, 90, 255), fmt="PNG"):
    buf = io.BytesIO()
    Image.new("RGBA" if fmt == "PNG" else "RGB", size, color if fmt == "PNG" else color[:3]).save(buf, fmt)
    return buf.getvalue()


M = cv2_matrix("https://cybershield.example/qr?ref=demo", "Q")
N = len(M)                                                          # modules per side (derived, never assumed)


class ColorTests(unittest.TestCase):
    def test_valid_hex_is_normalised(self):
        self.assertEqual(normalize_hex("#0b1628"), "#0B1628")
        self.assertEqual(normalize_hex(" #abc "), "#AABBCC")

    def test_invalid_colors_are_rejected(self):
        for bad in ("red", "rgb(0,0,0)", "#12", "#GGGGGG", "0B1628", "#12345678", "", None, "#00000;", "url(x)"):
            with self.assertRaises(QRError, msg=repr(bad)):
                normalize_hex(bad)

    def test_design_validate_normalises_every_color_and_rejects_bad_ones(self):
        d = Design(fg="#abc", bg="#def", fg2="#123", cta_color="#fff", frame_color="#000", eye_outer_color="#0f0").validate()
        self.assertEqual((d.fg, d.bg, d.eye_outer_color), ("#AABBCC", "#DDEEFF", "#00FF00"))
        for field in ("fg", "fg2", "bg", "cta_color", "frame_color", "eye_outer_color", "eye_inner_color"):
            with self.assertRaises(QRError, msg=field):
                replace(Design(), **{field: "blue"}).validate()


class SettingsTests(unittest.TestCase):
    def test_all_four_error_levels_are_accepted_and_others_rejected(self):
        for level in "LMQH":
            self.assertEqual(Design(error_correction=level).validate().error_correction, level)
        self.assertEqual(EC_CAPACITY, {"L": 0.07, "M": 0.15, "Q": 0.25, "H": 0.30})
        for bad in ("X", "", "m", None):
            with self.assertRaises(QRError):
                Design(error_correction=bad).validate()

    def test_quiet_zone_limits(self):
        for ok in (1, 4, 10):
            self.assertEqual(Design(quiet_zone=ok).validate().quiet_zone, ok)
        for bad in (0, 11, -1, 4.5):
            with self.assertRaises(QRError, msg=bad):
                Design(quiet_zone=bad).validate()

    def test_output_sizes(self):
        self.assertEqual(SIZES, (512, 768, 1024, 2048, 4096))
        for bad in (100, 1000, 8192):
            with self.assertRaises(QRError):
                Design(target_px=bad).validate()

    def test_enums_padding_and_logo_ranges(self):
        for kwargs in (dict(pattern="stars"), dict(eye_outer="hex"), dict(eye_inner="x"), dict(fill="conic"), dict(frame="oval"),
                       dict(cta_size="huge"), dict(frame_padding=0), dict(frame_padding=7), dict(logo_fraction=0.01),
                       dict(logo_fraction=MAX_LOGO_FRACTION + 0.01), dict(logo_margin=-1), dict(logo_margin=4)):
            with self.assertRaises(QRError, msg=str(kwargs)):
                Design(**kwargs).validate()

    def test_label_text_rules(self):
        self.assertEqual(Design(cta_text="  Scan Me  ").validate().cta_text, "Scan Me")
        for bad in ("x" * 31, "Escanéame", "Scan 🙂"):
            with self.assertRaises(QRError, msg=bad):
                Design(cta_text=bad).validate()

    def test_quiet_zone_is_applied_around_the_code(self):
        for q in (1, 4, 8):
            s = sc.build_scene(M, Design(quiet_zone=q).validate())
            self.assertEqual((s.width, s.height), (N + 2 * q, N + 2 * q))
            self.assertEqual(s.origin, (q, q))
            self.assertEqual(s.n, N)


class PresetTests(unittest.TestCase):
    def test_every_color_preset_is_valid_and_has_good_contrast(self):
        for name, preset in COLOR_PRESETS.items():
            if preset is None:
                continue
            d = Design(**preset).validate()
            for c in d.module_colors() + list(d.eye_colors()):
                self.assertGreaterEqual(contrast_ratio(c, d.bg), 4.5, f"{name}: {c} on {d.bg}")

    def test_requested_color_presets_exist(self):
        for name in ("Classic black and white", "Cybersecurity blue", "Cyan and navy", "Teal and dark blue",
                     "Purple and blue", "Custom brand colors"):
            self.assertIn(name, COLOR_PRESETS)
        self.assertEqual({"solid", "diagonal"}, {p["fill"] for p in COLOR_PRESETS.values() if p})

    def test_style_presets_use_only_verified_shapes(self):
        for name in ("Classic", "Rounded", "Circular", "Modern geometric"):
            self.assertIn(name, STYLE_PRESETS)
        for name, preset in STYLE_PRESETS.items():
            if preset:
                Design(**preset).validate()
                self.assertNotEqual(preset["eye_outer"], "circle", f"{name}: circular outer rings were not readable in testing")

    def test_default_design_has_no_warnings(self):
        self.assertEqual(scan_warnings(Design().validate(), 29), [])


class WarningTests(unittest.TestCase):
    def text(self, **kw):
        return " ".join(scan_warnings(Design(**kw).validate(), 29))

    def test_contrast_inversion_transparency_quiet_zone(self):
        self.assertIn("Low contrast", self.text(fg="#CCCCCC"))
        self.assertIn("inverted", self.text(fg="#FFFFFF", bg="#000000"))
        self.assertIn("transparent background", self.text(transparent=True))
        self.assertIn("quiet zone", self.text(quiet_zone=2))

    def test_decorative_shapes_gradients_and_circular_markers(self):
        for kw in (dict(pattern="dots"), dict(eye_inner="circle"), dict(fill="linear")):
            self.assertIn("Decorative", self.text(**kw))
        self.assertIn("unverified", self.text(eye_outer="circle"))

    def test_logo_advice(self):
        base = dict(logo_bytes=png())
        self.assertIn("Q or H", self.text(error_correction="M", **base))
        self.assertNotIn("Q or H", self.text(error_correction="H", **base))
        self.assertIn("unreadable", self.text(logo_fraction=0.2, error_correction="H", **base))

    def test_label_contrast_and_transparent_frames(self):
        self.assertIn("label text has low contrast", self.text(frame="badge", cta_text="Hi", cta_color="#222222", frame_color="#0B1628"))
        self.assertIn("Transparency applies outside the frame", self.text(frame="badge", cta_text="Hi", transparent=True))

    def test_auto_label_color_is_readable(self):
        for frame, fc, bg in (("badge", "#0B1628", "#FFFFFF"), ("badge", "#FDE68A", "#FFFFFF"), ("border", "#000000", "#101010")):
            c = auto_label_color(frame, fc, bg)
            sits_on = fc if frame == "badge" else bg
            self.assertGreaterEqual(contrast_ratio(c, sits_on), 4.5)


class LogoValidationTests(unittest.TestCase):
    def test_png_and_jpeg_accepted_by_content(self):
        self.assertEqual(check_logo(png())[0], "PNG")
        self.assertEqual(check_logo(png(fmt="JPEG"))[0], "JPEG")

    def test_wrong_content_is_rejected_whatever_the_name(self):
        gif, bmp = io.BytesIO(), io.BytesIO()
        Image.new("RGB", (40, 40)).save(gif, "GIF")
        Image.new("RGB", (40, 40)).save(bmp, "BMP")
        for data in (gif.getvalue(), bmp.getvalue(), b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>",
                     b"<script>alert(1)</script>", b"MZ\x90\x00 not an image", b"", b"\x89PNG\r\n\x1a\n garbage"):
            with self.assertRaises(QRError):
                check_logo(data)

    def test_truncated_oversized_and_tiny_images_rejected(self):
        with self.assertRaises(QRError):
            check_logo(png()[:60])
        with self.assertRaises(QRError):
            check_logo(png((8, 8)))
        with self.assertRaises(QRError):
            check_logo(png((2500, 100)))
        with self.assertRaises(QRError):
            check_logo(b"\x89PNG" + b"0" * (1024 * 1024 + 1))

    def test_a_polyglot_is_only_ever_read_as_pixels(self):
        sneaky = png() + b"<script>alert(1)</script>"
        self.assertEqual(check_logo(sneaky)[0], "PNG")        # accepted as an image; the extra bytes are never interpreted
        d = Design(logo_bytes=sneaky, error_correction="H").validate()
        s = sc.build_scene(M, d)
        self.assertIsNotNone(s.logo)


class StructureTests(unittest.TestCase):
    def test_finder_patterns_are_verified(self):
        sc.verify_finders(M)
        broken = [row[:] for row in M]
        broken[0][0] = False
        with self.assertRaises(QRError):
            sc.verify_finders(broken)
        with self.assertRaises(QRError):
            sc.verify_finders([[True] * 10] * 10)

    def test_alignment_tables_match_the_qr_standard(self):
        for n, coords in ((25, [6, 18]), (45, [6, 22, 38]), (73, [6, 26, 46, 66]), (177, [6, 30, 58, 86, 114, 142, 170])):
            got = sorted({c[0] for c in sc.alignment_centers(n)} | {6})
            self.assertEqual(got, coords, n)
        self.assertEqual(sc.alignment_centers(21), [])

    def test_logo_may_not_cover_markers_timing_or_format_information(self):
        fatal, _ = sc.structures_under(29, 2, 2, 6)
        self.assertTrue(fatal)
        self.assertTrue(sc.structures_under(29, 5, 12, 6)[0])                  # crosses the timing pattern
        self.assertEqual(sc.structures_under(29, 10, 10, 9), ([], []))
        self.assertTrue(sc.structures_under(45, 17, 17, 11)[1])                # soft: covers the centre alignment pattern

    def test_logo_hole_is_centred_and_module_aligned(self):
        for n in (21, 25, 29, 45, 61, 77):
            for frac in (0.05, 0.12, 0.2):
                for margin in (0, 1, 3):
                    d = Design(logo_fraction=frac, logo_margin=margin)
                    hole = logo_hole_modules(n, d)
                    self.assertEqual((n - hole) % 2, 0, (n, frac, margin))     # same parity: exactly centred
                    self.assertGreaterEqual(hole, n * frac)

    def test_logo_too_large_for_the_error_level_is_refused(self):
        with self.assertRaises(QRError):
            sc.build_scene(M, Design(logo_bytes=png(), error_correction="L", logo_fraction=0.22, logo_margin=3).validate())
        ok = Design(logo_bytes=png(), error_correction="H", logo_fraction=0.12).validate()
        self.assertLess(logo_coverage(29, ok), EC_CAPACITY["H"])
        self.assertIsNotNone(sc.build_scene(M, ok).logo)

    def test_build_scene_itself_refuses_a_corrupted_matrix(self):
        broken = [row[:] for row in M]
        broken[3][3] = False                                   # damage a position marker
        with self.assertRaises(QRError):
            sc.build_scene(broken, Design().validate())

    def test_build_scene_itself_refuses_a_logo_that_would_cover_format_information(self):
        tiny = cv2_matrix("hello", "H")                        # version 1, 21 modules
        self.assertEqual(len(tiny), 21)
        with self.assertRaisesRegex(QRError, "position marker or its format information"):
            sc.build_scene(tiny, Design(logo_bytes=png(), error_correction="H", logo_margin=1).validate())
        ok = sc.build_scene(tiny, Design(logo_bytes=png(), error_correction="H", logo_margin=0, logo_fraction=0.05).validate())
        self.assertIsNotNone(ok.logo)                          # a smaller clear area fits between the structures

    def test_modules_exclude_logo_hole_and_position_markers(self):
        d = Design(logo_bytes=png(), error_correction="H").validate()
        s = sc.build_scene(M, d)
        hx, hy, hw, hh = s.logo.hole
        self.assertFalse([m for m in s.modules if hx <= m[0] < hx + hw and hy <= m[1] < hy + hh])
        ox, oy = s.origin
        finder = {(ox + x, oy + y) for ex, ey in ((0, 0), (N - 7, 0), (0, N - 7)) for x in range(ex, ex + 7) for y in range(ey, ey + 7)}
        self.assertFalse(finder & set(s.modules))
        plain = sc.build_scene(M, Design().validate())
        expected = [(x, y) for y in range(N) for x in range(N)
                    if M[y][x] and not ((x < 7 and y < 7) or (x >= N - 7 and y < 7) or (x < 7 and y >= N - 7))]
        self.assertEqual(sorted(plain.modules), sorted((x + plain.origin[0], y + plain.origin[1]) for x, y in expected))


class FrameTests(unittest.TestCase):
    def scene(self, **kw):
        return sc.build_scene(M, Design(**kw).validate())

    def test_frame_shapes_never_enter_the_code_block(self):
        for frame in FRAMES[1:]:
            for pad in (1, 2, 6):
                s = self.scene(frame=frame, cta_text="Scan Me", frame_padding=pad, cta_color="#FFFFFF")
                bx, by, bw, bh = s.block
                self.assertEqual((bw, bh), (N + 8, N + 8))
                for shape in s.shapes:
                    if isinstance(shape, sc.Poly):
                        ys = [p[1] for p in shape.points]
                        self.assertTrue(max(ys) <= by or min(ys) >= by + bh, f"{frame}: pointer overlaps the code")
                    elif shape.fill and shape.w >= bw and shape.h >= bh:
                        self.assertIsNotNone(s.block_backing, f"{frame}: filled card needs an opaque quiet zone")
                    elif shape.stroke:
                        self.assertTrue(shape.x + shape.stroke_w / 2 <= bx and shape.y + shape.stroke_w / 2 <= by
                                        and shape.x + shape.w - shape.stroke_w / 2 >= bx + bw
                                        and shape.y + shape.h - shape.stroke_w / 2 >= by + bh, f"{frame}: border cuts into the code")
                    else:
                        self.assertTrue(shape.y >= by + bh or shape.y + shape.h <= by, f"{frame}: label bubble overlaps the code")
                if s.label:
                    top, bottom = s.label.cy - s.label.size / 2, s.label.cy + s.label.size / 2
                    self.assertTrue(bottom <= by or top >= by + bh, f"{frame}: label text overlaps the code")
                self.assertTrue(s.width == int(s.width) and s.height == int(s.height))

    def test_label_is_centred_and_fits(self):
        for frame in ("border", "badge", "tag", "bubble"):
            s = self.scene(frame=frame, cta_text="Visit Website")
            self.assertAlmostEqual(s.label.cx, s.width / 2)
            self.assertLessEqual(s.label.width, s.width)
            self.assertEqual(s.label.text, "Visit Website")

    def test_long_text_shrinks_and_impossible_text_is_refused(self):
        long = self.scene(frame="badge", cta_text="Scan to see our whole menu!", cta_size="large")
        self.assertLess(long.label.size, 4)
        self.assertLessEqual(long.label.width, long.width - 2)      # one module of margin each side
        with self.assertRaises(QRError):
            sc.build_scene(cv2_matrix("a", "L"), Design(frame="badge", cta_text="W" * 30, cta_size="large").validate())

    def test_label_less_fancy_frames_fall_back_to_a_plain_rounded_border(self):
        for frame in ("badge", "tag", "bubble"):
            s = self.scene(frame=frame)
            self.assertIsNone(s.label)
            self.assertEqual((s.width, s.height), (s.width, s.width))        # square: no lopsided empty band

    def test_transparent_filled_frames_keep_an_opaque_code_block(self):
        s = self.scene(frame="badge", cta_text="Hi", transparent=True)
        self.assertIsNone(s.background)
        self.assertEqual(s.block_backing, "#FFFFFF")


class GeometryTests(unittest.TestCase):
    def test_every_shape_flattens_to_a_closed_polygon_inside_its_cell(self):
        for pattern in geo.PATTERNS:
            polys = geo.flatten(geo.module_path(pattern, 3, 5))
            self.assertEqual(len(polys), 1)
            for x, y in polys[0]:
                self.assertTrue(3 - 1e-6 <= x <= 4 + 1e-6 and 5 - 1e-6 <= y <= 6 + 1e-6, pattern)

    def test_marker_ring_keeps_the_1_1_3_1_1_proportions(self):
        for kind in geo.EYE_OUTER:
            outer, hole = geo.eye_ring(kind, 0, 0)
            xs = [p[0] for poly in geo.flatten(outer) for p in poly]
            hx = [p[0] for poly in geo.flatten(hole) for p in poly]
            self.assertAlmostEqual(max(xs) - min(xs), 7, places=3)
            self.assertAlmostEqual(max(hx) - min(hx), 5, places=3)       # one-module-thick ring
        for kind in geo.EYE_INNER:
            xs = [p[0] for poly in geo.flatten(geo.eye_centre(kind, 0, 0)) for p in poly]
            self.assertAlmostEqual(max(xs) - min(xs), 3, places=3)

    def test_rounded_marker_radius_stays_within_the_verified_limit(self):
        self.assertLessEqual(geo.EYE_ROUND_RADIUS, 0.7)       # decoded 48/48 up to 0.7; first failure at 0.8

    def test_label_metrics(self):
        self.assertTrue(geo.cta_text_ok("Scan Me!"))
        self.assertFalse(geo.cta_text_ok("é"))
        self.assertGreater(geo.text_width("Scan Me", 3, True), geo.text_width("Scan Me", 3, False))


if __name__ == "__main__":
    unittest.main()
