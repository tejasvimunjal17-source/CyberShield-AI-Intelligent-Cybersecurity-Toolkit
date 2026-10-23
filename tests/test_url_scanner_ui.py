"""Part 6 UI-flow tests for the URL scanner and shared-component compatibility.

These run against tests/fake_streamlit.py (a recording stand-in). They check
what the app asks Streamlit to render and which network calls it makes. They
are NOT a substitute for opening the real app in a browser.
"""

import importlib
import os
import sys
import unittest
from unittest import mock

from backend import virustotal_client as vt
from backend.url_analyzer import analyze_url
from tests.fake_streamlit import FakeStreamlit
from tests.test_vt_url_report import URL_REPORT, FakeResponse

GET = "backend.virustotal_client.requests.get"
POST = "backend.virustotal_client.requests.post"
BASE = "https://www.virustotal.com/api/v3"
URL_A = "https://example.com/login?token=abc"
URL_B = "https://other.example.org/"
AID = "u-abc123def456-1700000000"
FILE_PAYLOAD = {"data": {"id": "f" * 64, "attributes": {
    "last_analysis_stats": {"malicious": 1, "harmless": 9},
    "last_analysis_results": {"EngineA": {"category": "malicious", "result": "Trojan.Y"}}}}}


class UiBase(unittest.TestCase):
    key_env = "test-key"

    def setUp(self):
        vt._limiter = vt._MinuteLimiter()
        self.fake = FakeStreamlit()
        self.st = self.fake.st
        self.pressed: set = set()
        self.button_calls: list = []

        def button(label, key=None, disabled=False, **kw):
            self.button_calls.append((label, key, disabled))
            return (key in self.pressed or label in self.pressed) and not disabled

        self.st.button.side_effect = button
        self.st.checkbox.side_effect = lambda label, key=None, **kw: self.fake.session.get(key, False)
        self.st.tabs.side_effect = lambda labels: [mock.MagicMock() for _ in labels]

        self.env = mock.patch.dict(os.environ, {"VIRUSTOTAL_API_KEY": self.key_env})
        self.env.start()
        self.mods = mock.patch.dict(sys.modules, {"streamlit": self.st})
        self.mods.start()
        for name in [m for m in list(sys.modules) if m.split(".")[0] in ("views", "components")]:
            del sys.modules[name]
        self.scanner = importlib.import_module("views.url_scanner")
        self.vt_report = importlib.import_module("components.vt_report")

    def tearDown(self):
        self.mods.stop()
        self.env.stop()
        for name in [m for m in list(sys.modules) if m.split(".")[0] in ("views", "components")]:
            sys.modules.pop(name, None)

    # helpers
    def section(self, url=URL_A, prefix="url"):
        self.scanner.render_vt_section(analyze_url(url), prefix)

    def errors(self):
        return [c.args[0] for c in self.st.error.call_args_list]

    def button_state(self, key):
        return [c for c in self.button_calls if c[1] == key]


class LookupFlowTests(UiBase):
    def test_not_configured_shows_notice_and_no_buttons_or_requests(self):
        with mock.patch.dict(os.environ, {"VIRUSTOTAL_API_KEY": ""}):
            with mock.patch(GET) as get, mock.patch(POST) as post:
                self.section()
        get.assert_not_called()
        post.assert_not_called()
        self.assertEqual(self.button_calls, [])
        self.assertTrue(self.st.info.called)

    def test_nothing_is_requested_until_button_pressed(self):
        with mock.patch(GET) as get, mock.patch(POST) as post:
            self.section()
        get.assert_not_called()
        post.assert_not_called()
        self.assertIn("url_vt_btn", [c[1] for c in self.button_calls])
        self.assertFalse(self.st.dataframe.called)

    def test_lookup_renders_real_fields_and_never_submits(self):
        self.pressed = {"url_vt_btn"}
        with mock.patch(GET, return_value=FakeResponse(200, URL_REPORT)) as get, mock.patch(POST) as post:
            self.section(URL_A)
        post.assert_not_called()
        self.assertEqual(get.call_count, 1)
        self.assertTrue(get.call_args.args[0].startswith(BASE + "/urls/"))
        self.assertNotIn("example.com", get.call_args.args[0])  # encoded id, not the raw URL
        md = self.fake.all_markdown()
        self.assertIn("2 of 83 vendor results flagged this URL as malicious", md)
        tables = [c.args[0] for c in self.st.dataframe.call_args_list]
        flat = str(tables)
        for expected in ("Alpha", "Beta", "Forcepoint", "social networking", "2012-12-11", "Zeta"):
            self.assertIn(expected, flat)
        self.assertTrue(self.st.tabs.called)
        self.assertEqual(self.st.tabs.call_args.args[0], ["Summary", "Detection", "Details"])
        self.assertEqual(self.button_state("url_vt_submit_btn")[0][2], True)  # disabled: not confirmed
        self.assertFalse(self.errors())

    def test_untrusted_strings_are_not_injected_as_html(self):
        payload = {"data": {"id": "x", "attributes": {
            "last_analysis_stats": {"harmless": 1},
            "tags": ["<script>alert(1)</script>"],
            "last_analysis_results": {"E": {"category": "harmless"}}}}}
        self.pressed = {"url_vt_btn"}
        with mock.patch(GET, return_value=FakeResponse(200, payload)):
            self.section()
        html = self.fake.all_markdown()
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_redirect_chain_is_defanged_inert_text(self):
        self.pressed = {"url_vt_btn"}
        with mock.patch(GET, return_value=FakeResponse(200, URL_REPORT)):
            self.section()
        codes = [c.args[0] for c in self.st.code.call_args_list]
        chain = [c for c in codes if "->" in c]
        self.assertTrue(chain)
        self.assertIn("hxxps://example[.]com/", chain[0])
        self.assertNotIn("https://", chain[0])

    def test_error_is_shown_and_survives_rerun(self):
        self.pressed = {"url_vt_btn"}
        with mock.patch(GET, return_value=FakeResponse(429, {})):
            self.section()
        self.assertTrue(any("rate limit" in e.lower() for e in self.errors()) or
                        "failed" in self.fake.all_markdown())
        self.assertIn("failed", self.fake.all_markdown())
        self.assertIn("says nothing about the URL", str(self.st.caption.call_args_list))
        self.pressed = set()
        self.fake.markdown_calls.clear()
        with mock.patch(GET) as get:
            self.section()
        get.assert_not_called()
        self.assertIn("failed", self.fake.all_markdown())  # still shown, no new request

    def test_not_found_is_not_a_verdict_and_offers_opt_in_submission(self):
        self.pressed = {"url_vt_btn"}
        with mock.patch(GET, return_value=FakeResponse(404, {})), mock.patch(POST) as post:
            self.section()
        post.assert_not_called()
        self.assertIn("no existing report", self.fake.all_markdown())
        self.assertFalse(self.st.tabs.called)
        labels = [c.args[0] for c in self.st.expander.call_args_list]
        self.assertTrue(any("Request a new analysis" in label for label in labels))

    def test_report_for_a_different_url_is_not_shown(self):
        self.pressed = {"url_vt_btn"}
        with mock.patch(GET, return_value=FakeResponse(200, URL_REPORT)):
            self.section(URL_A)
        self.st.dataframe.reset_mock()
        self.pressed = set()
        self.section(URL_B)
        self.assertFalse(self.st.dataframe.called)


class SubmissionFlowTests(UiBase):
    def _lookup_first(self, url=URL_A):
        self.pressed = {"url_vt_btn"}
        with mock.patch(GET, return_value=FakeResponse(404, {})):
            self.section(url)
        self.pressed = set()

    def test_privacy_notes_are_shown_before_submission(self):
        self._lookup_first()
        md = self.fake.all_markdown()
        self.assertIn("third-party", md)
        self.assertIn("query parameters", md)  # URL_A has ?token=
        self.assertIn("never visits", md)

    def test_unconfirmed_submit_is_disabled_and_sends_nothing(self):
        self._lookup_first()
        self.pressed = {"url_vt_submit_btn"}  # user "clicks" a disabled button
        with mock.patch(POST) as post:
            self.section()
        post.assert_not_called()
        self.assertTrue(self.button_state("url_vt_submit_btn")[-1][2])

    def test_confirmed_submit_posts_once_to_virustotal_only(self):
        self._lookup_first()
        self.fake.session["url_vt_confirm"] = True  # ticked after the first render
        self.pressed = {"url_vt_submit_btn"}
        resp = FakeResponse(200, {"data": {"id": AID}})
        with mock.patch(POST, return_value=resp) as post, mock.patch(GET) as get:
            self.section()
        self.assertEqual(post.call_count, 1)
        self.assertEqual(post.call_args.args[0], BASE + "/urls")
        self.assertEqual(post.call_args.kwargs["data"], {"url": URL_A})
        get.assert_not_called()
        self.assertEqual(self.fake.session["url_vt_sub"]["analysis_id"], AID)
        self.assertIn(AID, str(self.st.caption.call_args_list))
        self.assertIn("not a verdict", str(self.st.success.call_args_list))
        self.assertIn("url_vt_status_btn", [c[1] for c in self.button_calls])

    def test_submission_error_is_reported_accurately(self):
        self._lookup_first()
        self.fake.session["url_vt_confirm"] = True
        self.pressed = {"url_vt_submit_btn"}
        with mock.patch(POST, return_value=FakeResponse(429, {})):
            self.section()
        self.assertTrue(any("rate limit" in e.lower() for e in self.errors()))
        self.assertFalse(self.st.success.called)

    def test_consent_does_not_carry_over_to_another_url(self):
        self._lookup_first(URL_A)
        self.fake.session["url_vt_confirm"] = True
        self.fake.session["url_vt_confirm_url"] = URL_A
        self.pressed = {"url_vt_btn"}
        with mock.patch(GET, return_value=FakeResponse(404, {})):
            self.section(URL_B)
        self.assertFalse(self.fake.session["url_vt_confirm"])

    def test_status_queued_then_completed(self):
        self._lookup_first()
        self.fake.session["url_vt_sub"] = {"url": URL_A, "analysis_id": AID, "error": ""}
        self.pressed = {"url_vt_status_btn"}
        queued = {"data": {"attributes": {"status": "queued", "stats": {}, "results": {}}}}
        with mock.patch(GET, return_value=FakeResponse(200, queued)) as get:
            self.section()
        self.assertTrue(get.call_args.args[0].endswith("/analyses/" + AID))
        self.assertIn("No verdict exists yet", str(self.st.info.call_args_list))

        self.st.info.reset_mock()
        done = {"data": {"attributes": {"status": "completed", "date": 1760868000,
                                        "stats": {"malicious": 1, "harmless": 5},
                                        "results": {"A": {"category": "malicious", "result": "x"}}}}}
        with mock.patch(GET, return_value=FakeResponse(200, done)):
            self.section()
        self.assertNotIn("No verdict exists yet", str(self.st.info.call_args_list))
        self.assertIn("Completed", self.fake.all_markdown())
        self.assertIn("A", str(self.st.dataframe.call_args_list))

    def test_status_error_shown(self):
        self._lookup_first()
        self.fake.session["url_vt_sub"] = {"url": URL_A, "analysis_id": AID, "error": ""}
        self.pressed = {"url_vt_status_btn"}
        with mock.patch(GET, return_value=FakeResponse(200, {"data": {}})):
            self.section()
        self.assertTrue(self.errors())


class FullPageAndCompatibilityTests(UiBase):
    def test_full_page_separates_local_and_external_and_makes_no_request(self):
        self.st.text_input.return_value = URL_A
        self.pressed = {"Analyze URL"}
        with mock.patch(GET) as get, mock.patch(POST) as post:
            self.scanner.render()
        get.assert_not_called()
        post.assert_not_called()
        subs = [c.args[0] for c in self.st.subheader.call_args_list]
        self.assertLess(subs.index("Local heuristic analysis"), subs.index("VirusTotal reputation"))

    def test_qr_analyzer_still_shares_the_same_functions(self):
        qr = importlib.import_module("views.qr_analyzer")
        self.assertIs(qr.render_vt_section, self.scanner.render_vt_section)
        self.assertIs(qr.render_analysis, self.scanner.render_analysis)

    def test_file_analyzer_lookup_still_works_and_uses_the_part7_report(self):
        # Part 7 intentionally replaced the old flat file report with Summary/Detection/Details tabs.
        fa = importlib.import_module("views.file_analyzer")
        self.pressed = {"k_btn"}
        with mock.patch(GET, return_value=FakeResponse(200, FILE_PAYLOAD)) as get, mock.patch(POST) as post:
            fa._lookup_block("f" * 64, "k")
        post.assert_not_called()
        self.assertTrue(get.call_args.args[0].endswith("/files/" + "f" * 64))
        self.assertIn("EngineA", str(self.st.dataframe.call_args_list))
        self.assertEqual(self.st.tabs.call_args.args[0], ["Summary", "Detection", "Details"])

    def test_vt_report_public_interface_preserved(self):
        for name in ("vt_available", "run_lookup", "render_report", "not_configured_notice"):
            self.assertTrue(callable(getattr(self.vt_report, name)))
        self.assertEqual(vt.VTReport(kind="file", identifier="x", found=True).all_results, [])
        with mock.patch(GET, return_value=FakeResponse(401, {})):
            self.assertIsNone(self.vt_report.run_lookup("file", "a" * 64))
        self.assertTrue(self.st.error.called)

    def test_api_key_never_rendered(self):
        self.pressed = {"url_vt_btn"}
        with mock.patch(GET, return_value=FakeResponse(200, URL_REPORT)):
            self.section()
        everything = self.fake.all_markdown() + str(self.st.mock_calls)
        self.assertNotIn(self.key_env, everything)


if __name__ == "__main__":
    unittest.main()
