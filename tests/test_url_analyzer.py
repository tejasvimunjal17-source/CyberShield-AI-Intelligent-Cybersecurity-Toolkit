import unittest


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


from backend.url_analyzer import analyze_url, defang, virustotal_url_id


def codes(a):
    return {f.code for f in a.findings}


class UrlAnalyzerTests(unittest.TestCase):
    def test_plain_https_has_no_strong_signals(self):
        a = analyze_url("https://example.com/")
        self.assertTrue(a.valid)
        self.assertEqual(a.hostname, "example.com")
        self.assertEqual(a.signal_level, "No strong heuristic signals")

    def test_empty_and_invalid(self):
        for bad in ["", "   ", "http://", "javascript:alert(1)", "ftp://x.com", "http://exa mple.com"]:
            a = analyze_url(bad)
            self.assertFalse(a.valid, bad)
            self.assertTrue(a.error)

    def test_too_long(self):
        self.assertFalse(analyze_url("http://a.com/" + "x" * 3000).valid)

    def test_bad_port(self):
        self.assertFalse(analyze_url("http://example.com:99999/").valid)

    def test_missing_scheme_assumed_http(self):
        a = analyze_url("example.com/login")
        self.assertTrue(a.valid)
        self.assertIn("no_scheme", codes(a))
        self.assertIn("http", codes(a))

    def test_ip_host(self):
        a = analyze_url("http://192.168.1.10/admin")
        self.assertIn("ip_host", codes(a))
        self.assertIn("private_ip", codes(a))

    def test_punycode(self):
        self.assertIn("punycode", codes(analyze_url("https://xn--pple-43d.com")))

    def test_userinfo_at_sign(self):
        a = analyze_url("https://paypal.com@evil.example.net/x")
        self.assertIn("userinfo", codes(a))
        self.assertEqual(a.hostname, "evil.example.net")

    def test_shortener(self):
        self.assertIn("shortener", codes(analyze_url("https://bit.ly/abc")))

    def test_brand_lookalike(self):
        self.assertIn("brand_lookalike", codes(analyze_url("https://paypal-secure-login.example.com")))
        self.assertIn("brand_lookalike", codes(analyze_url("https://paypal.example.com")))

    def test_real_brand_domain_not_flagged_as_lookalike(self):
        self.assertNotIn("brand_lookalike", codes(analyze_url("https://www.paypal.com/signin")))

    def test_two_part_suffix(self):
        a = analyze_url("https://login.evil.co.uk/")
        self.assertEqual(a.registered_domain, "evil.co.uk")

    def test_embedded_url_and_port(self):
        a = analyze_url("https://example.com:8443/r?next=https://other.example/")
        self.assertIn("embedded_url", codes(a))
        self.assertIn("odd_port", codes(a))

    def test_many_signals_level_and_wording(self):
        a = analyze_url("http://paypal.com@xn--pple-43d.top:8080/login")
        self.assertEqual(a.signal_level, "Many suspicious signals")
        for word in ("safe", "malicious"):
            self.assertNotIn(word, a.signal_level.lower())

    def test_defang(self):
        self.assertEqual(defang("http://a.com/x"), "hxxp://a[.]com/x")

    def test_vt_url_id_is_urlsafe_base64_without_padding(self):
        self.assertEqual(virustotal_url_id("http://www.google.com/"), "aHR0cDovL3d3dy5nb29nbGUuY29tLw")
        self.assertNotIn("=", virustotal_url_id("http://a.com/?q=1"))

    def test_no_network_imports(self):
        import backend.url_analyzer as m
        src = _read(m.__file__)
        for banned in ("import requests", "urllib.request", "socket"):
            self.assertNotIn(banned, src)


if __name__ == "__main__":
    unittest.main()
