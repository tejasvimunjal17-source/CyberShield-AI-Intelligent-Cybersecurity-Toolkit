"""Content types for the QR generator: validation, escaping and payload shape. No network, no qrcode package needed."""

import unittest
from datetime import date, time
from unittest import mock

from qr_tools import payloads as pl
from qr_tools.generator import MAX_QR_TEXT_CHARS, QRError

SAMPLES = {
    "url": {"url": "https://example.com/a?b=1&c=2"},
    "text": {"text": "Hello\nWorld é"},
    "email": {"address": "a@b.co", "subject": "Hi / there", "body": "a&b=c"},
    "phone": {"phone": "+44 (20) 7946-0958"},
    "sms": {"phone": "+15550100", "message": "Hi: there"},
    "wifi": {"ssid": "Home;Net", "password": "p:w,d", "security": "WPA", "hidden": True},
    "whatsapp": {"phone": "+44 7700 900123", "message": "Hello & welcome"},
    "vcard": {"first": "Ada", "last": "Lovelace, Jr", "org": "A;B", "phone": "+1 555 0100", "email": "a@b.co",
              "website": "https://x.org", "note": "l1\nl2"},
    "instagram": {"handle": "@user.name"},
    "facebook": {"handle": "https://www.facebook.com/somepage"},
    "youtube": {"handle": "@chan_1"},
    "linkedin": {"handle": "jane-doe"},
    "social_other": {"url": "https://example.com/me"},
    "business": {"org": "Acme, Inc", "phone": "+1 555 0100", "website": "https://acme.test"},
    "file_link": {"kind": "PDF document", "url": "https://example.com/menu.pdf"},
    "drive": {"url": "https://drive.google.com/file/d/abc123/view?usp=sharing"},
    "calendar": {"title": "Launch; party", "location": "HQ, Floor 2", "start_date": date(2026, 11, 2), "start_time": time(9, 0),
                 "end_date": date(2026, 11, 2), "end_time": time(10, 30), "description": "Bring\nsnacks"},
}


class RegistryTests(unittest.TestCase):
    def test_every_registered_type_has_a_sample_and_builds(self):
        self.assertEqual(set(SAMPLES), set(pl.TYPES_BY_ID))
        for type_id, values in SAMPLES.items():
            payload, notes = pl.build(type_id, values)
            self.assertTrue(payload and len(payload) <= MAX_QR_TEXT_CHARS, type_id)
            self.assertIsInstance(notes, list)

    def test_requested_types_exist_and_original_labels_are_kept(self):
        labels = {t.label for t in pl.CONTENT_TYPES}
        for original in ("URL", "Text", "Wi-Fi", "Email"):
            self.assertIn(original, labels)
        self.assertEqual(set(pl.CATEGORIES), {t.category for t in pl.CONTENT_TYPES})

    def test_building_never_touches_the_network(self):
        with mock.patch("socket.socket", side_effect=AssertionError("network used")), \
                mock.patch("socket.getaddrinfo", side_effect=AssertionError("dns used")):
            for type_id, values in SAMPLES.items():
                pl.build(type_id, values)

    def test_unknown_type_and_empty_values(self):
        with self.assertRaises(QRError):
            pl.build("nope", {})
        for type_id in pl.TYPES_BY_ID:
            with self.assertRaises(QRError, msg=type_id):
                pl.build(type_id, {})


class BasicAndCommunicationTests(unittest.TestCase):
    def test_url_text_email(self):
        self.assertEqual(pl.build("url", SAMPLES["url"])[0], "https://example.com/a?b=1&c=2")
        self.assertEqual(pl.build("text", SAMPLES["text"])[0], "Hello\nWorld é")
        email = pl.build("email", SAMPLES["email"])[0]
        self.assertEqual(email, "mailto:a@b.co?subject=Hi%20%2F%20there&body=a%26b%3Dc")
        self.assertEqual(pl.build("email", {"address": "a@b.co"})[0], "mailto:a@b.co")

    def test_url_rejects_unsafe_schemes_and_credentials(self):
        for bad in ("javascript:alert(1)", "data:text/html,x", "ftp://x.com", "https://u:p@x.com", "example.com", "https://"):
            with self.assertRaises(QRError, msg=bad):
                pl.build("url", {"url": bad})
        self.assertTrue(any("not encrypted" in n for n in pl.build("url", {"url": "http://example.com"})[1]))

    def test_text_rejects_control_characters_but_keeps_newlines(self):
        with self.assertRaises(QRError):
            pl.build("text", {"text": "a\x00b"})
        self.assertIn("\n", pl.build("text", {"text": "a\nb"})[0])

    def test_phone_and_sms(self):
        self.assertEqual(pl.build("phone", SAMPLES["phone"])[0], "tel:+442079460958")
        self.assertEqual(pl.build("sms", SAMPLES["sms"])[0], "SMSTO:+15550100:Hi: there")
        self.assertEqual(pl.build("sms", {"phone": "5550100"})[0], "SMSTO:5550100")
        for bad in ("abc", "12", "+1" + "2" * 20, "555-0100 ext 5", ""):
            with self.assertRaises(QRError, msg=bad):
                pl.build("phone", {"phone": bad})

    def test_wifi_escapes_special_characters(self):
        payload = pl.build("wifi", SAMPLES["wifi"])[0]
        self.assertTrue(payload.startswith("WIFI:T:WPA;"))
        self.assertIn(r"S:Home\;Net", payload)
        self.assertIn(r"P:p\:w\,d", payload)
        self.assertIn("H:true", payload)
        self.assertIn("T:nopass", pl.build("wifi", {"ssid": "Cafe", "security": "No password"})[0])

    def test_whatsapp(self):
        self.assertEqual(pl.build("whatsapp", SAMPLES["whatsapp"])[0],
                         "https://wa.me/447700900123?text=Hello%20%26%20welcome")
        self.assertEqual(pl.build("whatsapp", {"phone": "+447700900123"})[0], "https://wa.me/447700900123")
        with self.assertRaises(QRError):
            pl.build("whatsapp", {"phone": "123"})
        self.assertTrue(pl.build("whatsapp", {"phone": "07700 900123"})[1])   # missing + gives advice


class VCardTests(unittest.TestCase):
    def test_contact_card_structure_and_escaping(self):
        card = pl.build("vcard", SAMPLES["vcard"])[0].split("\r\n")
        self.assertEqual(card[0], "BEGIN:VCARD")
        self.assertEqual(card[1], "VERSION:3.0")
        self.assertEqual(card[-1], "END:VCARD")
        self.assertIn(r"N:Lovelace\, Jr;Ada;;;", card)
        self.assertIn("FN:Ada Lovelace\\, Jr", card)
        self.assertIn(r"ORG:A\;B", card)
        self.assertIn("TEL;TYPE=WORK,VOICE:+15550100", card)
        self.assertIn("NOTE:l1\\nl2", card)

    def test_injection_attempts_cannot_add_fields(self):
        for field in ("first", "org", "title", "city"):
            with self.assertRaises(QRError, msg=field):
                pl.build("vcard", {"first": "Ada", field: "x\r\nTEL:+1999"})
        card = pl.build("vcard", {"first": "Ada", "note": "x\nTEL:+1999"})[0].split("\r\n")
        self.assertEqual([ln for ln in card if ln.startswith("TEL")], [])            # no injected phone line
        self.assertIn("NOTE:x\\nTEL:+1999", card)                                     # the text stays inside the NOTE value

    def test_business_requires_company_and_contact_requires_a_name(self):
        with self.assertRaises(QRError):
            pl.build("business", {"first": "Sam"})
        with self.assertRaises(QRError):
            pl.build("vcard", {"org": "Only Co"})
        card = pl.build("business", {"org": "Acme"})[0]
        self.assertIn("FN:Acme", card)
        self.assertIn("ORG:Acme", card)

    def test_bad_email_phone_website_rejected(self):
        for field, bad in (("email", "nope"), ("phone", "abc"), ("website", "javascript:x")):
            with self.assertRaises(QRError, msg=field):
                pl.build("vcard", {"first": "A", field: bad})


class SocialTests(unittest.TestCase):
    def test_handles_become_profile_links(self):
        self.assertEqual(pl.build("instagram", {"handle": "@user.name"})[0], "https://www.instagram.com/user.name/")
        self.assertEqual(pl.build("facebook", {"handle": "somepage"})[0], "https://www.facebook.com/somepage")
        self.assertEqual(pl.build("youtube", {"handle": "@chan_1"})[0], "https://www.youtube.com/@chan_1")
        self.assertEqual(pl.build("youtube", {"handle": "UC" + "a" * 22})[0], "https://www.youtube.com/channel/UC" + "a" * 22)
        self.assertEqual(pl.build("linkedin", {"handle": "jane-doe"})[0], "https://www.linkedin.com/in/jane-doe")

    def test_real_links_on_the_right_site_are_kept(self):
        self.assertEqual(pl.build("instagram", {"handle": "https://www.instagram.com/x/"})[0], "https://www.instagram.com/x/")
        self.assertEqual(pl.build("instagram", {"handle": "instagram.com/x"})[0], "https://instagram.com/x")

    def test_lookalike_wrong_site_and_insecure_links_rejected(self):
        for bad in ("https://instagram.com.evil.test/x", "https://evilinstagram.com/x", "http://instagram.com/x",
                    "https://example.com/x", "https://u:p@instagram.com/x", "not a handle!"):
            with self.assertRaises(QRError, msg=bad):
                pl.build("instagram", {"handle": bad})
        with self.assertRaises(QRError):
            pl.build("linkedin", {"handle": "https://facebook.com/x"})

    def test_other_profile_url(self):
        payload, notes = pl.build("social_other", SAMPLES["social_other"])
        self.assertEqual(payload, "https://example.com/me")
        self.assertTrue(any("not checked" in n for n in notes))
        with self.assertRaises(QRError):
            pl.build("social_other", {"url": "javascript:alert(1)"})


class FileLinkTests(unittest.TestCase):
    def test_every_document_kind_accepts_matching_extensions(self):
        expect = {"PDF document": "a.pdf", "Word document": "a.docx", "Excel spreadsheet": "a.xlsx",
                  "PowerPoint presentation": "a.pptx", "Text file": "a.txt", "CSV file": "a.csv", "ZIP archive": "a.zip",
                  "Python source file": "tool.py"}
        for kind, name in expect.items():
            self.assertEqual(pl.build("file_link", {"kind": kind, "url": f"https://example.com/d/{name}"})[0],
                             f"https://example.com/d/{name}")
        self.assertIn(".doc", pl.FILE_KINDS["Word document"])
        self.assertIn(".xls", pl.FILE_KINDS["Excel spreadsheet"])
        self.assertIn(".ppt", pl.FILE_KINDS["PowerPoint presentation"])

    def test_mismatched_and_blocked_extensions_rejected(self):
        with self.assertRaises(QRError):
            pl.build("file_link", {"kind": "PDF document", "url": "https://x.com/a.docx"})
        for ext in (".exe", ".msi", ".bat", ".ps1", ".apk", ".dll", ".sh", ".js", ".vbs", ".jar"):
            for kind in ("PDF document", "Other document (json, xml, md, rtf, odt, ods, odp, epub)"):
                with self.assertRaisesRegex(QRError, "not accepted", msg=ext):      # the specific deny-list message
                    pl.build("file_link", {"kind": kind, "url": f"https://x.com/a{ext}"})

    def test_cloud_links_without_extension_are_allowed_with_advice(self):
        payload, notes = pl.build("file_link", {"kind": "PDF document", "url": "https://dropbox.com/s/abc123/menu?dl=0"})
        self.assertTrue(payload.startswith("https://dropbox.com/"))
        text = " ".join(notes)
        self.assertIn("no file extension", text)
        self.assertIn("CyberShield AI does not host files", pl.TYPES_BY_ID["file_link"].note)

    def test_note_explains_hosting_and_does_not_claim_to_host(self):
        for t in ("file_link", "drive"):
            note = pl.TYPES_BY_ID[t].note
            self.assertIn("cannot contain" if t == "file_link" else "Share", note)
            self.assertIn("does not", note)

    def test_google_drive_links(self):
        ok = pl.build("drive", SAMPLES["drive"])[0]
        self.assertTrue(ok.startswith("https://drive.google.com/file/d/"))
        self.assertTrue(pl.build("drive", {"url": "https://docs.google.com/spreadsheets/d/xyz/edit"})[0])
        for bad in ("https://evil.com/file/d/x", "http://drive.google.com/file/d/x", "https://drive.google.com/",
                    "https://drive.google.com.evil.test/file/d/x"):
            with self.assertRaises(QRError, msg=bad):
                pl.build("drive", {"url": bad})


class CalendarTests(unittest.TestCase):
    def lines(self, **over):
        values = dict(SAMPLES["calendar"], **over)
        return pl.build("calendar", values)[0].split("\r\n")

    def test_timed_event(self):
        ls = self.lines()
        self.assertEqual(ls[0], "BEGIN:VCALENDAR")
        self.assertEqual(ls[-1], "END:VCALENDAR")
        self.assertIn("DTSTART:20261102T090000", ls)
        self.assertIn("DTEND:20261102T103000", ls)
        self.assertIn(r"SUMMARY:Launch\; party", ls)
        self.assertIn(r"LOCATION:HQ\, Floor 2", ls)
        self.assertIn(r"DESCRIPTION:Bring\nsnacks", ls)

    def test_utc_and_all_day(self):
        self.assertIn("DTSTART:20261102T090000Z", self.lines(utc=True))
        ls = self.lines(all_day=True, end_date=date(2026, 11, 3))
        self.assertIn("DTSTART;VALUE=DATE:20261102", ls)
        self.assertIn("DTEND;VALUE=DATE:20261104", ls)          # DTEND is exclusive

    def test_validation(self):
        with self.assertRaises(QRError):
            self.lines(end_time=time(8, 0))
        with self.assertRaises(QRError):
            self.lines(end_date=date(2026, 11, 1))
        with self.assertRaises(QRError):
            self.lines(all_day=True, end_date=date(2026, 11, 1))
        with self.assertRaises(QRError):
            self.lines(title="")
        with self.assertRaises(QRError):
            pl.build("calendar", {"title": "x"})

    def test_output_is_deterministic_and_unique_per_event(self):
        a, b = pl.build("calendar", SAMPLES["calendar"])[0], pl.build("calendar", SAMPLES["calendar"])[0]
        self.assertEqual(a, b)
        self.assertNotEqual(a, pl.build("calendar", dict(SAMPLES["calendar"], title="Other"))[0])

    def test_long_lines_are_folded_to_75_octets(self):
        payload = pl.build("calendar", dict(SAMPLES["calendar"], description="é" * 150))[0]
        for physical in payload.split("\r\n"):
            self.assertLessEqual(len(physical.encode("utf-8")), 75)
        unfolded = payload.replace("\r\n ", "")
        self.assertIn("DESCRIPTION:" + "é" * 150, unfolded)

    def test_injection_cannot_add_event_fields(self):
        with self.assertRaises(QRError):
            self.lines(title="x\r\nATTENDEE:mailto:evil@x.com")
        self.assertNotIn("\r\nATTENDEE", pl.build("calendar", dict(SAMPLES["calendar"], description="a\nATTENDEE:x"))[0])


class PreviewTests(unittest.TestCase):
    def test_wifi_password_is_masked_in_the_readable_preview(self):
        payload = pl.build("wifi", {"ssid": "Cafe", "password": "sup3rsecret", "security": "WPA"})[0]
        shown = pl.readable_preview(payload)
        self.assertNotIn("sup3rsecret", shown)
        self.assertIn("Cafe", shown)
        self.assertIn("sup3rsecret", payload)               # the code itself is unchanged

    def test_long_payloads_are_truncated_for_display_only(self):
        payload = "x" * 1000
        self.assertLess(len(pl.readable_preview(payload)), 500)
        self.assertIn("1000 characters", pl.readable_preview(payload))


if __name__ == "__main__":
    unittest.main()
