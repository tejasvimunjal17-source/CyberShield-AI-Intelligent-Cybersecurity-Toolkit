"""Scannability evidence: styled codes are rendered and then actually decoded.

"Decodes" means OpenCV's QR decoders (classic and ArUco) read back exactly the intended payload. That is real
evidence but not proof for every phone: it is the same decoder the app uses for its own check. Anything that
fails here is reported as unverified by the app instead of being called safe.
"""

import io
import unittest
from dataclasses import replace
from unittest import mock

import numpy as np
from PIL import Image, ImageDraw

from qr_tools import exporter as ex
from qr_tools import generator as gen
from qr_tools import geometry as geo
from qr_tools import payloads as pl
from qr_tools.decoder import decode_image_bytes
from qr_tools.design import COLOR_PRESETS, STYLE_PRESETS, Design, scan_warnings
from qr_tools.render_raster import render_raster
from qr_tools.scene import build_scene
from tests.qr_matrix import cv2_matrix
from tests.test_qr_payloads import SAMPLES
from tests.test_qr_render import png

PAYLOADS = ["https://cybershield.example/qr?ref=demo",
            "https://example.com/a/much/longer/path?with=query&and=more&params=1234567890abcdef",
            "WIFI:T:WPA;S:Home;P:secret123;;", "hello", "mailto:a@b.co?subject=Hi",
            "https://wa.me/447700900123?text=Hello", "x" * 200]


def fake_matrix(data, error_correction="M"):
    return cv2_matrix(gen.build_text_payload(data), error_correction)


def read(image, light_surface=True):
    return ex.try_decode(image, light_surface)[0]


class ReliabilityBase(unittest.TestCase):
    def setUp(self):
        ex.clear_cache()
        patcher = mock.patch.object(gen, "make_matrix", side_effect=fake_matrix)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(ex.clear_cache)

    def render(self, payload, design):
        d = design.validate()
        scene = build_scene(cv2_matrix(payload, d.error_correction), d)
        return render_raster(scene, d.target_px), scene, d


class PresetReliabilityTests(ReliabilityBase):
    def test_every_style_preset_with_every_color_preset_decodes(self):
        failures = []
        for sname, style in STYLE_PRESETS.items():
            for cname, colors in COLOR_PRESETS.items():
                if not style or not colors:
                    continue
                for payload in PAYLOADS[:2]:
                    img, _, _ = self.render(payload, Design(**style, **colors, error_correction="Q", target_px=1024))
                    if read(img) != payload:
                        failures.append((sname, cname, payload[:20]))
        self.assertEqual(failures, [], "styled codes that did not decode")

    def test_rounded_marker_radius_is_inside_the_verified_range(self):
        # Evidence for geometry.EYE_ROUND_RADIUS: decoded 48/48 up to 0.7 and failed from 0.8; the shipped value must keep decoding.
        ok = total = 0
        for payload in PAYLOADS:
            for level in "MQH":
                for px in (512, 1024):
                    img, _, _ = self.render(payload, Design(pattern="rounded", eye_outer="rounded", eye_inner="rounded",
                                                            error_correction=level, target_px=px))
                    total += 1
                    ok += read(img) == payload
        self.assertEqual((ok, total), (total, total))

    def test_dots_and_diamonds_decode_with_square_markers(self):
        for pattern in ("dots", "diamond", "rounded"):
            for payload in PAYLOADS:
                img, _, _ = self.render(payload, Design(pattern=pattern, error_correction="Q"))
                self.assertEqual(read(img), payload, (pattern, payload[:20]))

    def test_circular_outer_ring_is_never_presented_as_verified(self):
        d = Design(eye_outer="circle")
        self.assertIn("unverified", " ".join(scan_warnings(d.validate(), 29)))
        result = ex.verify(PAYLOADS[0], d)
        self.assertTrue(result.structure_ok)                      # the data pattern itself is intact
        self.assertIn(result.status, ("unreadable", "ok"))        # honest either way; never 'mismatch'
        if result.status == "unreadable":
            self.assertIn("could not read", result.message)
            self.assertIn("test-scan", result.message)
        for preset in STYLE_PRESETS.values():
            if preset:
                self.assertNotEqual(preset["eye_outer"], "circle")


class ContentTypeReliabilityTests(ReliabilityBase):
    def test_every_content_type_decodes_back_to_its_payload(self):
        for type_id, values in SAMPLES.items():
            payload, _ = pl.build(type_id, values)
            result = ex.verify(payload, Design(error_correction="M"))
            self.assertEqual(result.status, "ok", f"{type_id}: {result.message}")
            self.assertTrue(result.structure_ok, type_id)

    def test_styled_vcard_and_calendar_still_decode(self):
        for type_id in ("vcard", "calendar", "wifi"):
            payload, _ = pl.build(type_id, SAMPLES[type_id])
            for style in ("Rounded", "Circular"):
                self.assertEqual(ex.verify(payload, Design(**STYLE_PRESETS[style], error_correction="Q")).status, "ok",
                                 (type_id, style))


class FrameLogoColorReliabilityTests(ReliabilityBase):
    def test_all_frame_styles_decode(self):
        for frame in ("border", "rounded", "badge", "tag", "bubble"):
            for payload in PAYLOADS[:3]:
                img, _, _ = self.render(payload, Design(frame=frame, cta_text="Scan Me", cta_color="#FFFFFF" if frame in ("badge", "tag", "bubble") else "#0B1628",
                                                        frame_color="#0B1628", error_correction="Q"))
                self.assertEqual(read(img), payload, (frame, payload[:20]))

    def test_frame_with_every_padding_and_text_size_decodes(self):
        for pad in (1, 3, 6):
            for size in ("small", "medium", "large"):
                img, _, _ = self.render(PAYLOADS[0], Design(frame="badge", cta_text="Visit Website", cta_size=size, frame_padding=pad))
                self.assertEqual(read(img), PAYLOADS[0], (pad, size))

    def test_logos_up_to_fifteen_percent_decode_at_levels_q_and_h(self):
        for level in ("Q", "H"):
            for pct in (0.08, 0.12, 0.15):
                for payload in PAYLOADS[:2]:
                    img, scene, _ = self.render(payload, Design(logo_bytes=png(), logo_fraction=pct, error_correction=level, pattern="rounded"))
                    self.assertEqual(read(img), payload, (level, pct, payload[:20]))
                    self.assertIsNotNone(scene.logo)

    def test_logo_covering_the_markers_is_refused_not_rendered(self):
        with self.assertRaises(gen.QRError):
            self.render("hello", Design(logo_bytes=png(), error_correction="H", logo_margin=1))   # version 1 code

    def test_transparent_codes_decode_on_a_light_surface(self):
        img, _, d = self.render(PAYLOADS[0], Design(transparent=True, pattern="rounded"))
        self.assertEqual(img.getpixel((1, 1))[3], 0)
        self.assertEqual(read(img), PAYLOADS[0])

    def test_quiet_zone_of_four_or_more_decodes(self):
        for q in (4, 6, 10):
            img, _, _ = self.render(PAYLOADS[0], Design(quiet_zone=q))
            self.assertEqual(read(img), PAYLOADS[0], q)

    def test_every_offered_raster_export_decodes_with_the_projects_own_decoder(self):
        for fmt in ("png", "jpg", "tiff"):
            for design in (Design(), Design(**STYLE_PRESETS["Rounded"], **COLOR_PRESETS["Cybersecurity blue"], target_px=768),
                           Design(frame="badge", cta_text="Scan Me", pattern="rounded", target_px=1024)):
                data = ex.export(PAYLOADS[0], design, fmt).data
                result = decode_image_bytes(data)
                self.assertTrue(result.found and result.text == PAYLOADS[0], (fmt, design.pattern, design.frame))


class StructureCheckTests(ReliabilityBase):
    def test_no_module_is_lost_by_any_styling(self):
        designs = [Design(**s, **c) for s in STYLE_PRESETS.values() if s for c in COLOR_PRESETS.values() if c]
        designs += [Design(frame=f, cta_text="Hi", cta_color="#FFFFFF") for f in ("border", "rounded", "badge", "tag", "bubble")]
        designs += [Design(logo_bytes=png(), error_correction="H"), Design(transparent=True), Design(eye_outer="circle", pattern="dots"),
                    Design(quiet_zone=1), Design(quiet_zone=10), Design(fill="radial", fg="#FF0000", fg2="#0000AA", bg="#FFFFFF")]
        for d in designs:
            img, scene, dd = self.render(PAYLOADS[0], d)
            bad, total = ex.structure_check(scene, img, dd)
            self.assertEqual(bad, 0, f"{dd.pattern}/{dd.fill}/{dd.frame}: {bad} of {total} modules differ")
            hole = scene.logo.hole[2] ** 2 if scene.logo else 0
            self.assertEqual(total, scene.n ** 2 - 3 * 49 - hole + 3 * 14, "the check must cover every data module")

    def test_damage_is_detected(self):
        img, scene, d = self.render(PAYLOADS[0], Design(target_px=768))
        damaged = img.copy()
        box = d.target_px // scene.width
        ox, oy = scene.origin
        ImageDraw.Draw(damaged).rectangle((box * (ox + 9), box * (oy + 9), box * (ox + 20), box * (oy + 12)), fill=(255, 255, 255, 255))
        bad, _ = ex.structure_check(scene, damaged, d)
        self.assertGreater(bad, 5)

    def test_a_picture_of_a_different_code_is_detected(self):
        img_a, scene_a, d = self.render("https://a.example/one", Design(target_px=768))
        _, scene_b, _ = self.render("https://b.example/two", Design(target_px=768))       # same length, same version
        self.assertEqual(scene_a.n, scene_b.n)
        self.assertEqual(ex.structure_check(scene_a, img_a, d)[0], 0)
        self.assertGreater(ex.structure_check(scene_b, img_a, d)[0], 20)                  # a different pattern cannot pass


class VerifyOutcomeTests(ReliabilityBase):
    def test_ok(self):
        r = ex.verify(PAYLOADS[0], Design())
        self.assertEqual(r.status, "ok")
        self.assertIn("not a guarantee", r.message)
        self.assertIn(r.decoder, ("OpenCV", "OpenCV-ArUco"))

    def test_a_different_decoded_text_is_a_mismatch_and_tells_the_user_not_to_use_it(self):
        with mock.patch.object(ex, "try_decode", return_value=("https://evil.example", "OpenCV")):
            r = ex.verify(PAYLOADS[0], Design())
        self.assertEqual(r.status, "mismatch")
        self.assertIn("DIFFERENT content", r.message)

    def test_unreadable_reports_structure_and_advises_a_test_scan(self):
        with mock.patch.object(ex, "try_decode", return_value=("", "")):
            r = ex.verify(PAYLOADS[0], Design(pattern="dots"))
        self.assertEqual(r.status, "unreadable")
        self.assertTrue(r.structure_ok)
        self.assertIn("test-scan", r.message)
        self.assertIn("intact", r.message)

    def test_unreadable_with_damage_names_the_modules(self):
        with mock.patch.object(ex, "try_decode", return_value=("", "")), mock.patch.object(ex, "structure_check", return_value=(7, 900)):
            r = ex.verify(PAYLOADS[0], Design())
        self.assertFalse(r.structure_ok)
        self.assertIn("7 of 900", r.message)

    def test_missing_decoder_is_reported_as_unavailable_not_as_a_pass(self):
        with mock.patch.object(ex, "_decoders", side_effect=ImportError):
            r = ex.verify(PAYLOADS[0], Design())
        self.assertEqual(r.status, "unavailable")
        self.assertNotIn("OK", r.message)

    def test_crlf_payloads_compare_correctly(self):
        payload, _ = pl.build("vcard", SAMPLES["vcard"])
        with mock.patch.object(ex, "try_decode", return_value=(payload.replace("\r\n", "\n"), "OpenCV")):
            self.assertEqual(ex.verify(payload, Design()).status, "ok")

    def test_inverted_transparent_codes_are_checked_on_a_dark_surface(self):
        calls = []
        real = ex.try_decode
        with mock.patch.object(ex, "try_decode", side_effect=lambda img, light_surface=True: (calls.append(light_surface), real(img, light_surface))[1]):
            ex.verify(PAYLOADS[0], Design(transparent=True, fg="#FFFFFF", bg="#000000"))
            ex.verify(PAYLOADS[0], Design(transparent=True))
        self.assertEqual(calls, [False, True])


if __name__ == "__main__":
    unittest.main()


try:
    import qrcode as _qrcode          # noqa: F401
    HAVE_QRCODE = True
except ImportError:
    HAVE_QRCODE = False


@unittest.skipUnless(HAVE_QRCODE, "the `qrcode` package (a project requirement) is not installed in this environment")
class RealQrcodeMatrixTests(unittest.TestCase):
    """The production path: qr_tools.generator.make_matrix (the `qrcode` package) feeding the new pipeline, unpatched.

    These are skipped where `qrcode` is missing (including the environment this feature was developed in), so a green
    run elsewhere is the first real evidence that the new renderers work with qrcode's own matrices.
    """

    def setUp(self):
        ex.clear_cache()
        self.addCleanup(ex.clear_cache)

    def test_real_matrices_pass_the_marker_check_and_render_and_decode_for_every_preset(self):
        from qr_tools.scene import verify_finders
        for level in "MQH":
            for payload in PAYLOADS[:3]:
                verify_finders([list(r) for r in gen.make_matrix(payload, level)])
        failures = []
        for sname, style in STYLE_PRESETS.items():
            for cname, colors in COLOR_PRESETS.items():
                if not style or not colors:
                    continue
                d = Design(**style, **colors, error_correction="Q", target_px=1024)
                if ex.verify(PAYLOADS[0], d).status != "ok":
                    failures.append((sname, cname))
        self.assertEqual(failures, [])

    def test_every_format_exports_and_every_content_type_verifies_with_real_matrices(self):
        for fmt in ex.FORMATS:
            self.assertTrue(ex.export(PAYLOADS[0], Design(pattern="rounded"), fmt).data)
        for type_id, values in SAMPLES.items():
            payload, _ = pl.build(type_id, values)
            result = ex.verify(payload, Design())
            self.assertEqual(result.status, "ok", f"{type_id}: {result.message}")
