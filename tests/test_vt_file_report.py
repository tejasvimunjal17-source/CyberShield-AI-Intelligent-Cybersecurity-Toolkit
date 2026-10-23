"""Part 7 backend tests. All VirusTotal traffic is mocked; no API key is needed."""

import hashlib
import io
import logging
import os
import unittest
from datetime import datetime, timezone
from unittest import mock

import requests

from backend import file_report as fr
from backend import virustotal_client as vt
from backend.file_hashing import FileTooLargeError, hash_bytes, hash_stream
from tests.test_vt_url_report import BASE, GET, KEY, POST, FakeResponse

SHA256 = hashlib.sha256(b"hello").hexdigest()
SHA1 = hashlib.sha1(b"hello").hexdigest()
MD5 = hashlib.md5(b"hello").hexdigest()
AID = "MDEyMzQ1Njc4OWFiY2RlZg=="  # file-analysis ids are base64-like and may end with '='

FILE_REPORT = {"data": {"id": SHA256, "attributes": {
    "last_analysis_stats": {"malicious": 3, "suspicious": 1, "harmless": 0, "undetected": 60,
                            "timeout": 0, "type-unsupported": 5},
    "last_analysis_date": 1760868000,
    "last_analysis_results": {
        "Zeta": {"category": "undetected", "result": None},
        "Beta": {"category": "suspicious", "result": "Heur.Gen"},
        "Alpha": {"category": "malicious", "result": "Trojan.Evil"},
    },
    "type_description": "Win32 EXE", "size": 123456, "magic": "PE32 executable",
    "meaningful_name": "setup.exe", "names": ["setup.exe", "a.exe", ""],
    "sha256": SHA256.upper(), "sha1": SHA1, "md5": MD5,
    "tags": ["peexe", "overlay"], "reputation": -4, "times_submitted": 77,
    "first_submission_date": 1355216161, "last_submission_date": 1760868000,
    "popular_threat_classification": {
        "suggested_threat_label": "trojan.evil/gen",
        "popular_threat_name": [{"value": "evil", "count": 9}, {"value": "", "count": 1}, "junk"],
    },
    "title": "must be ignored for files", "last_final_url": "http://ignored/",
}}}


class Base(unittest.TestCase):
    def setUp(self):
        vt._limiter = vt._MinuteLimiter()
        self.env = mock.patch.dict(os.environ, {"VIRUSTOTAL_API_KEY": KEY})
        self.env.start()

    def tearDown(self):
        self.env.stop()


class LocalHashingTests(unittest.TestCase):
    def test_all_three_digests_match_hashlib_on_binary_multi_chunk_data(self):
        data = bytes(range(256)) * (4 * 4096) + b"\x00\xff\x01"   # > 1 MiB, not text
        r = hash_stream(io.BytesIO(data))
        self.assertEqual(r.sha256, hashlib.sha256(data).hexdigest())
        self.assertEqual(r.sha1, hashlib.sha1(data).hexdigest())
        self.assertEqual(r.md5, hashlib.md5(data).hexdigest())
        self.assertEqual(r.size, len(data))

    def test_empty_input_hashes_the_empty_string(self):
        r = hash_bytes(b"")
        self.assertEqual((r.size, r.md5), (0, "d41d8cd98f00b204e9800998ecf8427e"))
        self.assertEqual(r.sha256, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")

    def test_size_limit_boundary(self):
        self.assertEqual(hash_bytes(b"x" * 50, max_bytes=50).size, 50)
        with self.assertRaises(FileTooLargeError):
            hash_bytes(b"x" * 51, max_bytes=50)

    def test_oversize_stops_reading_early(self):
        class Endless:
            reads = 0
            def read(self, n):
                Endless.reads += 1
                return b"x" * n
        with self.assertRaises(FileTooLargeError):
            hash_stream(Endless(), max_bytes=3 * 1024 * 1024)
        self.assertLessEqual(Endless.reads, 5)

    def test_hash_stream_reads_from_current_position(self):
        # Documents why the view must rewind uploaded files before hashing.
        s = io.BytesIO(b"hello")
        s.read()
        self.assertEqual(hash_stream(s).size, 0)
        s.seek(0)
        self.assertEqual(hash_stream(s).sha256, SHA256)


class FileReportParsingTests(Base):
    def test_full_file_report(self):
        with mock.patch(GET, return_value=FakeResponse(200, FILE_REPORT)) as get:
            r = vt.lookup_hash(SHA256)
        self.assertTrue(get.call_args.args[0].endswith("/files/" + SHA256))
        self.assertEqual((r.malicious, r.suspicious, r.harmless, r.undetected, r.timeout), (3, 1, 0, 60, 0))
        self.assertEqual(r.total_engines, 64)  # 'type-unsupported' is not counted as an engine verdict
        self.assertEqual((r.file_type, r.file_size, r.magic), ("Win32 EXE", 123456, "PE32 executable"))
        self.assertEqual((r.meaningful_name, r.names), ("setup.exe", ["setup.exe", "a.exe"]))
        self.assertEqual((r.sha256, r.sha1, r.md5), (SHA256, SHA1, MD5))  # lower-cased and validated
        self.assertEqual((r.tags, r.reputation, r.times_submitted), (["peexe", "overlay"], -4, 77))
        self.assertEqual((r.first_submission_date, r.last_submission_date), (1355216161, 1760868000))
        self.assertEqual(r.threat_label, "trojan.evil/gen")
        self.assertEqual(r.threat_names, ["evil"])
        self.assertEqual([x[0] for x in r.all_results], ["Alpha", "Beta", "Zeta"])
        self.assertTrue(r.permalink.endswith("/gui/file/" + SHA256))

    def test_url_only_fields_stay_empty_for_files(self):
        with mock.patch(GET, return_value=FakeResponse(200, FILE_REPORT)):
            r = vt.lookup_hash(SHA256)
        self.assertEqual((r.title, r.final_url, r.redirection_chain, r.categories, r.content_type), ("", "", [], [], ""))
        self.assertIsNone(r.http_status)

    def test_missing_fields_are_empty_never_invented(self):
        with mock.patch(GET, return_value=FakeResponse(200, {"data": {"id": "x", "attributes": {
                "last_analysis_stats": {"harmless": 2}}}})):
            r = vt.lookup_hash(SHA256)
        self.assertEqual((r.file_type, r.magic, r.meaningful_name, r.threat_label), ("", "", "", ""))
        self.assertEqual((r.file_size, r.first_submission_date, r.reputation), (None, None, None))
        self.assertEqual((r.sha256, r.names, r.tags, r.all_results), ("", [], [], []))

    def test_wrong_types_are_tolerated(self):
        weird = {"data": {"id": "x", "attributes": {
            "last_analysis_stats": {"malicious": 1}, "size": "big", "type_description": 5,
            "names": "nope", "tags": {"a": 1}, "sha256": "not-hex" * 9, "sha1": 7, "md5": "G" * 32,
            "popular_threat_classification": ["x"], "reputation": 1.5, "times_submitted": True}}}
        with mock.patch(GET, return_value=FakeResponse(200, weird)):
            r = vt.lookup_hash(SHA256)
        self.assertIsNone(r.file_size)
        self.assertIsNone(r.reputation)
        self.assertIsNone(r.times_submitted)
        self.assertEqual((r.sha256, r.sha1, r.md5, r.names, r.tags), ("", "", "", [], []))
        self.assertEqual((r.threat_label, r.threat_names), ("", []))

    def test_malformed_payloads_raise_safe_errors(self):
        for payload in (None, {}, {"data": []}, {"data": {"attributes": [1]}},
                        {"data": {"attributes": {"last_analysis_stats": "x"}}}):
            with mock.patch(GET, return_value=FakeResponse(200, payload)):
                with self.assertRaises(vt.VirusTotalError):
                    vt.lookup_hash(SHA256)
        with mock.patch(GET, return_value=FakeResponse(200, None, bad_json=True)):
            with self.assertRaises(vt.VirusTotalError):
                vt.lookup_hash(SHA256)

    def test_no_report_is_not_clean(self):
        with mock.patch(GET, return_value=FakeResponse(404, {})):
            r = vt.lookup_hash(SHA256)
        self.assertFalse(r.found)
        self.assertEqual(r.total_engines, 0)

    def test_errors_timeouts_and_missing_key(self):
        for status, exc in [(401, vt.VirusTotalAuthError), (429, vt.VirusTotalRateLimitError),
                            (500, vt.VirusTotalError)]:
            vt._limiter = vt._MinuteLimiter()
            with mock.patch(GET, return_value=FakeResponse(status, {})):
                with self.assertRaises(exc) as cm:
                    vt.lookup_hash(SHA256)
            self.assertNotIn(KEY, str(cm.exception))
        vt._limiter = vt._MinuteLimiter()
        with mock.patch(GET, side_effect=requests.exceptions.Timeout()):
            with self.assertRaises(vt.VirusTotalNetworkError):
                vt.lookup_hash(SHA256)
        with mock.patch.dict(os.environ, {"VIRUSTOTAL_API_KEY": ""}):
            with mock.patch(GET) as get:
                with self.assertRaises(vt.VirusTotalNotConfiguredError):
                    vt.lookup_hash(SHA256)
                get.assert_not_called()


class SubmitFileTests(Base):
    DATA = b"MZ\x90\x00 secret-marker-9f3a"

    def test_refuses_without_explicit_confirmation(self):
        for kwargs in ({}, {"confirmed": False}, {"confirmed": "yes"}, {"confirmed": 1}, {"confirmed": None}):
            with mock.patch(POST) as post:
                with self.assertRaises(vt.VirusTotalInputError):
                    vt.submit_file(self.DATA, **kwargs)
                post.assert_not_called()

    def test_missing_key_makes_no_request(self):
        with mock.patch.dict(os.environ, {"VIRUSTOTAL_API_KEY": ""}):
            with mock.patch(POST) as post:
                with self.assertRaises(vt.VirusTotalNotConfiguredError):
                    vt.submit_file(self.DATA, confirmed=True)
                post.assert_not_called()

    def test_rejects_bad_content_without_a_request(self):
        for bad in ("text", None, 123, b"", bytearray()):
            with mock.patch(POST) as post:
                with self.assertRaises(vt.VirusTotalInputError):
                    vt.submit_file(bad, confirmed=True)
                post.assert_not_called()

    def test_oversize_is_refused_without_a_request(self):
        with mock.patch.object(vt, "VT_MAX_UPLOAD_BYTES", 10):
            with mock.patch(POST) as post:
                with self.assertRaises(vt.VirusTotalInputError) as cm:
                    vt.submit_file(b"x" * 11, confirmed=True)
                post.assert_not_called()
            self.assertIn("direct-upload limit", str(cm.exception))
            with mock.patch(POST, return_value=FakeResponse(200, {"data": {"id": AID}})):
                self.assertEqual(vt.submit_file(b"x" * 10, confirmed=True).analysis_id, AID)  # boundary ok

    def test_app_limit_is_not_above_virustotals_ceiling(self):
        self.assertLessEqual(fr.UPLOAD_LIMIT_BYTES, vt.VT_MAX_UPLOAD_BYTES)

    def test_success_uploads_once_to_configured_base_only(self):
        with mock.patch(POST, return_value=FakeResponse(200, {"data": {"id": AID, "type": "analysis"}})) as post:
            result = vt.submit_file(self.DATA, confirmed=True)
        self.assertEqual(result.analysis_id, AID)
        self.assertEqual(post.call_count, 1)
        self.assertEqual(post.call_args.args[0], BASE + "/files")
        kw = post.call_args.kwargs
        self.assertEqual(kw["files"], {"file": ("sample", self.DATA)})
        self.assertNotIn("data", kw)
        self.assertEqual(kw["timeout"], vt.UPLOAD_TIMEOUT_SECONDS)
        self.assertEqual(kw["headers"]["x-apikey"], KEY)

    def test_original_file_name_is_never_sent(self):
        for risky in ("../../etc/Resume Jane Doe.pdf", "Q3 payroll.xlsx", "naïve.txt", "a" * 100, "", None, 5):
            vt._limiter = vt._MinuteLimiter()
            with mock.patch(POST, return_value=FakeResponse(200, {"data": {"id": AID}})) as post:
                vt.submit_file(self.DATA, confirmed=True, filename=risky)
            self.assertEqual(post.call_args.kwargs["files"]["file"][0], "sample", risky)
        vt._limiter = vt._MinuteLimiter()
        with mock.patch(POST, return_value=FakeResponse(200, {"data": {"id": AID}})) as post:
            vt.submit_file(self.DATA, confirmed=True, filename="report-1.bin")
        self.assertEqual(post.call_args.kwargs["files"]["file"][0], "report-1.bin")

    def test_error_statuses_map_to_specific_safe_errors(self):
        cases = [(401, vt.VirusTotalAuthError), (403, vt.VirusTotalAuthError),
                 (429, vt.VirusTotalRateLimitError), (400, vt.VirusTotalInputError),
                 (413, vt.VirusTotalInputError), (503, vt.VirusTotalError)]
        for status, exc_type in cases:
            vt._limiter = vt._MinuteLimiter()
            with mock.patch(POST, return_value=FakeResponse(status, {})):
                with self.assertRaises(exc_type) as cm:
                    vt.submit_file(self.DATA, confirmed=True)
            self.assertNotIn(KEY, str(cm.exception))
            self.assertNotIn("secret-marker", str(cm.exception))
        vt._limiter = vt._MinuteLimiter()
        with mock.patch(POST, return_value=FakeResponse(413, {})):
            with self.assertRaises(vt.VirusTotalInputError) as cm:
                vt.submit_file(self.DATA, confirmed=True)
        self.assertIn("too large", str(cm.exception))

    def test_timeout_and_network_failure(self):
        for raised in (requests.exceptions.Timeout("t"),
                       requests.exceptions.ConnectionError(f"boom {KEY} secret-marker-9f3a")):
            vt._limiter = vt._MinuteLimiter()
            with mock.patch(POST, side_effect=raised):
                with self.assertRaises(vt.VirusTotalNetworkError) as cm:
                    vt.submit_file(self.DATA, confirmed=True)
            self.assertNotIn(KEY, str(cm.exception))
            self.assertNotIn("secret-marker", str(cm.exception))

    def test_malformed_responses(self):
        bad = [FakeResponse(200, None, bad_json=True), FakeResponse(200, {}), FakeResponse(200, {"data": {}}),
               FakeResponse(200, {"data": {"id": 5}}), FakeResponse(200, {"data": {"id": "../x/y/zzzz"}}),
               FakeResponse(200, {"data": {"id": "short"}}), FakeResponse(200, [])]
        for resp in bad:
            vt._limiter = vt._MinuteLimiter()
            with mock.patch(POST, return_value=resp):
                with self.assertRaises(vt.VirusTotalError):
                    vt.submit_file(self.DATA, confirmed=True)

    def test_uploads_count_against_the_shared_rate_guard(self):
        with mock.patch(GET, return_value=FakeResponse(404, {})):
            for _ in range(vt.PUBLIC_API_PER_MINUTE):
                vt.lookup_hash(SHA256)
        with mock.patch(POST) as post:
            with self.assertRaises(vt.VirusTotalRateLimitError):
                vt.submit_file(self.DATA, confirmed=True)
            post.assert_not_called()

    def test_content_and_key_are_never_logged(self):
        records = []

        class Grab(logging.Handler):
            def emit(self, record):
                records.append(record.getMessage())

        logger = logging.getLogger("backend.virustotal_client")
        handler = Grab(level=logging.DEBUG)
        old_level = logger.level
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        try:
            for status in (200, 401, 429, 500):
                vt._limiter = vt._MinuteLimiter()
                resp = FakeResponse(status, {"data": {"id": AID}})
                with mock.patch(POST, return_value=resp):
                    try:
                        vt.submit_file(self.DATA, confirmed=True)
                    except vt.VirusTotalError:
                        pass
        finally:
            logger.removeHandler(handler)
            logger.setLevel(old_level)
        joined = " ".join(records)
        self.assertNotIn("secret-marker", joined)
        self.assertNotIn(KEY, joined)

    def test_file_analysis_status_uses_the_same_polling_client(self):
        payload = {"data": {"attributes": {"status": "completed", "date": 1760868000,
                                           "stats": {"malicious": 2, "undetected": 60},
                                           "results": {"A": {"category": "malicious", "result": "x"}}}}}
        with mock.patch(GET, return_value=FakeResponse(200, payload)) as get:
            a = vt.get_analysis(AID)
        self.assertTrue(get.call_args.args[0].endswith("/analyses/" + AID))
        self.assertTrue(a.completed)
        self.assertEqual(a.total_engines, 62)


NOW = datetime(2026, 10, 19, 15, 19, 19, tzinfo=timezone.utc)
TS = int(datetime(2026, 10, 19, 10, 19, 19, tzinfo=timezone.utc).timestamp())


def _report(**kw):
    base = dict(kind="file", identifier=SHA256, found=True, harmless=10, last_analysis_date=TS,
                sha256=SHA256)
    base.update(kw)
    return vt.VTReport(**base)


class FileReportLogicTests(unittest.TestCase):
    def test_headlines_never_say_safe(self):
        zero = fr.file_headline(_report())
        self.assertEqual(zero.tone, "info")
        self.assertIn("not proof", zero.detail)
        self.assertIn("this file", zero.headline)
        bad = fr.file_headline(_report(malicious=3, suspicious=1))
        self.assertEqual(bad.tone, "bad")
        self.assertIn("3 of 14", bad.headline)
        self.assertIn("1 as suspicious", bad.headline)
        self.assertEqual(fr.file_headline(_report(suspicious=2)).tone, "warn")
        self.assertIn("no vendor results", fr.file_headline(_report(harmless=0)).headline)

    def test_overview_states_distinguish_missing_failed_and_clean(self):
        texts = {fr.VT_NOT_CONFIGURED: "not configured", fr.VT_NOT_REQUESTED: "No VirusTotal lookup",
                 fr.VT_NOT_FOUND: "no existing report"}
        for state, text in texts.items():
            self.assertIn(text, fr.compose_overview(state).vt_headline)
        nf = fr.compose_overview(fr.VT_NOT_FOUND)
        self.assertIn("not a verdict", nf.vt_detail)
        self.assertNotIn("clean", (nf.vt_headline + nf.vt_detail).lower())
        err = fr.compose_overview(fr.VT_ERROR, error="Rate limit hit.")
        self.assertIn("failed", err.vt_headline)
        self.assertIn("says nothing about the file", err.vt_detail)
        self.assertTrue(any("exact bytes" in c for c in nf.caveats))

    def test_stale_and_undated_reports(self):
        old = int(NOW.timestamp()) - 90 * 86400
        ov = fr.compose_overview(fr.VT_REPORT, _report(last_analysis_date=old), queried_hash=SHA256, now=NOW)
        self.assertTrue(any("more than 30 days old" in c for c in ov.caveats))
        undated = fr.compose_overview(fr.VT_REPORT, _report(last_analysis_date=None), queried_hash=SHA256, now=NOW)
        self.assertTrue(any("did not return an analysis date" in c for c in undated.caveats))
        fresh = fr.compose_overview(fr.VT_REPORT, _report(), queried_hash=SHA256, now=NOW)
        self.assertEqual(fresh.last_analysis_age, "5 hours ago")
        self.assertFalse(any("30 days" in c for c in fresh.caveats))

    def test_hash_match_cross_check(self):
        self.assertTrue(fr.hash_match_status(_report(), SHA256))
        self.assertTrue(fr.hash_match_status(_report(md5=MD5), MD5.upper()))
        self.assertFalse(fr.hash_match_status(_report(), "a" * 64))
        self.assertIsNone(fr.hash_match_status(_report(sha256=""), SHA256))   # nothing returned to compare
        self.assertIsNone(fr.hash_match_status(None, SHA256))
        self.assertIsNone(fr.hash_match_status(vt.VTReport(kind="file", identifier="x", found=False), SHA256))
        self.assertIsNone(fr.hash_match_status(_report(), "not-a-hash"))

    def test_mismatch_adds_a_warning(self):
        ov = fr.compose_overview(fr.VT_REPORT, _report(), queried_hash="b" * 64, now=NOW)
        self.assertTrue(any(c.startswith("WARNING") for c in ov.caveats))

    def test_upload_blocker_boundaries(self):
        self.assertIn("empty", fr.upload_blocker(0))
        self.assertEqual(fr.upload_blocker(1), "")
        self.assertEqual(fr.upload_blocker(fr.UPLOAD_LIMIT_BYTES), "")
        self.assertIn("above", fr.upload_blocker(fr.UPLOAD_LIMIT_BYTES + 1))

    def test_upload_privacy_notes_cover_required_points(self):
        text = " ".join(fr.upload_privacy_notes(2048)).lower()
        for needle in ("third-party", "security community", "2.0 kb", "personal", "cannot be taken back",
                       "file name is not sent", "never executed", "quota"):
            self.assertIn(needle, text, needle)


if __name__ == "__main__":
    unittest.main()
