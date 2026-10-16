import io
import unittest

from PIL import Image

from qr_tools import generator as gen

try:
    import qrcode  # noqa: F401
    HAVE_QRCODE = True
except ImportError:
    HAVE_QRCODE = False

# A synthetic 21x21 matrix (finder-pattern-like) for tests that must not
# depend on the qrcode package.
def synthetic_matrix(n=21):
    return [[(x + y) % 2 == 0 or x < 7 and y < 7 for x in range(n)] for y in range(n)]


class PayloadTests(unittest.TestCase):
    def test_url_validation(self):
        self.assertEqual(gen.build_url_payload(" https://a.com "), "https://a.com")
        for bad in ["a.com", "javascript:alert(1)", "ftp://a.com", "", "https://"]:
            with self.assertRaises(gen.QRError, msg=bad):
                gen.build_url_payload(bad)

    def test_text_limits(self):
        with self.assertRaises(gen.QRError):
            gen.build_text_payload("   ")
        with self.assertRaises(gen.QRError):
            gen.build_text_payload("x" * 5000)
        self.assertEqual(gen.build_text_payload("héllo 你好"), "héllo 你好")

    def test_wifi(self):
        self.assertEqual(gen.build_wifi_payload("Home", "pw", "WPA"), "WIFI:T:WPA;S:Home;P:pw;;")
        self.assertEqual(gen.build_wifi_payload("Open", "", "nopass"), "WIFI:T:nopass;S:Open;;")
        self.assertIn(r"S:a\;b", gen.build_wifi_payload("a;b", "x", "WPA"))
        self.assertTrue(gen.build_wifi_payload("H", "p", "WPA", hidden=True).endswith("H:true;;"))
        with self.assertRaises(gen.QRError):
            gen.build_wifi_payload("", "x")
        with self.assertRaises(gen.QRError):
            gen.build_wifi_payload("x", "")

    def test_email(self):
        self.assertEqual(gen.build_email_payload("a@b.co"), "mailto:a@b.co")
        self.assertIn("subject=Hi%20there", gen.build_email_payload("a@b.co", "Hi there"))
        with self.assertRaises(gen.QRError):
            gen.build_email_payload("not-an-email")


class StyleTests(unittest.TestCase):
    def test_contrast(self):
        self.assertAlmostEqual(gen.contrast_ratio("#000000", "#FFFFFF"), 21.0, places=1)
        self.assertLess(gen.contrast_ratio("#777777", "#888888"), 2)

    def test_bad_color(self):
        with self.assertRaises(gen.QRError):
            gen.contrast_ratio("red", "#FFFFFF")

    def test_warnings(self):
        w = gen.style_warnings(gen.QRStyle(foreground="#777777", background="#888888"))
        self.assertTrue(any("contrast" in x.lower() for x in w))
        w = gen.style_warnings(gen.QRStyle(foreground="#FFFFFF", background="#000000"))
        self.assertTrue(any("inverted" in x.lower() for x in w))
        self.assertEqual(gen.style_warnings(gen.QRStyle()), [])


class RenderTests(unittest.TestCase):
    def test_colors_and_size(self):
        style = gen.QRStyle(foreground="#0B1628", background="#FFFFFF", target_px=420, border_modules=4)
        img = gen.render_image(synthetic_matrix(), style)
        self.assertEqual(img.size[0], img.size[1])
        self.assertLessEqual(img.size[0], 420)
        self.assertEqual(img.getpixel((0, 0)), (255, 255, 255))   # quiet zone = background
        box = img.size[0] // (21 + 8)
        self.assertEqual(img.getpixel((4 * box + 1, 4 * box + 1)), (11, 22, 40))  # first module dark

    def test_png_jpg_bytes_are_valid_images(self):
        img = gen.render_image(synthetic_matrix(), gen.QRStyle())
        self.assertEqual(Image.open(io.BytesIO(gen.to_png_bytes(img))).format, "PNG")
        self.assertEqual(Image.open(io.BytesIO(gen.to_jpg_bytes(img))).format, "JPEG")

    def test_svg(self):
        svg = gen.to_svg_bytes(synthetic_matrix(), gen.QRStyle(foreground="#0F766E")).decode()
        self.assertTrue(svg.startswith("<svg"))
        self.assertIn('fill="#0F766E"', svg)
        self.assertIn('viewBox="0 0 29 29"', svg)

    def test_svg_refuses_logo(self):
        with self.assertRaises(gen.QRError):
            gen.to_svg_bytes(synthetic_matrix(), gen.QRStyle(logo_bytes=b"x"))

    def test_logo_forces_level_h_and_is_placed(self):
        buf = io.BytesIO()
        Image.new("RGB", (100, 100), (255, 0, 0)).save(buf, format="PNG")
        style = gen.QRStyle(error_correction="L", logo_bytes=buf.getvalue(), target_px=580)
        self.assertEqual(gen.effective_error_correction(style), "H")
        img = gen.render_image(synthetic_matrix(), style)
        centre = img.getpixel((img.width // 2, img.height // 2))
        self.assertEqual(centre, (255, 0, 0))

    def test_bad_logo(self):
        with self.assertRaises(gen.QRError):
            gen.render_image(synthetic_matrix(), gen.QRStyle(logo_bytes=b"not an image"))

    def test_output_size_is_capped(self):
        img = gen.render_image(synthetic_matrix(), gen.QRStyle(target_px=999999))
        self.assertLessEqual(img.size[0], gen.MAX_OUTPUT_PX)


@unittest.skipUnless(HAVE_QRCODE, "qrcode package not installed in this environment")
class RoundTripTests(unittest.TestCase):
    """Generate with our code, decode with OpenCV."""

    def _roundtrip(self, text, **style_kwargs):
        from qr_tools.decoder import decode_image_bytes
        style = gen.QRStyle(**style_kwargs)
        matrix = gen.make_matrix(text, gen.effective_error_correction(style))
        png = gen.to_png_bytes(gen.render_image(matrix, style))
        return decode_image_bytes(png).text

    def test_url(self):
        self.assertEqual(self._roundtrip("https://example.com/a?b=c"), "https://example.com/a?b=c")

    def test_custom_colors(self):
        self.assertEqual(self._roundtrip("hello", foreground="#0B1628", background="#E6EEF8"), "hello")

    def test_unicode(self):
        self.assertEqual(self._roundtrip("héllo 你好 ✓"), "héllo 你好 ✓")


if __name__ == "__main__":
    unittest.main()
