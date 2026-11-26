"""Cyber Hygiene (Phase 1): content, page rendering, navigation integration, CyberGuide docs.

Run against tests/fake_streamlit.py, a recording stand-in. These checks show what the app asks
Streamlit to render and how the Python control flow behaves. They do NOT show how the page
looks in a real browser, and they do not open the documentation links.
"""

import ast
import importlib
import re
import sys
import unittest
from unittest import mock

import numpy  # noqa: F401  (import before the harness patches sys.modules, so this module also runs alone)

import app_registry as reg
from components import nav_state
from content.cyber_hygiene import (DOCS_CHECKED, GENERAL_NOTE, OFFICIAL_HOSTS, SECTIONS, Doc,
                                   Item, OsSection)
from cyberguide.knowledge_base import load_sections, retrieve
from tests.fake_streamlit import FakeStreamlit

# Every documentation URL the page may use. Each was found on the vendor's own help site by
# web search on 2026-11-25. A new link must be opened and added here by a person: this set is
# the guard against invented links.
VERIFIED_URLS = frozenset({
    # Google
    "https://support.google.com/android/answer/7680439",
    "https://support.google.com/accounts/answer/46526",
    "https://support.google.com/android/answer/9431959",
    "https://support.google.com/googleplay/answer/2812853",
    "https://support.google.com/android/answer/9079129",
    "https://support.google.com/accounts/answer/185839",
    "https://support.google.com/android/answer/3265955",
    # Microsoft
    "https://support.microsoft.com/en-us/windows/windows-update-faq-8a903416-6f45-0718-f5c7-375e92dddeb2",
    "https://support.microsoft.com/en-us/help/17464",
    "https://support.microsoft.com/en-us/help/4028017",
    "https://support.microsoft.com/en-us/help/4502379",
    "https://support.microsoft.com/help/4026923",
    "https://support.microsoft.com/en-us/windows/protect-yourself-from-phishing-0c7ea947-ba98-3bd9-7184-430e1f860a44",
    "https://support.microsoft.com/en-us/windows/back-up-and-restore-with-windows-backup-87a81f8a-78fa-456e-b521-ac0560e32338",
    # Apple
    "https://support.apple.com/118575",
    "https://support.apple.com/guide/iphone/iph14a867ae/ios",   # seen only as an Apple URL cited in another page
    "https://support.apple.com/102660",
    "https://support.apple.com/guide/iphone/control-access-to-information-in-apps-iph251e92810/ios",
    "https://support.apple.com/guide/icloud/locate-a-device-mmfc0f2442/icloud",
    "https://support.apple.com/guide/personal-safety/ips327569a75/web",
    "https://support.apple.com/102568",
    "https://support.apple.com/guide/personal-safety/ips4930e3486/web",
    "https://support.apple.com/guide/mac-help/mh11785/mac",
    "https://support.apple.com/guide/mac-help/mh11783/mac",
    "https://support.apple.com/102445",
    "https://support.apple.com/guide/security/sec469d47bd8/web",
    "https://support.apple.com/guide/mac-help/flvlt003",
    "https://support.apple.com/104984",
})

REQUIRED_TOPICS = {
    "android": ("keep android updated", "google play", "permissions", "play protect", "screen lock", "2-step verification",
                "apk", "accessibility", "public wi-fi", "find hub", "google account", "suspicious"),
    "windows": ("windows update", "defender antivirus", "firewall", "windows security", "windows hello", "bitlocker",
                "device encryption", "cracked", "trusted", "standard account", "phishing", "backup", "automatic"),
    "ios": ("update", "face id", "touch id", "passcode", "two-factor", "permissions", "find my",
            "configuration profile", "safari", "links", "app store", "devices", "automatic"),
    "macos": ("update", "filevault", "firewall", "gatekeeper", "xprotect", "permissions", "password",
              "two-factor", "configuration profile", "time machine", "phishing", "download"),
}


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _section_text(section):
    parts = [section.intro, section.notice]
    for i in section.items:
        parts += [i.title, i.what, i.why, i.tip, i.note, *i.steps]
    return " ".join(parts).lower()


class ContentTests(unittest.TestCase):
    def test_four_sections_in_the_required_order(self):
        self.assertEqual([s.title for s in SECTIONS],
                         ["Android Security", "Windows Security", "iOS Security", "macOS Security"])
        self.assertEqual([s.key for s in SECTIONS], ["android", "windows", "ios", "macos"])

    def test_every_requested_topic_is_covered(self):
        for section in SECTIONS:
            text = _section_text(section)
            for needle in REQUIRED_TOPICS[section.key]:
                self.assertIn(needle, text, f"{section.key}: {needle}")

    def test_every_item_has_what_why_steps_tip(self):
        for section in SECTIONS:
            keys = [i.key for i in section.items]
            self.assertEqual(len(keys), len(set(keys)), section.key)
            for i in section.items:
                for field in (i.title, i.what, i.why, i.tip):
                    self.assertTrue(field.strip(), f"{section.key}/{i.key}")
                self.assertGreaterEqual(len(i.steps), 3, f"{section.key}/{i.key}")
                self.assertTrue(all(s.strip() for s in i.steps))

    def test_links_are_https_official_and_verified(self):
        for section in SECTIONS:
            for i in section.items:
                if i.doc is None:
                    continue
                url = i.doc.url
                self.assertTrue(url.startswith("https://"), url)
                host = url.split("/")[2]
                self.assertIn(host, OFFICIAL_HOSTS, url)
                self.assertIn(url, VERIFIED_URLS, f"{section.key}/{i.key}: unverified link {url}")
                self.assertNotIn(" ", url)

    def test_no_two_link_buttons_in_a_section_share_label_and_url(self):
        # Streamlit raises a duplicate-widget error for identical buttons.
        for section in SECTIONS:
            pairs = [(i.doc.label, i.doc.url) for i in section.items if i.doc]
            self.assertEqual(len(pairs), len(set(pairs)), section.key)
            self.assertEqual(len([l for l, _ in pairs]), len({l for l, _ in pairs}), section.key)

    def test_missing_link_is_rare_explained_and_not_invented(self):
        missing = [(s.key, i.key) for s in SECTIONS for i in s.items if i.doc is None]
        self.assertEqual(missing, [("android", "public_wifi")])
        item = next(i for i in SECTIONS[0].items if i.key == "public_wifi")
        self.assertIn("No dedicated official", item.note)

    def test_windows_10_end_of_support_is_stated_and_antivirus_is_not_oversold(self):
        win = next(s for s in SECTIONS if s.key == "windows")
        n = win.notice
        self.assertEqual(win.notice_tone, "warning")
        for needle in ("Windows 10", "October 14, 2025", "October 13, 2026", "Windows 11",
                       "Antivirus and the settings below do not make an unsupported version of Windows secure"):
            self.assertIn(needle, n)
        text = _section_text(win)
        self.assertIn("windows home", text)           # BitLocker edition limit
        self.assertIn("smart app control is a windows 11 feature", text)
        self.assertIn("compatible camera", text)       # Windows Hello hardware limit

    def test_availability_limits_are_mentioned(self):
        for section in SECTIONS:
            self.assertRegex(section.notice.lower(), r"version|edition|manufacturer|vary", section.key)
        text = " ".join(_section_text(s) for s in SECTIONS)
        for needle in ("android 11", "apple silicon", "older iphones", "macos 13", "tpm"):
            self.assertIn(needle, text)

    def test_no_hard_coded_future_prone_os_version_names(self):
        text = " ".join(_section_text(s) for s in SECTIONS)
        self.assertIsNone(re.search(r"\b(ios|ipados|macos) ?(1[5-9]|2\d)\b", text))
        self.assertIsNone(re.search(r"\bandroid 1[5-9]\b", text))
        for name in ("tahoe", "sequoia", "sonoma"):
            self.assertNotIn(name, text)

    def test_content_is_plain_text(self):
        text = " ".join(_section_text(s) for s in SECTIONS) + GENERAL_NOTE
        for bad in ("<script", "http://", "javascript:"):
            self.assertNotIn(bad, text.lower())

    def test_find_hub_uses_the_current_google_name(self):
        text = _section_text(SECTIONS[0])
        self.assertIn("find hub", text)
        self.assertIn("formerly", text.replace("previously", "formerly"))


class PageBase(unittest.TestCase):
    def setUp(self):
        self.fake = FakeStreamlit()
        self.st = self.fake.st
        self.st.tabs.side_effect = lambda labels: [mock.MagicMock() for _ in labels]
        self.mods = mock.patch.dict(sys.modules, {"streamlit": self.st})
        self.mods.start()
        self._purge()
        self.page = importlib.import_module("views.cyber_hygiene")

    def tearDown(self):
        self._purge()
        self.mods.stop()

    @staticmethod
    def _purge():
        for name in [m for m in list(sys.modules) if m.split(".")[0] in ("views", "components")]:
            del sys.modules[name]


class PageRenderTests(PageBase):
    def test_renders_title_four_tabs_and_every_item(self):
        self.page.render()
        self.st.title.assert_called_once_with("Cyber Hygiene")
        labels = self.st.tabs.call_args.args[0]
        self.assertEqual(labels, [f"{s.icon} {s.title}" for s in SECTIONS])
        total = sum(len(s.items) for s in SECTIONS)
        self.assertEqual(self.st.expander.call_count, total)
        md = self.fake.all_markdown()
        for s in SECTIONS:
            for i in s.items:
                self.assertIn(i.title, md)
        self.assertIn("What it is:", md)
        self.assertIn("Why it matters:", md)

    def test_two_column_card_layout(self):
        self.page.render()
        widths = {c.args[0] for c in self.st.columns.call_args_list}
        self.assertEqual(widths, {2})
        expected_rows = sum((len(s.items) + 1) // 2 for s in SECTIONS)
        self.assertEqual(self.st.columns.call_count, expected_rows)

    def test_each_link_item_gets_one_official_doc_button(self):
        self.page.render()
        calls = self.st.link_button.call_args_list
        expected = [(i.doc.label, i.doc.url) for s in SECTIONS for i in s.items if i.doc]
        got = [(c.args[0], c.args[1]) for c in calls]
        self.assertEqual(len(got), len(expected))
        for (label, url), (g_label, g_url) in zip(expected, got):
            self.assertIn(label, g_label)
            self.assertEqual(url, g_url)
        self.assertTrue(all(c.args[1].startswith("https://") for c in calls))

    def test_steps_tip_and_note_are_inside_the_expander(self):
        self.page.render()
        md = self.fake.all_markdown()
        self.assertIn("**How to enable**", md)
        self.assertIn("**Security recommendation:**", md)
        self.assertIn("1. ", md)
        captions = str(self.st.caption.call_args_list)
        self.assertIn("Availability:", captions)
        self.assertIn(DOCS_CHECKED, captions)

    def test_windows_notice_is_a_warning_and_others_are_info(self):
        self.page.render()
        warnings = [c.args[0] for c in self.st.warning.call_args_list]
        self.assertEqual(len(warnings), 1)
        self.assertIn("Windows 10", warnings[0])
        self.assertEqual(self.st.info.call_count, 3)

    def test_item_without_a_link_says_so(self):
        self.page.render()
        self.assertIn("No official documentation link", str(self.st.caption.call_args_list))

    def test_all_text_is_escaped_before_html(self):
        hostile = Item("x", "<script>alert(1)</script>", "<img src=x onerror=1>", "a & b", ("1", "2", "3"),
                       "tip", Doc("lbl", "https://support.google.com/android/answer/7680439"))
        section = OsSection("t", "T", "T", "intro", "notice", "info", (hostile,))
        with mock.patch.object(self.page, "SECTIONS", (section,)):
            self.page.render()
        html_calls = [c.args[0] for c in self.st.markdown.call_args_list if c.kwargs.get("unsafe_allow_html")]
        joined = "\n".join(html_calls)
        self.assertNotIn("<script>", joined)
        self.assertNotIn("<img", joined)
        self.assertIn("&lt;script&gt;", joined)
        self.assertIn("a &amp; b", joined)

    def test_rendering_writes_no_session_state_and_makes_no_network_or_widgets(self):
        before = dict(self.fake.session)
        self.page.render()
        self.assertEqual(dict(self.fake.session), before)
        self.assertFalse(self.st.rerun.called)
        for name in ("text_input", "text_area", "file_uploader", "checkbox", "selectbox"):
            self.assertFalse(getattr(self.st, name).called, name)
        self.assertFalse(self.st.button.called)
        tree = ast.parse(_read("views/cyber_hygiene.py"))
        imported = {n.names[0].name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import)}
        imported |= {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
        self.assertFalse(imported & {"requests", "backend", "config", "os", "subprocess", "urllib"})


class IntegrationTests(unittest.TestCase):
    def test_registry_entry(self):
        m = reg.get_module("cyber_hygiene")
        self.assertEqual((m.key, m.title, m.icon, m.group, m.status),
                         ("cyber_hygiene", "Cyber Hygiene", "🛡️", "Protect", "implemented"))
        self.assertIn("cyber_hygiene", reg.implemented_keys())
        self.assertNotIn("cyber_hygiene", [p.key for p in reg.planned()])

    def test_router_wiring_and_sync_assertion_are_intact(self):
        src = _read("streamlit_app.py")
        self.assertIn('"cyber_hygiene": cyber_hygiene.render,', src)
        self.assertIn("assert set(PAGES) == set(reg.implemented_keys())", src)
        self.assertTrue(_read("views/cyber_hygiene.py"))

    def test_protect_group_sits_between_qr_tools_and_learn(self):
        groups = nav_state.nav_groups()
        self.assertEqual([g for g, _ in groups], ["Platform", "Analysis", "QR Tools", "Protect", "Learn", "System"])
        protect = dict(groups)["Protect"]
        self.assertEqual([m.key for m in protect], ["cyber_hygiene"])

    def test_navigate_opens_the_page_and_closes_the_drawer(self):
        state = {nav_state.SIDEBAR_KEY: True, "page": "dashboard", "guide_history": ["keep"]}
        self.assertEqual(nav_state.navigate(state, "cyber_hygiene"), "cyber_hygiene")
        self.assertFalse(nav_state.is_sidebar_open(state))
        self.assertEqual(state["guide_history"], ["keep"])


class ShieldFlowTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeStreamlit()
        self.fake.st.tabs.side_effect = lambda labels: [mock.MagicMock() for _ in labels]
        self.fake.run_app()
        self.fake.press("landing_cta_hero")
        self.fake.run_app()

    def toggle(self):
        self.fake.press("cybershield_navtoggle_btn")
        self.fake.run_app()

    def test_opens_through_the_shield_highlights_and_closes_the_drawer(self):
        self.fake.session["guide_history"] = [{"role": "user", "content": "keep"}]
        self.toggle()
        self.assertIn("cs_navitem_cyber_hygiene", self.fake.button_keys)
        self.assertIn("Cyber Hygiene", self.fake.button_labels["cs_navitem_cyber_hygiene"])
        self.assertIn("🛡️", self.fake.button_labels["cs_navitem_cyber_hygiene"])
        self.assertIn("Protect", self.fake.all_markdown())
        self.fake.press("cs_navitem_cyber_hygiene")
        self.assertEqual(self.fake.session["page"], "cyber_hygiene")
        self.assertFalse(self.fake.session[nav_state.SIDEBAR_KEY])
        self.assertEqual(self.fake.session["view"], "app")
        self.fake.run_app()
        self.assertFalse(self.fake.st.error.called)
        self.fake.st.title.assert_called_with("Cyber Hygiene")
        self.assertEqual(self.fake.st.link_button.call_count,
                         sum(1 for s in SECTIONS for i in s.items if i.doc))
        self.toggle()
        active = [k for k in self.fake.button_keys if k and k.startswith("cs_navitem_active_")]
        self.assertEqual(active, ["cs_navitem_active_cyber_hygiene"])
        self.assertEqual(self.fake.session["guide_history"][0]["content"], "keep")
        keys = [k for k in self.fake.button_keys if k]
        self.assertEqual(len(keys), len(set(keys)), "duplicate widget keys")

    def test_page_renders_with_cyberguide_present_and_no_sidebar(self):
        self.fake.session["page"] = "cyber_hygiene"
        self.fake.run_app()
        self.assertFalse(self.fake.st.error.called)
        self.assertIn("cyberguide_fab", self.fake.container_keys())
        self.assertFalse(self.fake.sidebar_calls())

    def test_dashboard_lists_the_new_page_automatically(self):
        # dashboard.py is unchanged: it builds its tool cards from the registry.
        self.assertIn("Open Cyber Hygiene", self.fake.button_labels.values())
        self.assertIn("dash_open_cyber_hygiene", self.fake.button_keys)

    def test_every_other_page_still_renders(self):
        for key in reg.implemented_keys():
            fake = FakeStreamlit()
            fake.st.tabs.side_effect = lambda labels: [mock.MagicMock() for _ in labels]
            fake.run_app()
            fake.session["view"] = "app"
            fake.session["page"] = key
            fake.run_app()
            self.assertFalse(fake.st.error.called, key)


class KnowledgeTests(unittest.TestCase):
    def sections(self):
        return [s for s in load_sections() if s.page == "cyber_hygiene"]

    def test_topics_exist_and_link_to_the_page_key(self):
        secs = self.sections()
        self.assertEqual(len(secs), 2)
        body = " ".join(s.body for s in secs)
        for needle in ("cyber_hygiene", "Protect", "Android Security", "Windows Security", "iOS Security",
                       "macOS Security", "Google Play Protect", "Microsoft Defender", "FileVault", "Find My",
                       "Gatekeeper", "XProtect", "Time Machine", "Windows 10 reached end of support"):
            self.assertIn(needle, body, needle)
        for s in secs:
            self.assertLessEqual(len(s.body), 1800, "engine truncates sections at 1800 characters")

    def test_knowledge_matches_the_implementation(self):
        body = " ".join(s.body for s in self.sections())
        self.assertIn("one Android tip, avoiding unknown public Wi-Fi, has no documentation link", body)
        for s in SECTIONS:
            self.assertIn(s.title, body)
        self.assertNotIn("planned", body.lower())

    def test_question_retrieval(self):
        for q in ("How do I secure my Android phone?", "Is antivirus enough on Windows 10?",
                  "Where is the Cyber Hygiene page?", "How do I turn on FileVault on my Mac?"):
            top = [s.page for s in retrieve(q, k=3)]
            self.assertIn("cyber_hygiene", top, q)

    def test_navigation_docs_name_the_protect_group(self):
        nav = next(s for s in load_sections() if s.title == "Navigation sidebar and shield button")
        self.assertIn("Cyber Hygiene", nav.body)
        text = _read("knowledge.md")
        self.assertIn("Protect (Cyber Hygiene)", text)
        self.assertIn("lists all eleven pages", text)

    def test_readme_mentions_the_page(self):
        readme = _read("README.md")
        self.assertIn("Cyber Hygiene", readme)
        self.assertIn("all eleven pages", readme)


if __name__ == "__main__":
    unittest.main()
