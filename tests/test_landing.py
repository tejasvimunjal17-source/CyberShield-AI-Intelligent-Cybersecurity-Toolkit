import ast
import unittest

import app_registry as reg
from components import app_state
from components.landing_css import landing_css
from content import landing_content as copy


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


class AppStateTests(unittest.TestCase):
    def test_fresh_session_is_landing(self):
        self.assertEqual(app_state.get_view({}), app_state.VIEW_LANDING)

    def test_unknown_view_value_is_landing(self):
        for bad in ("", "admin", None, 5):
            self.assertEqual(app_state.get_view({"view": bad}), app_state.VIEW_LANDING)

    def test_get_started_opens_dashboard(self):
        state = {}
        self.assertEqual(app_state.enter_app(state), "dashboard")
        self.assertEqual(app_state.get_view(state), app_state.VIEW_APP)
        self.assertEqual(state["page"], reg.DEFAULT_PAGE)

    def test_enter_specific_page_and_every_implemented_page(self):
        for key in reg.implemented_keys():
            state = {}
            app_state.enter_app(state, page=key)
            self.assertEqual(state["page"], key)

    def test_invalid_or_planned_page_falls_back_to_dashboard(self):
        for bad in ("nope", "phishing_lab", "reports", ""):
            state = {}
            app_state.enter_app(state, page=bad)
            self.assertEqual(state["page"], "dashboard")

    def test_open_guide_flag(self):
        state = {}
        app_state.enter_app(state, open_guide=True)
        self.assertTrue(state["guide_open"])
        state2 = {}
        app_state.enter_app(state2)
        self.assertNotIn("guide_open", state2)

    def test_unrelated_state_is_preserved(self):
        state = {"guide_history": [{"role": "user", "content": "hi"}], "url_analysis": "x", "guide_open": False}
        app_state.enter_app(state)
        self.assertEqual(state["guide_history"], [{"role": "user", "content": "hi"}])
        self.assertEqual(state["url_analysis"], "x")
        self.assertFalse(state["guide_open"])

    def test_repeated_calls_are_stable(self):
        state = {}
        for _ in range(5):
            app_state.enter_app(state)
            self.assertEqual(app_state.get_view(state), "app")
        snapshot = dict(state)
        for _ in range(5):
            app_state.get_view(state)
        self.assertEqual(state, snapshot)

    def test_module_keys_match_existing_code(self):
        self.assertIn(f'"{app_state.PAGE_KEY}"', _read("components/sidebar.py"))
        self.assertIn(f'"{app_state.GUIDE_OPEN_KEY}"', _read("components/cyberguide_chat.py"))


class ContentTests(unittest.TestCase):
    def all_text(self):
        parts = [copy.HERO_HEADING, copy.HERO_DESCRIPTION, copy.FEATURES_HEADING, copy.HOW_HEADING,
                 copy.ABOUT_HEADING, copy.FINAL_HEADING, copy.FINAL_TEXT, copy.ABOUT_INTRO,
                 copy.FOOTER_NOTICE, *copy.TRUST_NOTES, *copy.HERO_CHIPS]
        for t, d in copy.STEPS:
            parts += [t, d]
        for f in copy.FEATURES:
            parts += [f.title, f.description, f.cta]
        return " ".join(parts)

    def test_required_copy_is_exact(self):
        self.assertEqual(copy.HERO_HEADING, "Your Smarter Cybersecurity Toolkit")
        self.assertEqual(copy.FEATURES_HEADING, "Everything You Need to Start Investigating")
        self.assertEqual(copy.FINAL_HEADING, "Ready to Explore CyberShield AI?")
        self.assertEqual(copy.FINAL_TEXT, "Choose a tool and start learning how to inspect potentially suspicious digital content.")
        self.assertEqual(len(copy.STEPS), 3)

    def test_six_features_with_unique_keys(self):
        self.assertEqual([f.title for f in copy.FEATURES],
                         ["URL Security Scanner", "File Hash Analyzer", "QR Code Generator",
                          "QR Code Security Analyzer", "CyberGuide AI", "Security Learning Center"])
        self.assertEqual(len({f.key for f in copy.FEATURES}), 6)

    def test_feature_links_point_to_implemented_pages_and_titles_match_registry(self):
        for f in copy.FEATURES:
            if f.page is not None:
                module = reg.get_module(f.page)
                self.assertIsNotNone(module, f.key)
                self.assertEqual(module.status, "implemented")
                self.assertEqual(module.title, f.title)
        guide = next(f for f in copy.FEATURES if f.key == "cyberguide")
        self.assertTrue(guide.open_guide)

    def test_planned_modules_are_not_advertised(self):
        text = self.all_text().lower()
        for m in reg.planned():
            self.assertNotIn(m.title.lower(), text, m.title)

    def test_no_unsupported_claims(self):
        text = self.all_text().lower()
        for phrase in ("certified", "certification", "trusted by", "enterprise", "military", "100%",
                       "bank-grade", "unbreakable", "real-time protection", "blocks threats", "million"):
            self.assertNotIn(phrase, text, phrase)

    def test_required_honesty_notices_present(self):
        notes = " ".join(copy.TRUST_NOTES).lower()
        for needle in ("heuristic", "inaccurate", "api configuration", "does not guarantee"):
            self.assertIn(needle, notes, needle)
        self.assertIn("educational", copy.ABOUT_INTRO.lower())

    def test_footer_links_are_in_page_anchors(self):
        for _, href in copy.FOOTER_LINKS:
            self.assertTrue(href.startswith("#"))


class CssTests(unittest.TestCase):
    def setUp(self):
        self.css = landing_css()

    def test_valid_style_block(self):
        self.assertTrue(self.css.strip().startswith("<style>") and self.css.strip().endswith("</style>"))
        self.assertEqual(self.css.count("{"), self.css.count("}"))

    def test_has_mobile_breakpoint(self):
        self.assertIn("@media (max-width: 640px)", self.css)

    def test_does_not_touch_part1_chrome_or_hide_things(self):
        for forbidden in ("stSidebar", "stToolbar", "stHeader", "stMainMenu", "stStatusWidget",
                          "visibility: hidden", "display: none"):
            self.assertNotIn(forbidden, self.css)

    def test_no_external_resources_or_scripts(self):
        for forbidden in ("http://", "https://", "@import", "<script", "url("):
            self.assertNotIn(forbidden, self.css)

    def test_cta_buttons_have_dark_text_for_contrast(self):
        self.assertIn("#06121F", self.css)


class WiringTests(unittest.TestCase):
    def main_body(self):
        tree = ast.parse(_read("streamlit_app.py"))
        return next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main").body

    @staticmethod
    def _calls(node):
        return {getattr(c.func, "id", getattr(c.func, "attr", "")) for c in ast.walk(node) if isinstance(c, ast.Call)}

    def test_landing_branch_returns_before_app_shell(self):
        body = self.main_body()
        branch = next(s for s in body if isinstance(s, ast.If)
                      and "VIEW_LANDING" in ast.dump(s.test) and "get_view" in ast.dump(s.test))
        self.assertIn("render_landing", self._calls(branch))
        self.assertTrue(any(isinstance(s, ast.Return) for s in branch.body))
        landing_calls = self._calls(branch)
        for shell in ("render_top_menu", "render_sidebar", "render_cyberguide"):
            self.assertNotIn(shell, landing_calls)
        index = body.index(branch)
        later = set()
        for stmt in body[index + 1:]:
            later |= self._calls(stmt)
        self.assertIn("render_top_menu", later)
        self.assertIn("render_cyberguide", later)

    def test_no_pages_directory_and_views_kept(self):
        import os
        self.assertFalse(os.path.exists("pages"))
        self.assertTrue(os.path.isdir("views"))

    def test_landing_module_has_no_rerun_or_javascript_or_query_params(self):
        tree = ast.parse(_read("components/landing.py"))
        used = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        for forbidden in ("rerun", "query_params", "switch_page", "html"):
            self.assertNotIn(forbidden, used, f"landing.py uses st.{forbidden}")
        strings = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        self.assertFalse([t for t in strings if "<script" in t.lower() or "javascript:" in t.lower()])


if __name__ == "__main__":
    unittest.main()
