"""Seeded sweep over the whole option space: every combination must either work correctly or fail with a clean QRError."""

import io
import random
import unittest
from dataclasses import replace
from unittest import mock

from PIL import Image

from qr_tools import exporter as ex
from qr_tools import generator as gen
from qr_tools import geometry as geo
from qr_tools.design import FILLS, FRAMES, SIZES, Design
from qr_tools.generator import QRError, contrast_ratio
from qr_tools.render_raster import render_raster
from qr_tools.scene import build_scene
from tests.qr_matrix import cv2_matrix
from tests.test_qr_render import png

MAGIC = {"png": b"\x89PNG", "jpg": b"\xff\xd8", "svg": b"<?xml", "pdf": b"%PDF-"}
COLORS = ["#000000", "#FFFFFF", "#0B1628", "#14B8A6", "#FF0000", "#CCCCCC", "#6D28D9", "#0F766E"]
PAYLOADS = ["https://example.com", "hello", "WIFI:T:WPA;S:Home;P:secret123;;", "x" * 150, "https://example.com/a?b=1&c=2" * 4]


class RobustnessTests(unittest.TestCase):
    def setUp(self):
        ex.clear_cache()
        patcher = mock.patch.object(gen, "make_matrix", side_effect=lambda d, ec="M": cv2_matrix(gen.build_text_payload(d), ec))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(ex.clear_cache)

    @staticmethod
    def random_design(rng):
        frame = rng.choice(FRAMES)
        return Design(
            pattern=rng.choice(geo.PATTERNS), eye_outer=rng.choice(geo.EYE_OUTER), eye_inner=rng.choice(geo.EYE_INNER),
            eye_outer_color=rng.choice([None] + COLORS), eye_inner_color=rng.choice([None] + COLORS),
            fg=rng.choice(COLORS), fg2=rng.choice(COLORS), fill=rng.choice(FILLS), bg=rng.choice(COLORS),
            transparent=rng.random() < 0.3, error_correction=rng.choice("LMQH"), quiet_zone=rng.randint(1, 10),
            target_px=rng.choice(SIZES[:3]), logo_bytes=png() if rng.random() < 0.4 else None,
            logo_fraction=rng.choice([0.05, 0.12, 0.18, 0.22]), logo_margin=rng.randint(0, 3), frame=frame,
            cta_text=rng.choice(["", "Scan Me", "Visit Website", "A fairly long label to force shrinking"[:30], "W" * 30]),
            cta_color=rng.choice(COLORS), cta_size=rng.choice(["small", "medium", "large"]), cta_bold=rng.random() < 0.5,
            frame_color=rng.choice(COLORS), frame_padding=rng.randint(1, 6))

    def test_random_combinations_work_or_fail_cleanly_and_never_lose_modules(self):
        rng = random.Random(20261025)
        worked = refused = flagged = 0
        reasons = set()
        for i in range(70):
            design, payload, fmt = self.random_design(rng), rng.choice(PAYLOADS), rng.choice(list(MAGIC))
            try:
                result = ex.export(payload, design, fmt)
            except QRError as exc:                                      # a clean, user-readable refusal is acceptable
                refused += 1
                reasons.add(str(exc)[:40])
                self.assertTrue(str(exc).strip(), "refusals must explain themselves")
                continue
            worked += 1
            self.assertTrue(result.data.startswith(MAGIC[fmt]), (i, fmt))
            self.assertGreater(len(result.data), 200)
            if fmt in ("png", "jpg"):
                self.assertEqual(Image.open(io.BytesIO(result.data)).size, (result.width_px, result.height_px))
            scene, d, matrix = ex.prepare(payload, design)
            probe = replace(d, target_px=min(d.target_px, 1024))
            bad, total = ex.structure_check(scene, render_raster(scene, probe.target_px), probe)
            surface = "#FFFFFF" if d.transparent else d.bg
            colors = d.module_colors() + list(d.eye_colors())
            adequate = all(contrast_ratio(c, surface) >= 3 for c in colors)
            if adequate:
                self.assertEqual(bad, 0, f"combination {i} lost {bad}/{total} modules: {d}")
            elif bad:
                # A picture that lost modules must already have been flagged to the user as low contrast.
                self.assertTrue(any("contrast" in w.lower() for w in ex.warnings_for(payload, design)),
                                f"combination {i}: {bad} modules unreadable but no contrast warning: {d}")
                flagged += 1
        self.assertGreater(worked, 25)                                  # the sweep really exercised working designs
        self.assertGreaterEqual(flagged, 1)                             # and met low-contrast designs, which were warned about
        self.assertGreater(refused, 3)                                  # and really hit refusals (logo too big, label too long...)

    def test_invalid_settings_are_refused_for_every_format(self):
        bad_designs = [Design(fg="nope"), Design(quiet_zone=0), Design(target_px=999), Design(cta_text="é"), Design(pattern="star"),
                       Design(logo_bytes=b"junk"), Design(logo_fraction=0.9), Design(frame="x"), Design(error_correction="Z")]
        for design in bad_designs:
            for fmt in list(MAGIC) + ["tiff"]:
                with self.assertRaises(QRError, msg=f"{design} / {fmt}"):
                    ex.export("https://example.com", design, fmt)

    def test_oversized_content_is_refused_not_truncated(self):
        for fmt in MAGIC:
            with self.assertRaises(QRError):
                ex.export("x" * 5000, Design(), fmt)

    def test_a_refused_design_never_leaves_stale_output_in_the_cache(self):
        good = ex.export("https://example.com", Design(), "png").data
        with self.assertRaises(QRError):
            ex.export("https://example.com", Design(fg="bad"), "png")
        self.assertEqual(ex.export("https://example.com", Design(), "png").data, good)

    def test_every_format_survives_the_extremes(self):
        extremes = [Design(quiet_zone=10, target_px=512, frame="bubble", cta_text="W" * 30, cta_size="large", frame_padding=6),
                    Design(quiet_zone=1, target_px=512, pattern="diamond", fill="radial", fg="#CCCCCC"),
                    Design(target_px=4096, transparent=True, fill="diagonal", fg="#6D28D9", fg2="#0F766E")]
        for design in extremes:
            for fmt in ("svg", "pdf") + (("png",) if design.target_px < 4096 else ()):
                try:
                    out = ex.export("https://example.com/extremes", design, fmt)
                except QRError:
                    continue
                self.assertTrue(out.data.startswith(MAGIC[fmt]))


if __name__ == "__main__":
    unittest.main()
