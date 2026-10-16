import os
import unittest
from unittest import mock

import requests

from backend import openrouter_client as orc
from backend import virustotal_client as vt


class FakeResponse:
    def __init__(self, status=200, payload=None, bad_json=False):
        self.status_code = status
        self._payload = payload
        self._bad = bad_json

    def json(self):
        if self._bad:
            raise ValueError("bad json")
        return self._payload


VT_FILE_OK = {"data": {"id": "abc123", "attributes": {
    "last_analysis_stats": {"malicious": 3, "suspicious": 1, "harmless": 50, "undetected": 20, "timeout": 0},
    "last_analysis_date": 1700000000,
    "last_analysis_results": {
        "EngineB": {"category": "suspicious", "result": "Heur.X"},
        "EngineA": {"category": "malicious", "result": "Trojan.Y"},
        "EngineC": {"category": "harmless", "result": None},
    }}}}
SHA256 = "a" * 64


class VirusTotalTests(unittest.TestCase):
    def setUp(self):
        vt._limiter = vt._MinuteLimiter()
        self.env = mock.patch.dict(os.environ, {"VIRUSTOTAL_API_KEY": "test-key-123"})
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def test_missing_key(self):
        with mock.patch.dict(os.environ, {"VIRUSTOTAL_API_KEY": ""}):
            with mock.patch("backend.virustotal_client.requests.get") as get:
                with self.assertRaises(vt.VirusTotalNotConfiguredError):
                    vt.lookup_hash(SHA256)
                get.assert_not_called()

    def test_invalid_hash_makes_no_request(self):
        with mock.patch("backend.virustotal_client.requests.get") as get:
            with self.assertRaises(vt.VirusTotalInputError):
                vt.lookup_hash("not-a-hash")
            get.assert_not_called()

    def test_success_parsing(self):
        with mock.patch("backend.virustotal_client.requests.get", return_value=FakeResponse(200, VT_FILE_OK)) as get:
            r = vt.lookup_hash(SHA256.upper())
        url = get.call_args.args[0]
        self.assertTrue(url.endswith(f"/files/{SHA256}"))
        self.assertEqual(get.call_args.kwargs["headers"]["x-apikey"], "test-key-123")
        self.assertEqual(get.call_args.kwargs["timeout"], vt.REQUEST_TIMEOUT_SECONDS)
        self.assertTrue(r.found)
        self.assertEqual((r.malicious, r.suspicious, r.harmless, r.undetected), (3, 1, 50, 20))
        self.assertEqual(r.total_engines, 74)
        self.assertEqual(r.flagged_engines[0][0], "EngineA")   # malicious sorted first
        self.assertEqual(len(r.flagged_engines), 2)
        self.assertEqual(r.permalink, "https://www.virustotal.com/gui/file/abc123")
        self.assertFalse(r.pending)

    def test_not_found_is_not_an_error(self):
        with mock.patch("backend.virustotal_client.requests.get", return_value=FakeResponse(404, {})):
            r = vt.lookup_hash(SHA256)
        self.assertFalse(r.found)

    def test_pending_report(self):
        payload = {"data": {"id": "x", "attributes": {"last_analysis_stats": {}}}}
        with mock.patch("backend.virustotal_client.requests.get", return_value=FakeResponse(200, payload)):
            r = vt.lookup_url("https://example.com")
        self.assertTrue(r.pending)

    def test_url_lookup_uses_base64_id(self):
        payload = {"data": {"id": "u", "attributes": {"last_analysis_stats": {"harmless": 1}}}}
        with mock.patch("backend.virustotal_client.requests.get", return_value=FakeResponse(200, payload)) as get:
            vt.lookup_url("http://www.google.com/")
        self.assertTrue(get.call_args.args[0].endswith("/urls/aHR0cDovL3d3dy5nb29nbGUuY29tLw"))

    def test_url_needs_scheme(self):
        with self.assertRaises(vt.VirusTotalInputError):
            vt.lookup_url("example.com")

    def test_http_errors(self):
        cases = [(401, vt.VirusTotalAuthError), (403, vt.VirusTotalAuthError),
                 (429, vt.VirusTotalRateLimitError), (400, vt.VirusTotalInputError),
                 (500, vt.VirusTotalError)]
        for status, exc in cases:
            vt._limiter = vt._MinuteLimiter()
            with mock.patch("backend.virustotal_client.requests.get", return_value=FakeResponse(status, {})):
                with self.assertRaises(exc, msg=str(status)):
                    vt.lookup_hash(SHA256)

    def test_error_messages_never_contain_key(self):
        for status in (401, 429, 500):
            vt._limiter = vt._MinuteLimiter()
            with mock.patch("backend.virustotal_client.requests.get", return_value=FakeResponse(status, {})):
                try:
                    vt.lookup_hash(SHA256)
                except vt.VirusTotalError as e:
                    self.assertNotIn("test-key-123", str(e))

    def test_network_failures(self):
        for raised in (requests.exceptions.Timeout(), requests.exceptions.ConnectionError()):
            vt._limiter = vt._MinuteLimiter()
            with mock.patch("backend.virustotal_client.requests.get", side_effect=raised):
                with self.assertRaises(vt.VirusTotalNetworkError):
                    vt.lookup_hash(SHA256)

    def test_malformed_json(self):
        with mock.patch("backend.virustotal_client.requests.get", return_value=FakeResponse(200, None, bad_json=True)):
            with self.assertRaises(vt.VirusTotalError):
                vt.lookup_hash(SHA256)

    def test_local_rate_guard(self):
        now = [0.0]
        vt._limiter = vt._MinuteLimiter(clock=lambda: now[0])
        with mock.patch("backend.virustotal_client.requests.get", return_value=FakeResponse(404, {})) as get:
            for _ in range(4):
                vt.lookup_hash(SHA256)
            with self.assertRaises(vt.VirusTotalRateLimitError):
                vt.lookup_hash(SHA256)
            self.assertEqual(get.call_count, 4)
            now[0] = 61.0
            vt.lookup_hash(SHA256)
            self.assertEqual(get.call_count, 5)


OK_CHAT = {"choices": [{"message": {"content": "Hello there"}}]}


class OpenRouterTests(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-or-secret-xyz",
                                                "OPENROUTER_MODEL": "test/model"})
        self.env.start()
        self.sleep = mock.patch("backend.openrouter_client.time.sleep")
        self.sleep.start()

    def tearDown(self):
        self.sleep.stop()
        self.env.stop()

    def msgs(self):
        return [{"role": "user", "content": "hi"}]

    def test_missing_key(self):
        with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}):
            with mock.patch("backend.openrouter_client.requests.post") as post:
                with self.assertRaises(orc.OpenRouterNotConfiguredError):
                    orc.chat_completion(self.msgs())
                post.assert_not_called()

    def test_success_and_request_shape(self):
        with mock.patch("backend.openrouter_client.requests.post", return_value=FakeResponse(200, OK_CHAT)) as post:
            self.assertEqual(orc.chat_completion(self.msgs()), "Hello there")
        kwargs = post.call_args.kwargs
        self.assertEqual(kwargs["json"]["model"], "test/model")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer sk-or-secret-xyz")
        self.assertEqual(kwargs["timeout"], orc.REQUEST_TIMEOUT_SECONDS)
        self.assertTrue(post.call_args.args[0].endswith("/chat/completions"))

    def test_strips_think_blocks(self):
        payload = {"choices": [{"message": {"content": "<think>secret plan</think>Answer"}}]}
        with mock.patch("backend.openrouter_client.requests.post", return_value=FakeResponse(200, payload)):
            self.assertEqual(orc.chat_completion(self.msgs()), "Answer")

    def test_status_errors(self):
        cases = [(429, orc.OpenRouterRateLimitError), (401, orc.OpenRouterError),
                 (400, orc.OpenRouterError), (503, orc.OpenRouterError)]
        for status, exc in cases:
            with mock.patch("backend.openrouter_client.requests.post", return_value=FakeResponse(status, {})):
                with self.assertRaises(exc, msg=str(status)):
                    orc.chat_completion(self.msgs())

    def test_429_not_retried(self):
        with mock.patch("backend.openrouter_client.requests.post", return_value=FakeResponse(429, {})) as post:
            with self.assertRaises(orc.OpenRouterRateLimitError):
                orc.chat_completion(self.msgs())
        self.assertEqual(post.call_count, 1)

    def test_5xx_retried_once_then_fails(self):
        with mock.patch("backend.openrouter_client.requests.post", return_value=FakeResponse(503, {})) as post:
            with self.assertRaises(orc.OpenRouterError):
                orc.chat_completion(self.msgs())
        self.assertEqual(post.call_count, orc.MAX_RETRIES + 1)

    def test_timeout_after_retries(self):
        with mock.patch("backend.openrouter_client.requests.post", side_effect=requests.exceptions.Timeout()) as post:
            with self.assertRaises(orc.OpenRouterTimeoutError):
                orc.chat_completion(self.msgs())
        self.assertEqual(post.call_count, orc.MAX_RETRIES + 1)

    def test_bad_shapes(self):
        for resp in (FakeResponse(200, {"nope": 1}), FakeResponse(200, None, bad_json=True),
                     FakeResponse(200, {"choices": [{"message": {"content": "  "}}]})):
            with mock.patch("backend.openrouter_client.requests.post", return_value=resp):
                with self.assertRaises(orc.OpenRouterResponseError):
                    orc.chat_completion(self.msgs())

    def test_errors_never_leak_key(self):
        for status in (401, 429, 500):
            with mock.patch("backend.openrouter_client.requests.post", return_value=FakeResponse(status, {})):
                try:
                    orc.chat_completion(self.msgs())
                except orc.OpenRouterError as e:
                    self.assertNotIn("sk-or-secret-xyz", str(e))


if __name__ == "__main__":
    unittest.main()
