import os
import unittest


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()

from unittest import mock

import app_registry as reg
from backend import openrouter_client as orc
from cyberguide import engine
from cyberguide.knowledge_base import load_sections, parse_sections, retrieve


class KnowledgeSyncTests(unittest.TestCase):
    def setUp(self):
        self.text = _read("knowledge.md")
        self.sections = load_sections()

    def test_every_implemented_module_is_documented(self):
        for m in reg.implemented():
            self.assertIn(m.title, self.text, f"{m.title} missing from knowledge.md")

    def test_planned_modules_are_labeled_planned(self):
        planned_section = next(s for s in self.sections if s.title == "Planned features")
        for m in reg.planned():
            self.assertIn(m.title, planned_section.body, m.title)
        registry = next(s for s in self.sections if s.title == "Feature registry")
        self.assertIn("Planned", registry.body)

    def test_planned_not_in_implemented_list(self):
        registry = next(s for s in self.sections if s.title == "Feature registry")
        implemented_line = registry.body.split("\n")[0]
        for m in reg.planned():
            self.assertNotIn(m.title, implemented_line)

    def test_page_links_point_to_real_implemented_pages(self):
        for s in self.sections:
            if s.page:
                self.assertIn(s.page, reg.implemented_keys(), f"{s.title} -> {s.page}")

    def test_registry_matches_view_files_and_router(self):
        for key in reg.implemented_keys():
            self.assertTrue(os.path.exists(f"views/{key}.py"), key)
        src = _read("streamlit_app.py")
        for key in reg.implemented_keys():
            self.assertIn(f'"{key}":', src)

    def test_env_var_names_documented_match_code(self):
        for name in ("OPENROUTER_API_KEY", "VIRUSTOTAL_API_KEY"):
            self.assertIn(name, self.text)
            self.assertIn(name, _read("config.py"))

    def test_unsupported_formats_not_claimed(self):
        # PDF export / frames are described only as not implemented.
        limits = next(s for s in self.sections if s.title == "QR code limitations")
        self.assertIn("not implemented", limits.body)


class RetrievalTests(unittest.TestCase):
    def top(self, q):
        return [s.title for s in retrieve(q, k=2)]

    def test_core_questions(self):
        self.assertIn("How to generate a QR code", self.top("How do I generate a QR code?"))
        self.assertIn("How to analyze a suspicious URL", self.top("How do I analyze a suspicious website?"))
        self.assertIn("Troubleshooting: VirusTotal is not working", self.top("Why is VirusTotal not working?"))
        self.assertIn("How to interpret a VirusTotal report", self.top("How do I interpret a VirusTotal report?"))
        self.assertIn("How to configure OpenRouter for CyberGuide AI", self.top("How do I configure the OpenRouter API key?"))

    def test_no_match_returns_empty(self):
        self.assertEqual(retrieve("zzzz qqqq"), [])
        self.assertEqual(retrieve(""), [])

    def test_parse_sections_page_marker(self):
        s = parse_sections("# T\n\n## A\nbody\nPage: qr_generator\n\n## B\nother")
        self.assertEqual((s[0].title, s[0].page, s[1].page), ("A", "qr_generator", None))
        self.assertNotIn("Page:", s[0].body)


class EngineTests(unittest.TestCase):
    def test_no_key_falls_back_to_documentation_and_says_why(self):
        with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}):
            with mock.patch("backend.openrouter_client.requests.post") as post:
                a = engine.answer("How do I generate a QR code?", status={"openrouter": False})
                post.assert_not_called()
        self.assertEqual(a.source, "documentation")
        self.assertIn("not configured", a.notice)
        self.assertIn("qr_generator", a.pages)
        self.assertIn("Open QR Code Generator", a.text)

    def test_ai_error_falls_back_with_reason(self):
        with mock.patch("cyberguide.engine.orc.chat_completion", side_effect=orc.OpenRouterRateLimitError("rate limited")):
            a = engine.answer("How do I hash a file?")
        self.assertEqual(a.source, "documentation")
        self.assertIn("rate limited", a.notice)

    def test_ai_answer_labeled_ai_and_prompt_contains_docs_and_status(self):
        captured = {}

        def fake_chat(messages, **kw):
            captured["messages"] = messages
            return "Step 1..."

        with mock.patch("cyberguide.engine.orc.chat_completion", side_effect=fake_chat):
            a = engine.answer("Why is VirusTotal not working?", status={"openrouter": True, "virustotal": False})
        self.assertEqual(a.source, "ai")
        system = captured["messages"][0]["content"]
        self.assertIn("VIRUSTOTAL_API_KEY detected: False", system)
        self.assertIn("VIRUSTOTAL_API_KEY", system)
        self.assertIn("cannot run scans", system)
        self.assertEqual(captured["messages"][-1]["role"], "user")

    def test_secrets_are_redacted_before_sending_and_user_warned(self):
        captured = {}

        def fake_chat(messages, **kw):
            captured["messages"] = messages
            return "ok"

        with mock.patch("cyberguide.engine.orc.chat_completion", side_effect=fake_chat):
            a = engine.answer("my key sk-or-v1-abcdefghijklmnopqrstuv is not working")
        sent = " ".join(m["content"] for m in captured["messages"])
        self.assertNotIn("abcdefghijklmnop", sent)
        self.assertIn("rotate", a.notice)

    def test_input_is_clipped(self):
        captured = {}

        def fake_chat(messages, **kw):
            captured["messages"] = messages
            return "ok"

        with mock.patch("cyberguide.engine.orc.chat_completion", side_effect=fake_chat):
            engine.answer("qr " * 2000)
        self.assertLessEqual(len(captured["messages"][-1]["content"]), 1000)

    def test_history_is_bounded(self):
        captured = {}

        def fake_chat(messages, **kw):
            captured["messages"] = messages
            return "ok"

        history = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"m{i}"} for i in range(40)]
        with mock.patch("cyberguide.engine.orc.chat_completion", side_effect=fake_chat):
            engine.answer("qr code", history=history)
        self.assertLessEqual(len(captured["messages"]), 1 + engine.MAX_HISTORY_TURNS + 1)

    def test_unknown_topic_without_docs(self):
        with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}):
            a = engine.answer("zzzz qqqq")
        self.assertIn("couldn't find", a.text)

    def test_prompt_forbids_claiming_execution_and_safety_verdicts(self):
        p = engine.SYSTEM_PROMPT
        self.assertIn("Never say or imply that you did", p)
        self.assertIn("Never say a URL, file, or QR code is safe or malicious", p)


class ConfigTests(unittest.TestCase):
    def test_service_status_returns_booleans_only(self):
        import config
        with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-or-zzz", "VIRUSTOTAL_API_KEY": ""}):
            status = config.service_status()
        self.assertEqual(status, {"openrouter": True, "virustotal": False})
        self.assertNotIn("sk-or-zzz", repr(status))


if __name__ == "__main__":
    unittest.main()
