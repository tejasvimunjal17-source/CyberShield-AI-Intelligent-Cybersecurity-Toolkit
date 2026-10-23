"""Maintenance tests: chrome (toolbar/header) CSS is wired into the shared render path.

Uses the fake Streamlit stand-in. This verifies what the app asks Streamlit to
render; it does not prove the controls disappear in a real browser or on a
given Streamlit/Community Cloud version.
"""

import ast
import importlib
import sys
import unittest
from unittest import mock

from components.chrome import HEADER_SELECTORS, TOOLBAR_SELECTORS, chrome_css
from tests.fake_streamlit import FakeStreamlit


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _main_body():
    tree = ast.parse(_read("streamlit_app.py"))
    return next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")


class MainWiringTests(unittest.TestCase):
    def test_main_calls_chrome_injection_unconditionally_before_the_view_split(self):
        body = _main_body().body
        names = [getattr(getattr(s.value, "func", None), "id", None) for s in body if isinstance(s, ast.Expr)]
        self.assertIn("inject_chrome_css", names, "must be a top-level statement of main(), not inside an if")
        first_if = next(i for i, s in enumerate(body) if isinstance(s, ast.If))
        self.assertLess(names.index("inject_chrome_css"), first_if)

    def test_called_once_per_run(self):
        calls = [n for n in ast.walk(_main_body())
                 if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "inject_chrome_css"]
        self.assertEqual(len(calls), 1)


class InjectChromeCssTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeStreamlit()
        self.patch = mock.patch.dict(sys.modules, {"streamlit": self.fake.st})
        self.patch.start()
        sys.modules.pop("components.theme", None)
        self.theme = importlib.import_module("components.theme")

    def tearDown(self):
        sys.modules.pop("components.theme", None)
        self.patch.stop()

    def test_custom_navigation_mode_hides_toolbar_and_header(self):
        with mock.patch.object(self.theme, "SHOW_DEFAULT_SIDEBAR", False):
            self.theme.inject_chrome_css()
        css = self.fake.all_markdown()
        self.assertEqual(css, chrome_css(True))
        for sel in TOOLBAR_SELECTORS + HEADER_SELECTORS:
            self.assertIn(sel, css)
        self.assertTrue(self.fake.st.markdown.call_args.kwargs.get("unsafe_allow_html"))

    def test_legacy_sidebar_mode_keeps_header_so_its_collapse_control_works(self):
        with mock.patch.object(self.theme, "SHOW_DEFAULT_SIDEBAR", True):
            self.theme.inject_chrome_css()
        css = self.fake.all_markdown()
        for sel in TOOLBAR_SELECTORS:
            self.assertIn(sel, css)
        for sel in HEADER_SELECTORS:
            self.assertNotIn(sel, css)

    def test_css_never_targets_our_own_controls(self):
        from components.shield_nav import DRAWER_KEY, TOGGLE_BOX_KEY, TOGGLE_BTN_KEY
        css = chrome_css(True)
        for ours in (DRAWER_KEY, TOGGLE_BOX_KEY, TOGGLE_BTN_KEY, "cyberguide", "landing", "cs-", "cybershield"):
            self.assertNotIn(ours, css, ours)

    def test_inject_css_itself_is_unchanged_and_separate(self):
        self.theme.inject_css()
        md = self.fake.all_markdown()
        self.assertIn(".block-container", md)
        self.assertNotIn("stToolbar", md)  # theme CSS stays free of chrome rules


if __name__ == "__main__":
    unittest.main()
