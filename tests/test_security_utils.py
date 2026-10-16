import unittest

from backend.security_utils import clip_text, redact_secrets


class SecurityUtilsTests(unittest.TestCase):
    def test_redacts_openrouter_style_key(self):
        out = redact_secrets("my key is sk-or-v1-abcdefghijklmnop1234 help")
        self.assertNotIn("abcdefghijklmnop", out)
        self.assertIn("[redacted]", out)

    def test_redacts_assignment(self):
        self.assertNotIn("hunter2", redact_secrets("api_key = hunter2"))

    def test_plain_text_untouched(self):
        self.assertEqual(redact_secrets("How do I make a QR code?"), "How do I make a QR code?")

    def test_clip(self):
        self.assertEqual(clip_text("  abcdef  ", 3), "abc")
        self.assertEqual(clip_text(None, 5), "")


if __name__ == "__main__":
    unittest.main()
