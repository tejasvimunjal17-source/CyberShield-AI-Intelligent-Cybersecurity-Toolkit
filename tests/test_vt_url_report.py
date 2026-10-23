"""Part 6 backend tests. All VirusTotal traffic is mocked; no API key is needed."""

import os
import unittest
from datetime import datetime, timezone
from unittest import mock

import requests

from backend import url_report as ur
from backend import virustotal_client as vt
from backend.url_analyzer import analyze_url

GET = "backend.virustotal_client.requests.get"
POST = "backend.virustotal_client.requests.post"
KEY = "test-key-SECRET-123"
BASE = "https://www.virustotal.com/api/v3"


class FakeResponse:
    def __init__(self, status=200, payload=None, bad_json=False):
        self.status_code, self._payload, self._bad = status, payload, bad_json

    def json(self):
        if self._bad:
            raise ValueError("bad json")
        return self._payload


URL_REPORT = {"data": {"id": "deadbeef" * 8, "attributes": {
    "last_analysis_stats": {"malicious": 2, "suspicious": 1, "harmless": 60, "undetected": 20, "timeout": 0},
    "last_analysis_date": 1760868000,
    "last_analysis_results": {
        "Zeta": {"category": "harmless", "result": "clean"},
        "Beta": {"category": "suspicious", "result": "suspicious"},
        "Alpha": {"category": "malicious", "result": "phishing"},
        "Gamma": {"category": "undetected", "result": "unrated"},
        "Broken": "not-a-dict",
    },
    "last_final_url": "https://www.example.com/",
    "title": "Example <b>Title</b>",
    "last_http_response_code": 200,
    "last_http_response_headers": {"Content-Type": "text/html; charset=utf-8", "X": "y"},
    "categories": {"Forcepoint": "social networking", "BitDefender": "socialnetworks", "Empty": ""},
    "tags": ["password-input", "trackers", ""],
    "redirection_chain": ["https://example.com/", "https://www.example.com/"],
    "first_submission_date": 1355216161,
    "last_submission_date": 1760868000,
    "times_submitted": 4242,
    "reputation": 12,
    "threat_names": ["Phish.Gen"],
}}}


class ClientBase(unittest.TestCase):
    def setUp(self):
        vt._limiter = vt._MinuteLimiter()
        self.env = mock.patch.dict(os.environ, {"VIRUSTOTAL_API_KEY": KEY})
        self.env.start()

    def tearDown(self):
        self.env.stop()


class UrlReportParsingTests(ClientBase):
    def test_full_url_report_fields(self):
        with mock.patch(GET, return_value=FakeResponse(200, URL_REPORT)):
            r = vt.lookup_url("https://example.com/")
        self.assertTrue(r.found)
        self.assertEqual((r.malicious, r.suspicious, r.harmless, r.undetected), (2, 1, 60, 20))
        self.assertEqual(r.final_url, "https://www.example.com/")
        self.assertEqual(r.http_status, 200)
        self.assertEqual(r.content_type, "text/html; charset=utf-8")
        self.assertEqual(r.categories, [("BitDefender", "socialnetworks"), ("Forcepoint", "social networking")])
        self.assertEqual(r.tags, ["password-input", "trackers"])
        self.assertEqual(r.redirection_chain, ["https://example.com/", "https://www.example.com/"])
        self.assertEqual((r.first_submission_date, r.times_submitted, r.reputation), (1355216161, 4242, 12))
        self.assertEqual(r.threat_names, ["Phish.Gen"])
        self.assertEqual(r.report_id, "deadbeef" * 8)
        self.assertTrue(r.permalink.endswith("/gui/url/" + "deadbeef" * 8))

    def test_all_results_sorted_and_malformed_entries_skipped(self):
        with mock.patch(GET, return_value=FakeResponse(200, URL_REPORT)):
            r = vt.lookup_url("https://example.com/")
        self.assertEqual([row[0] for row in r.all_results], ["Alpha", "Beta", "Gamma", "Zeta"])
        self.assertEqual([row[0] for row in r.flagged_engines], ["Alpha", "Beta"])  # unchanged behaviour

    def test_missing_optional_fields_are_empty_not_invented(self):
        minimal = {"data": {"id": "x", "attributes": {"last_analysis_stats": {"harmless": 5}}}}
        with mock.patch(GET, return_value=FakeResponse(200, minimal)):
            r = vt.lookup_url("https://example.com/")
        self.assertEqual((r.final_url, r.title, r.content_type), ("", "", ""))
        self.assertIsNone(r.http_status)
        self.assertIsNone(r.first_submission_date)
        self.assertEqual((r.categories, r.tags, r.redirection_chain, r.all_results), ([], [], [], []))

    def test_wrong_types_do_not_crash_or_leak(self):
        weird = {"data": {"id": "x", "attributes": {
            "last_analysis_stats": {"malicious": "9", "harmless": True},
            "last_http_response_code": "200", "categories": ["a"], "tags": "nope",
            "redirection_chain": {"a": 1}, "times_submitted": 1.5,
            "last_analysis_date": "yesterday"}}}
        with mock.patch(GET, return_value=FakeResponse(200, weird)):
            r = vt.lookup_url("https://example.com/")
        self.assertEqual(r.malicious, 0)
        self.assertIsNone(r.http_status)
        self.assertIsNone(r.times_submitted)
        self.assertIsNone(r.last_analysis_date)
        self.assertEqual((r.categories, r.tags, r.redirection_chain), ([], [], []))

    def test_malformed_attribute_containers_raise_safe_error(self):
        for payload in ({"data": {"attributes": [1]}},
                        {"data": {"attributes": {"last_analysis_stats": "x"}}},
                        {"data": []}, {"nodata": 1}, None):
            with mock.patch(GET, return_value=FakeResponse(200, payload)):
                with self.assertRaises(vt.VirusTotalError):
                    vt.lookup_url("https://example.com/")

    def test_long_values_are_capped(self):
        big = {"data": {"id": "x", "attributes": {
            "last_analysis_stats": {"harmless": 1},
            "title": "T" * 5000, "tags": [f"t{i}" for i in range(500)],
            "last_analysis_results": {f"E{i}": {"category": "harmless"} for i in range(500)}}}}
        with mock.patch(GET, return_value=FakeResponse(200, big)):
            r = vt.lookup_url("https://example.com/")
        self.assertEqual(len(r.title), vt.MAX_TEXT_CHARS)
        self.assertEqual(len(r.tags), vt.MAX_LIST_ITEMS)
        self.assertEqual(len(r.all_results), vt.MAX_ALL_RESULT_ROWS)

    def test_file_reports_keep_url_fields_empty(self):
        payload = {"data": {"id": "abc", "attributes": {"last_analysis_stats": {"harmless": 1}, "title": "ignored"}}}
        with mock.patch(GET, return_value=FakeResponse(200, payload)):
            r = vt.lookup_hash("a" * 64)
        self.assertEqual((r.kind, r.title, r.all_results), ("file", "", []))

    def test_not_found_is_not_a_clean_verdict(self):
        with mock.patch(GET, return_value=FakeResponse(404, {})):
            r = vt.lookup_url("https://example.com/")
        self.assertFalse(r.found)
        self.assertEqual(r.total_engines, 0)

    def test_errors_map_to_specific_safe_exceptions_without_key(self):
        cases = [(401, vt.VirusTotalAuthError), (429, vt.VirusTotalRateLimitError),
                 (500, vt.VirusTotalError), (400, vt.VirusTotalInputError)]
        for status, exc_type in cases:
            vt._limiter = vt._MinuteLimiter()
            with mock.patch(GET, return_value=FakeResponse(status, {})):
                with self.assertRaises(exc_type) as cm:
                    vt.lookup_url("https://example.com/")
            self.assertNotIn(KEY, str(cm.exception))

    def test_timeout_and_connection_errors(self):
        for raised in (requests.exceptions.Timeout("t"), requests.exceptions.ConnectionError(f"boom {KEY}")):
            vt._limiter = vt._MinuteLimiter()
            with mock.patch(GET, side_effect=raised):
                with self.assertRaises(vt.VirusTotalNetworkError) as cm:
                    vt.lookup_url("https://example.com/")
            self.assertNotIn(KEY, str(cm.exception))

    def test_lookup_sends_encoded_id_to_configured_base_only(self):
        with mock.patch(GET, return_value=FakeResponse(404, {})) as get:
            vt.lookup_url("https://evil.test/a?b=1")
        called = get.call_args.args[0]
        self.assertTrue(called.startswith(BASE + "/urls/"))
        self.assertNotIn("evil.test", called)
        self.assertEqual(get.call_args.kwargs["timeout"], vt.REQUEST_TIMEOUT_SECONDS)


class SubmitUrlTests(ClientBase):
    def test_refuses_without_explicit_confirmation(self):
        for kwargs in ({}, {"confirmed": False}, {"confirmed": "yes"}, {"confirmed": 1}):
            with mock.patch(POST) as post:
                with self.assertRaises(vt.VirusTotalInputError):
                    vt.submit_url("https://example.com/", **kwargs)
                post.assert_not_called()

    def test_missing_key_makes_no_request(self):
        with mock.patch.dict(os.environ, {"VIRUSTOTAL_API_KEY": ""}):
            with mock.patch(POST) as post:
                with self.assertRaises(vt.VirusTotalNotConfiguredError):
                    vt.submit_url("https://example.com/", confirmed=True)
                post.assert_not_called()

    def test_rejects_non_http_and_oversized_urls(self):
        for bad in ("ftp://x.com", "javascript:alert(1)", "example.com", "", None, "http://a/" + "x" * 3000):
            with mock.patch(POST) as post:
                with self.assertRaises(vt.VirusTotalInputError):
                    vt.submit_url(bad, confirmed=True)
                post.assert_not_called()

    def test_success_posts_form_to_configured_base_only(self):
        with mock.patch(POST, return_value=FakeResponse(200, {"data": {"id": "u-abc123def456-1700000000", "type": "analysis"}})) as post:
            result = vt.submit_url("  https://example.com/x?y=1 ", confirmed=True)
        self.assertEqual(result.analysis_id, "u-abc123def456-1700000000")
        self.assertEqual(post.call_args.args[0], BASE + "/urls")
        self.assertEqual(post.call_args.kwargs["data"], {"url": "https://example.com/x?y=1"})
        self.assertEqual(post.call_args.kwargs["timeout"], vt.REQUEST_TIMEOUT_SECONDS)
        self.assertEqual(post.call_args.kwargs["headers"]["x-apikey"], KEY)

    def test_error_statuses(self):
        for status, exc_type in [(401, vt.VirusTotalAuthError), (403, vt.VirusTotalAuthError),
                                 (429, vt.VirusTotalRateLimitError), (400, vt.VirusTotalInputError),
                                 (503, vt.VirusTotalError)]:
            vt._limiter = vt._MinuteLimiter()
            with mock.patch(POST, return_value=FakeResponse(status, {})):
                with self.assertRaises(exc_type):
                    vt.submit_url("https://example.com/", confirmed=True)

    def test_timeout_and_network_failure(self):
        for raised in (requests.exceptions.Timeout("t"), requests.exceptions.ConnectionError("c")):
            vt._limiter = vt._MinuteLimiter()
            with mock.patch(POST, side_effect=raised):
                with self.assertRaises(vt.VirusTotalNetworkError):
                    vt.submit_url("https://example.com/", confirmed=True)

    def test_malformed_responses(self):
        bad = [FakeResponse(200, None, bad_json=True), FakeResponse(200, {}), FakeResponse(200, {"data": {}}),
               FakeResponse(200, {"data": {"id": 123}}), FakeResponse(200, {"data": {"id": "../../files/x"}}),
               FakeResponse(200, {"data": {"id": "short"}}), FakeResponse(200, [])]
        for resp in bad:
            vt._limiter = vt._MinuteLimiter()
            with mock.patch(POST, return_value=resp):
                with self.assertRaises(vt.VirusTotalError):
                    vt.submit_url("https://example.com/", confirmed=True)

    def test_submissions_count_against_shared_rate_guard(self):
        with mock.patch(GET, return_value=FakeResponse(404, {})):
            for _ in range(vt.PUBLIC_API_PER_MINUTE):
                vt.lookup_url("https://example.com/")
        with mock.patch(POST) as post:
            with self.assertRaises(vt.VirusTotalRateLimitError):
                vt.submit_url("https://example.com/", confirmed=True)
            post.assert_not_called()


class AnalysisTests(ClientBase):
    AID = "u-abc123def456-1700000000"

    def _payload(self, status="completed", stats=None, results=None):
        return {"data": {"attributes": {"status": status, "date": 1760868000,
                                        "stats": stats if stats is not None else {"malicious": 1, "harmless": 5},
                                        "results": results or {"A": {"category": "malicious", "result": "x"}}}}}

    def test_completed(self):
        with mock.patch(GET, return_value=FakeResponse(200, self._payload())) as get:
            a = vt.get_analysis(self.AID)
        self.assertTrue(get.call_args.args[0].endswith("/analyses/" + self.AID))
        self.assertTrue(a.completed)
        self.assertEqual((a.malicious, a.harmless, a.total_engines), (1, 5, 6))
        self.assertEqual(a.results, [("A", "malicious", "x")])

    def test_queued_is_not_completed(self):
        with mock.patch(GET, return_value=FakeResponse(200, self._payload("queued", {}, {}))):
            a = vt.get_analysis(self.AID)
        self.assertFalse(a.completed)
        self.assertEqual(a.total_engines, 0)

    def test_invalid_ids_make_no_request(self):
        for bad in ("", "../files/abc", "a/b", "short", "x" * 300, None, "id with space", "id?x=1&y=2"):
            with mock.patch(GET) as get:
                with self.assertRaises(vt.VirusTotalInputError):
                    vt.get_analysis(bad)
                get.assert_not_called()

    def test_404_is_a_clear_error_not_a_verdict(self):
        with mock.patch(GET, return_value=FakeResponse(404, {})):
            with self.assertRaises(vt.VirusTotalError) as cm:
                vt.get_analysis(self.AID)
        self.assertIn("no analysis", str(cm.exception))

    def test_errors_and_malformed(self):
        for status, exc_type in [(429, vt.VirusTotalRateLimitError), (401, vt.VirusTotalAuthError),
                                 (502, vt.VirusTotalError)]:
            vt._limiter = vt._MinuteLimiter()
            with mock.patch(GET, return_value=FakeResponse(status, {})):
                with self.assertRaises(exc_type):
                    vt.get_analysis(self.AID)
        for payload in (None, {}, {"data": {}}, {"data": {"attributes": {}}},
                        {"data": {"attributes": {"status": 5}}},
                        {"data": {"attributes": {"status": "completed", "stats": "x"}}}):
            vt._limiter = vt._MinuteLimiter()
            with mock.patch(GET, return_value=FakeResponse(200, payload)):
                with self.assertRaises(vt.VirusTotalError):
                    vt.get_analysis(self.AID)


NOW = datetime(2026, 10, 19, 15, 19, 19, tzinfo=timezone.utc)
TS = int(datetime(2026, 10, 19, 10, 19, 19, tzinfo=timezone.utc).timestamp())


class ReportCompositionTests(unittest.TestCase):
    def test_time_helpers(self):
        self.assertEqual(ur.format_utc(TS), "2026-10-19 10:19:19 UTC")
        self.assertEqual(ur.format_utc(None), ur.NOT_RETURNED)
        self.assertEqual(ur.format_utc("x"), ur.NOT_RETURNED)
        self.assertEqual(ur.format_utc(True), ur.NOT_RETURNED)
        self.assertEqual(ur.relative_age(TS, NOW), "5 hours ago")
        self.assertEqual(ur.relative_age(TS + 3600 * 5 + 10, NOW), "")  # future
        self.assertEqual(ur.relative_age(int(NOW.timestamp()) - 3 * 86400, NOW), "3 days ago")
        self.assertEqual(ur.relative_age(int(NOW.timestamp()) - 1, NOW), "moments ago")
        self.assertEqual(ur.relative_age(None, NOW), "")
        self.assertTrue(ur.is_stale(int(NOW.timestamp()) - 31 * 86400, NOW))
        self.assertFalse(ur.is_stale(TS, NOW))
        self.assertFalse(ur.is_stale(None, NOW))

    def _report(self, **kw):
        base = dict(kind="url", identifier="u", found=True, harmless=10, last_analysis_date=TS)
        base.update(kw)
        return vt.VTReport(**base)

    def test_headlines_never_say_safe(self):
        zero = ur.vt_headline(self._report())
        self.assertEqual(zero.tone, "info")
        self.assertIn("not proof", zero.detail)
        self.assertNotIn("safe.", zero.headline.lower().replace("not proof the url is safe", ""))
        bad = ur.vt_headline(self._report(malicious=3, suspicious=1))
        self.assertEqual(bad.tone, "bad")
        self.assertIn("3 of 14", bad.headline)
        self.assertIn("1 as suspicious", bad.headline)
        self.assertEqual(ur.vt_headline(self._report(suspicious=2)).tone, "warn")
        pending = ur.vt_headline(self._report(harmless=0))
        self.assertIn("no vendor results", pending.headline)

    def test_overview_states(self):
        a = analyze_url("https://example.com/")
        cases = {
            ur.VT_NOT_CONFIGURED: "not configured",
            ur.VT_NOT_REQUESTED: "No VirusTotal lookup",
            ur.VT_NOT_FOUND: "no existing report",
        }
        for state, text in cases.items():
            self.assertIn(text, ur.compose_overview(a, state).vt_headline)
        err = ur.compose_overview(a, ur.VT_ERROR, error="Rate limit hit.")
        self.assertIn("failed", err.vt_headline)
        self.assertIn("Rate limit hit.", err.vt_detail)
        self.assertIn("says nothing about the URL", err.vt_detail)

    def test_overview_with_report_is_stale_aware_and_keeps_sources_separate(self):
        a = analyze_url("http://203.0.113.9/login")
        old = int(NOW.timestamp()) - 90 * 86400
        ov = ur.compose_overview(a, ur.VT_REPORT, self._report(last_analysis_date=old), now=NOW)
        self.assertEqual(ov.local_level, a.signal_level)
        self.assertEqual(ov.local_finding_count, len(a.findings))
        self.assertTrue(any("more than 30 days old" in c for c in ov.caveats))
        self.assertTrue(any("not a probability" in c for c in ov.caveats))
        self.assertEqual(ov.vt_tone, "info")  # local signals do not change the VT wording
        undated = ur.compose_overview(a, ur.VT_REPORT, self._report(last_analysis_date=None), now=NOW)
        self.assertTrue(any("did not return an analysis date" in c for c in undated.caveats))

    def test_privacy_notes(self):
        base = ur.submission_privacy_notes("https://example.com/")
        self.assertTrue(any("third-party" in n for n in base))
        self.assertTrue(any("never visits" in n for n in base))
        self.assertFalse(any("query parameters" in n for n in base))
        rich = " ".join(ur.submission_privacy_notes("https://user:pw@example.com/a?token=1#frag"))
        for needle in ("query parameters", "before an '@'", "fragment"):
            self.assertIn(needle, rich)
        self.assertIn("private or local", " ".join(ur.submission_privacy_notes("http://192.168.1.5/x")))
        self.assertIn("internal hostname", " ".join(ur.submission_privacy_notes("http://printer.local/")))
        ur.submission_privacy_notes("http://[bad")  # malformed: must not raise


if __name__ == "__main__":
    unittest.main()
