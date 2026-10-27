"""The README and CyberGuide's knowledge.md must describe the QR generator exactly as the code behaves."""

import re
import struct
import unittest

from qr_tools import exporter as ex
from qr_tools import geometry as geo
from qr_tools import payloads as pl
from qr_tools.design import (COLOR_PRESETS, EC_CAPACITY, MAX_LOGO_FRACTION, MIN_LOGO_FRACTION, SIZES, STYLE_PRESETS, Design)


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


README, KNOW = read("README.md"), read("knowledge.md")


class ReadmeMatchesCodeTests(unittest.TestCase):
    def test_example_image_is_real_and_linked_with_a_relative_path(self):
        links = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", README)
        self.assertEqual(links, ["docs/images/qr-generator-examples.png"])
        data = open(links[0], "rb").read()
        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
        w, h = struct.unpack(">II", data[16:24])
        self.assertGreater(w, 600)
        self.assertGreater(h, 400)
        self.assertIn("not screenshots of the app", README)

    def test_every_offered_format_is_documented_and_eps_is_only_ever_called_not_offered(self):
        for fmt in ex.FORMATS.values():
            self.assertIn(fmt.label, README)
            self.assertIn(fmt.label, KNOW)
        for text in (README, KNOW):
            for m in re.finditer(r"\bEPS\b", text):
                around = text[max(0, m.start() - 140):m.end() + 140].lower()
                self.assertTrue("not offered" in around or "not implement" in around or "deliberately" in around, around)
        self.assertIn("eps", ex.NOT_OFFERED)

    def test_content_type_count_categories_and_names(self):
        self.assertEqual(len(pl.CONTENT_TYPES), 17)
        mentions = re.findall(r"(\d+) content types", README)
        self.assertTrue(mentions)
        self.assertEqual(set(mentions), {"17"})                                    # every mention agrees with the code
        for category in pl.CATEGORIES:
            self.assertIn(category.split(" &")[0], README)
        for word in ("Wi-Fi", "WhatsApp", "vCard", "Instagram", "Facebook", "YouTube", "LinkedIn", "Google Drive", "Calendar", "SMS"):
            self.assertIn(word, README)
            self.assertIn(word, KNOW)

    def test_documented_numbers_match_the_code(self):
        self.assertEqual(SIZES, (512, 768, 1024, 2048, 4096))
        for px in SIZES:
            self.assertIn(str(px), README)
        self.assertIn("quiet zone 1 to 10 modules (default 4)", README)
        self.assertEqual(Design().quiet_zone, 4)
        self.assertIn(f"size {MIN_LOGO_FRACTION:.0%} to {MAX_LOGO_FRACTION:.0%} of the width", README)
        self.assertAlmostEqual(Design().logo_fraction, 0.12)
        self.assertIn("default 12%", README)
        self.assertIn("clear space 0 to 3 modules", README)
        self.assertIn(f"up to {geo.CTA_MAX_CHARS} characters", README)
        for level, share in EC_CAPACITY.items():
            self.assertIn(f"{share:.0%}".rstrip("%"), README)
        self.assertLessEqual(geo.EYE_ROUND_RADIUS, 0.7)
        caps = re.findall(r"capped at ([\d.]+)", README)
        self.assertTrue(caps)
        self.assertEqual(set(caps), {str(geo.EYE_ROUND_RADIUS)})                   # every mention must match the code

    def test_every_preset_is_documented(self):
        for name, preset in COLOR_PRESETS.items():
            if preset is not None:
                self.assertIn(name, README)
        for name, preset in STYLE_PRESETS.items():
            if preset is not None:
                self.assertIn(name, README)

    def test_no_unsupported_claims(self):
        low = README.lower()
        for claim in ("eps export is supported", "background image support", "uploads your logo", "sends your qr", "guaranteed to scan",
                      "guarantees a scan", "100% scannable", "license: ", "badge.svg", "shields.io"):
            self.assertNotIn(claim, low)
        self.assertIn("test-scan", low)
        reliability = README[README.index("### Reliability"):README.index("## Security and privacy")].lower()
        self.assertIn("not a guarantee", reliability)                              # the caveat must sit where the check is explained
        self.assertIn("evidence from one decoder", reliability)

    def test_limitations_section_covers_the_known_qr_limits(self):
        section = README[README.index("## Known limitations"):]
        for needle in ("qrcode", "ASCII", "Chromium", "PDF", "bitmap"):
            self.assertIn(needle, section)

    def test_knowledge_base_describes_the_same_limits(self):
        body = KNOW[KNOW.index("## QR code limitations"):KNOW.index("Page: qr_generator", KNOW.index("## QR code limitations"))]
        for needle in ("PNG or JPG up to 1 MB", "30 characters", "EPS is not offered", "background images are not offered",
                       "embedded bitmap", "not a guarantee"):
            self.assertIn(needle, body)                                            # in the limitations section itself


if __name__ == "__main__":
    unittest.main()
