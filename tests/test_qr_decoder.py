import io
import unittest

from qr_tools.decoder import DecodeError, classify_payload, decode_image_bytes

try:
    import cv2
    import numpy as np
    from PIL import Image
    HAVE_ENCODER = hasattr(cv2, "QRCodeEncoder")
except ImportError:  # pragma: no cover
    HAVE_ENCODER = False


def make_qr_png(text: str, scale: int = 8) -> bytes:
    """Independent fixture: OpenCV's encoder, not our generator."""
    raw = cv2.QRCodeEncoder.create().encode(text)
    raw = cv2.copyMakeBorder(raw, 4, 4, 4, 4, cv2.BORDER_CONSTANT, value=255)
    raw = cv2.resize(raw, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
    buf = io.BytesIO()
    Image.fromarray(raw).save(buf, format="PNG")
    return buf.getvalue()


class ClassifyTests(unittest.TestCase):
    def test_kinds(self):
        self.assertEqual(classify_payload("https://a.com"), "url")
        self.assertEqual(classify_payload("WIFI:T:WPA;S:x;P:y;;"), "wifi")
        self.assertEqual(classify_payload("mailto:a@b.co"), "email")
        self.assertEqual(classify_payload("tel:+123"), "phone")
        self.assertEqual(classify_payload("SMSTO:1:hi"), "sms")
        self.assertEqual(classify_payload("hello"), "text")


@unittest.skipUnless(HAVE_ENCODER, "OpenCV QRCodeEncoder not available")
class DecodeTests(unittest.TestCase):
    def test_decodes_url(self):
        r = decode_image_bytes(make_qr_png("https://example.com/path?q=1"))
        self.assertTrue(r.found)
        self.assertEqual(r.text, "https://example.com/path?q=1")
        self.assertEqual(r.kind, "url")

    def test_decodes_ascii_text(self):
        r = decode_image_bytes(make_qr_png("Hello CyberShield"))
        self.assertEqual(r.text, "Hello CyberShield")
        self.assertEqual(r.kind, "text")

    def test_blank_image_not_found(self):
        buf = io.BytesIO()
        Image.new("RGB", (200, 200), "white").save(buf, format="PNG")
        r = decode_image_bytes(buf.getvalue())
        self.assertFalse(r.found)

    def test_not_an_image(self):
        with self.assertRaises(DecodeError):
            decode_image_bytes(b"this is not an image")


if __name__ == "__main__":
    unittest.main()
