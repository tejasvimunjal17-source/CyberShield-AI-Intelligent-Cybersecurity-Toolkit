"""Part 7 UI-flow tests for the File Hash Analyzer and Part 6 + Part 7 compatibility.

Run against tests/fake_streamlit.py, a recording stand-in: they check what the app
asks Streamlit to render and which network calls it makes. They are NOT a
substitute for opening the real app in a browser.
"""

import hashlib
import importlib
import io
import unittest
from unittest import mock

from backend import virustotal_client as vt
from config import MAX_UPLOAD_BYTES
from tests.test_url_scanner_ui import UiBase
from tests.test_vt_file_report import AID, FILE_REPORT, SHA256
from tests.test_vt_url_report import BASE, GET, POST, URL_REPORT, FakeResponse

DATA = b"hello"
OK_POST = {"data": {"id": AID, "type": "analysis"}}


class FakeUpload(io.BytesIO):
    """Stand-in for Streamlit's UploadedFile."""

    def __init__(self, data=DATA, name="Quarterly payroll.xlsx", file_id="id-1"):
        super().__init__(data)
        self.name, self.file_id, self.size = name, file_id, len(data)


class FileUiBase(UiBase):
    def setUp(self):
        super().setUp()
        self.fa = importlib.import_module("views.file_analyzer")
        self.upload = FakeUpload()
        self.st.file_uploader.return_value = self.upload
        self.typed = ""
        self.st.text_input.side_effect = lambda label, key=None, **kw: self.typed if key == "typed_hash" else ""

    def page(self):
        self.fa.render()

    def lookup(self, response=None):
        self.pressed = {"file_vt_btn"}
        with mock.patch(GET, return_value=response or FakeResponse(200, FILE_REPORT)) as get, \
                mock.patch(POST) as post:
            self.page()
        self.pressed = set()
        return get, post

    def captions(self):
        return str(self.st.caption.call_args_list)


class LocalHashingUiTests(FileUiBase):
    def test_hashes_shown_and_nothing_sent_without_a_button_press(self):
        with mock.patch(GET) as get, mock.patch(POST) as post:
            self.page()
        get.assert_not_called()
        post.assert_not_called()
        codes = [c.args[0] for c in self.st.code.call_args_list]
        self.assertIn(hashlib.sha256(DATA).hexdigest(), codes)
        self.assertIn(hashlib.sha1(DATA).hexdigest(), codes)
        self.assertIn(hashlib.md5(DATA).hexdigest(), codes)
        self.assertIn("file_vt_btn", [c[1] for c in self.button_calls])
        self.assertFalse(self.st.dataframe.called)

    def test_file_read_earlier_is_rewound_before_hashing(self):
        self.upload.read()  # position now at end, as after an earlier read
        self.page()
        self.assertIn(hashlib.sha256(DATA).hexdigest(), [c.args[0] for c in self.st.code.call_args_list])

    def test_different_file_with_same_name_and_size_is_rehashed(self):
        self.page()
        other = FakeUpload(b"world", name=self.upload.name, file_id="id-2")
        self.assertEqual(other.size, self.upload.size)
        self.st.file_uploader.return_value = other
        self.st.code.reset_mock()
        self.page()
        codes = [c.args[0] for c in self.st.code.call_args_list]
        self.assertIn(hashlib.sha256(b"world").hexdigest(), codes)
        self.assertNotIn(hashlib.sha256(DATA).hexdigest(), codes)

    def test_oversized_file_is_rejected_without_reading_or_any_vt_section(self):
        big = FakeUpload()
        big.size = MAX_UPLOAD_BYTES + 1
        self.st.file_uploader.return_value = big
        with mock.patch.object(self.fa, "hash_stream") as hs, mock.patch(GET) as get, mock.patch(POST) as post:
            self.page()
        hs.assert_not_called()
        get.assert_not_called()
        post.assert_not_called()
        self.assertIn("exceeds", str(self.errors()))
        self.assertNotIn("file_vt_btn", [c[1] for c in self.button_calls])

    def test_empty_file_hashes_but_cannot_be_uploaded(self):
        self.st.file_uploader.return_value = FakeUpload(b"", name="e.txt")
        self.page()
        self.assertIn("empty", str(self.st.info.call_args_list))
        self.fake.session["file_vt_result"] = {
            "hash": hashlib.sha256(b"").hexdigest(),
            "report": vt.VTReport(kind="file", identifier="x", found=False), "error": ""}
        self.fake.session["hash_cache_key"] = None
        self.page()
        self.assertTrue(any("empty" in e for e in self.errors()))
        self.assertNotIn("file_vt_up_btn", [c[1] for c in self.button_calls])


class LookupUiTests(FileUiBase):
    def test_not_configured_shows_notice_and_makes_no_requests(self):
        import os
        with mock.patch.dict(os.environ, {"VIRUSTOTAL_API_KEY": ""}):
            with mock.patch(GET) as get, mock.patch(POST) as post:
                self.page()
        get.assert_not_called()
        post.assert_not_called()
        self.assertNotIn("file_vt_btn", [c[1] for c in self.button_calls])
        self.assertTrue(self.st.info.called)

    def test_lookup_sends_only_the_hash_and_never_uploads(self):
        get, post = self.lookup()
        post.assert_not_called()
        self.assertEqual(get.call_count, 1)
        self.assertTrue(get.call_args.args[0].endswith("/files/" + hashlib.sha256(DATA).hexdigest()))
        self.assertNotIn("headers", str(post.call_args_list))

    def test_report_renders_only_real_fields(self):
        self.lookup()
        md = self.fake.all_markdown()
        self.assertIn("3 of 64 vendor results flagged this file as malicious and 1 as suspicious", md)
        flat = str(self.st.dataframe.call_args_list) + str(self.st.metric.call_args_list) + \
            str(self.st.code.call_args_list) + str(self.st.mock_calls)
        for expected in ("Alpha", "Trojan.Evil", "Win32 EXE", "setup.exe", "trojan.evil/gen",
                         "2012-12-11", "SHA-256: " + SHA256, "123456"):
            self.assertIn(expected, flat, expected)
        self.assertEqual(self.st.tabs.call_args.args[0], ["Summary", "Detection", "Details"])
        self.assertNotIn("must be ignored for files", flat)

    def test_zero_detections_is_not_called_safe(self):
        clean = {"data": {"id": SHA256, "attributes": {
            "last_analysis_stats": {"harmless": 50, "undetected": 10}, "last_analysis_date": 1760868000}}}
        self.lookup(FakeResponse(200, clean))
        md = self.fake.all_markdown() + self.captions() + str(self.st.success.call_args_list)
        self.assertIn("not proof", md)
        self.assertNotIn("is safe.", md.replace("not proof the file is safe.", ""))

    def test_missing_report_is_not_a_clean_verdict_and_tabs_are_absent(self):
        self.lookup(FakeResponse(404, {}))
        md = self.fake.all_markdown() + self.captions()
        self.assertIn("no existing report", md)
        self.assertIn("not a verdict", md)
        self.assertFalse(self.st.tabs.called)

    def test_error_is_shown_and_survives_rerun(self):
        self.lookup(FakeResponse(429, {}))
        self.assertIn("failed", self.fake.all_markdown())
        self.fake.markdown_calls.clear()
        with mock.patch(GET) as get:
            self.page()
        get.assert_not_called()
        self.assertIn("failed", self.fake.all_markdown())

    def test_untrusted_strings_are_not_injected_as_html(self):
        payload = {"data": {"id": SHA256, "attributes": {
            "last_analysis_stats": {"harmless": 1}, "tags": ["<script>alert(1)</script>"],
            "last_analysis_results": {"E": {"category": "harmless"}}}}}
        self.lookup(FakeResponse(200, payload))
        html = self.fake.all_markdown()
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_hash_mismatch_in_returned_report_is_warned(self):
        other = {"data": {"id": "b" * 64, "attributes": {
            "last_analysis_stats": {"harmless": 5}, "sha256": "b" * 64, "last_analysis_date": 1760868000}}}
        self.lookup(FakeResponse(200, other))
        self.assertTrue(self.st.warning.called)
        self.assertIn("do not include the hash", str(self.st.warning.call_args_list))

    def test_typed_hash_lookup_has_no_upload_option(self):
        self.st.file_uploader.return_value = None
        self.typed = SHA256
        self.pressed = {"typed_vt_btn"}
        with mock.patch(GET, return_value=FakeResponse(200, FILE_REPORT)) as get, mock.patch(POST) as post:
            self.page()
        post.assert_not_called()
        self.assertTrue(get.call_args.args[0].endswith("/files/" + SHA256))
        self.assertNotIn("typed_vt_up_btn", [c[1] for c in self.button_calls])
        self.assertIn("pasted hash cannot be uploaded", self.captions())

    def test_invalid_typed_hash_makes_no_request(self):
        self.st.file_uploader.return_value = None
        self.typed = "xyz"
        with mock.patch(GET) as get, mock.patch(POST) as post:
            self.page()
        get.assert_not_called()
        post.assert_not_called()
        self.assertTrue(self.errors())


class UploadFlowTests(FileUiBase):
    def setUp(self):
        super().setUp()
        self.lookup(FakeResponse(404, {}))
        self.h = hashlib.sha256(DATA).hexdigest()

    def test_privacy_notes_are_shown_before_any_upload(self):
        md = self.fake.all_markdown()
        for needle in ("third-party", "security community", "personal", "cannot be taken back",
                       "file name is not sent"):
            self.assertIn(needle, md)
        labels = [c.args[0] for c in self.st.expander.call_args_list]
        self.assertTrue(any("Upload this file to VirusTotal" in label for label in labels))

    def test_unconfirmed_upload_is_disabled_and_sends_nothing(self):
        self.pressed = {"file_vt_up_btn"}
        with mock.patch(POST) as post:
            self.page()
        post.assert_not_called()
        self.assertTrue([c for c in self.button_calls if c[1] == "file_vt_up_btn"][-1][2])

    def test_confirmed_upload_posts_once_with_the_exact_bytes_and_neutral_name(self):
        self.fake.session["file_vt_up_confirm"] = True
        self.pressed = {"file_vt_up_btn"}
        with mock.patch(POST, return_value=FakeResponse(200, OK_POST)) as post, mock.patch(GET) as get:
            self.page()
        self.assertEqual(post.call_count, 1)
        self.assertEqual(post.call_args.args[0], BASE + "/files")
        self.assertEqual(post.call_args.kwargs["files"], {"file": ("sample", DATA)})
        get.assert_not_called()
        self.assertNotIn("payroll", str(post.call_args_list))   # original file name never leaves
        self.assertEqual(self.fake.session["file_vt_up_sub"]["analysis_id"], AID)
        self.assertIn("not a verdict", str(self.st.success.call_args_list))
        self.assertIn("file_vt_up_status_btn", [c[1] for c in self.button_calls])

    def test_file_changed_since_hashing_is_not_uploaded(self):
        self.fake.session["file_vt_up_confirm"] = True
        self.upload.getvalue = lambda: b"tampered"
        self.pressed = {"file_vt_up_btn"}
        with mock.patch(POST) as post:
            self.page()
        post.assert_not_called()
        self.assertIn("changed", str(self.errors()))

    def test_upload_errors_are_reported_accurately(self):
        for status, text in ((429, "rate limit"), (401, "rejected the api key"), (413, "too large")):
            vt._limiter = vt._MinuteLimiter()
            self.st.error.reset_mock()
            self.fake.session["file_vt_up_confirm"] = True
            self.pressed = {"file_vt_up_btn"}
            with mock.patch(POST, return_value=FakeResponse(status, {})):
                self.page()
            self.assertTrue(any(text in e.lower() for e in self.errors()), status)
        self.assertFalse(self.st.success.called)

    def test_network_failure_during_upload_is_reported(self):
        import requests
        self.fake.session["file_vt_up_confirm"] = True
        self.pressed = {"file_vt_up_btn"}
        with mock.patch(POST, side_effect=requests.exceptions.Timeout()):
            self.page()
        self.assertIn("did not respond", str(self.errors()))

    def test_consent_does_not_carry_over_to_a_different_file(self):
        self.fake.session["file_vt_up_confirm"] = True
        self.fake.session["file_vt_up_confirm_hash"] = self.h
        other = FakeUpload(b"another file", name="b.bin", file_id="id-9")
        self.st.file_uploader.return_value = other
        self.fake.session["file_vt_result"] = {
            "hash": hashlib.sha256(b"another file").hexdigest(),
            "report": vt.VTReport(kind="file", identifier="x", found=False), "error": ""}
        self.page()
        self.assertFalse(self.fake.session["file_vt_up_confirm"])

    def test_status_queued_then_completed(self):
        self.fake.session["file_vt_up_sub"] = {"hash": self.h, "analysis_id": AID, "error": ""}
        self.pressed = {"file_vt_up_status_btn"}
        queued = {"data": {"attributes": {"status": "queued", "stats": {}, "results": {}}}}
        with mock.patch(GET, return_value=FakeResponse(200, queued)) as get:
            self.page()
        self.assertTrue(get.call_args.args[0].endswith("/analyses/" + AID))
        self.assertIn("No verdict exists yet", str(self.st.info.call_args_list))
        self.st.info.reset_mock()
        done = {"data": {"attributes": {"status": "completed", "date": 1760868000,
                                        "stats": {"malicious": 1, "harmless": 5},
                                        "results": {"A": {"category": "malicious", "result": "x"}}}}}
        with mock.patch(GET, return_value=FakeResponse(200, done)):
            self.page()
        self.assertNotIn("No verdict exists yet", str(self.st.info.call_args_list))
        self.assertIn("Completed", self.fake.all_markdown())

    def test_status_error_shown(self):
        self.fake.session["file_vt_up_sub"] = {"hash": self.h, "analysis_id": AID, "error": ""}
        self.pressed = {"file_vt_up_status_btn"}
        with mock.patch(GET, return_value=FakeResponse(200, {"data": {}})):
            self.page()
        self.assertTrue(self.errors())


class CombinedPart6And7Tests(FileUiBase):
    def test_url_scanner_and_file_analyzer_use_the_same_client_and_do_not_share_state(self):
        scanner = importlib.import_module("views.url_scanner")
        self.assertIs(scanner.vt, self.fa.vt)                       # one client module, not a copy
        from backend.url_analyzer import analyze_url
        self.pressed = {"url_vt_btn"}
        with mock.patch(GET, return_value=FakeResponse(200, URL_REPORT)):
            scanner.render_vt_section(analyze_url("https://example.com/"), "url")
        self.pressed = set()
        self.lookup(FakeResponse(200, FILE_REPORT))
        s = self.fake.session
        self.assertEqual(s["url_vt_result"]["url"], "https://example.com/")
        self.assertEqual(s["file_vt_result"]["hash"], hashlib.sha256(DATA).hexdigest())
        self.assertEqual({k for k in s if k.endswith("_vt_result")}, {"url_vt_result", "file_vt_result"})

    def test_rate_guard_is_shared_between_both_scanners(self):
        from backend.url_analyzer import analyze_url
        scanner = importlib.import_module("views.url_scanner")
        self.pressed = {"url_vt_btn"}
        with mock.patch(GET, return_value=FakeResponse(404, {})):
            for _ in range(vt.PUBLIC_API_PER_MINUTE):
                scanner.render_vt_section(analyze_url("https://example.com/"), "url")
        self.pressed = {"file_vt_btn"}
        with mock.patch(GET) as get:
            self.page()
        get.assert_not_called()                                      # blocked locally, not sent
        self.assertIn("failed", self.fake.all_markdown())
        self.assertIn("Local rate guard", str(self.fake.session["file_vt_result"]["error"]))

    def test_url_scanner_submission_still_works_next_to_file_upload(self):
        from backend.url_analyzer import analyze_url
        scanner = importlib.import_module("views.url_scanner")
        self.pressed = {"url_vt_btn"}
        with mock.patch(GET, return_value=FakeResponse(404, {})):
            scanner.render_vt_section(analyze_url("https://example.com/x"), "url")
        self.fake.session["url_vt_confirm"] = True
        self.pressed = {"url_vt_submit_btn"}
        with mock.patch(POST, return_value=FakeResponse(200, OK_POST)) as post:
            scanner.render_vt_section(analyze_url("https://example.com/x"), "url")
        self.assertEqual(post.call_args.args[0], BASE + "/urls")
        self.assertEqual(post.call_args.kwargs["data"], {"url": "https://example.com/x"})
        self.assertNotIn("files", post.call_args.kwargs)

    def test_old_report_renderer_and_helpers_still_importable(self):
        vr = importlib.import_module("components.vt_report")
        for name in ("vt_available", "run_lookup", "render_report", "safe_call", "not_configured_notice"):
            self.assertTrue(callable(getattr(vr, name)), name)
        qr = importlib.import_module("views.qr_analyzer")
        self.assertTrue(callable(qr.render))

    def test_missing_key_disables_both_scanners_and_sends_nothing(self):
        import os
        from backend.url_analyzer import analyze_url
        scanner = importlib.import_module("views.url_scanner")
        with mock.patch.dict(os.environ, {"VIRUSTOTAL_API_KEY": ""}):
            with mock.patch(GET) as get, mock.patch(POST) as post:
                scanner.render_vt_section(analyze_url("https://example.com/"), "url")
                self.page()
        get.assert_not_called()
        post.assert_not_called()
        keys = [c[1] for c in self.button_calls]
        self.assertNotIn("url_vt_btn", keys)
        self.assertNotIn("file_vt_btn", keys)

    def test_api_key_never_rendered_by_either_scanner(self):
        self.lookup(FakeResponse(200, FILE_REPORT))
        self.assertNotIn(self.key_env, self.fake.all_markdown() + str(self.st.mock_calls))


if __name__ == "__main__":
    unittest.main()
