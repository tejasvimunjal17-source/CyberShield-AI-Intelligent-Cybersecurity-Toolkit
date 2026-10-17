import ast
import unittest

import app_registry as reg
import config
from components.chrome import SIDEBAR_SELECTORS, TOOLBAR_SELECTORS, chrome_css


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


class ChromeCssTests(unittest.TestCase):
    def test_toolbar_selectors_always_present(self):
        for hide in (True, False):
            css = chrome_css(hide)
            for sel in TOOLBAR_SELECTORS:
                self.assertIn(sel, css)

    def test_sidebar_css_only_when_requested(self):
        for sel in SIDEBAR_SELECTORS:
            self.assertIn(sel, chrome_css(True))
            self.assertNotIn(sel, chrome_css(False))

    def test_does_not_hide_header_menu_or_status(self):
        css = chrome_css(True)
        for forbidden in ("stHeader", "stMainMenu", "stStatusWidget", "stDecoration", "stMain", "stApp\"", "visibility: hidden"):
            self.assertNotIn(forbidden, css)

    def test_valid_style_block(self):
        css = chrome_css(True)
        self.assertTrue(css.startswith("<style>") and css.endswith("</style>"))
        self.assertEqual(css.count("{"), css.count("}"))


class WiringTests(unittest.TestCase):
    def test_default_sidebar_flag_is_off(self):
        self.assertFalse(config.SHOW_DEFAULT_SIDEBAR)

    def test_render_sidebar_only_called_when_flag_is_on(self):
        tree = ast.parse(_read("streamlit_app.py"))
        guarded, unguarded = 0, 0
        for node in ast.walk(tree):
            if isinstance(node, ast.If) and isinstance(node.test, ast.Name) and node.test.id == "SHOW_DEFAULT_SIDEBAR":
                for stmt in node.body:
                    for sub in ast.walk(stmt):
                        if isinstance(sub, ast.Call) and getattr(sub.func, "id", "") == "render_sidebar":
                            guarded += 1
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "render_sidebar":
                unguarded += 1
        self.assertEqual(guarded, 1)
        self.assertEqual(unguarded, guarded, "render_sidebar() called outside the SHOW_DEFAULT_SIDEBAR branch")

    def test_navigation_logic_preserved_for_future_parts(self):
        names = {n.name for n in ast.parse(_read("components/sidebar.py")).body if isinstance(n, ast.FunctionDef)}
        self.assertTrue({"go_to", "current_page", "render_sidebar"} <= names)
        self.assertNotIn("render_top_menu", names, "temporary menu was replaced by the shield drawer in Part 3")

    def test_legacy_sidebar_uses_registry_and_unique_key_prefix(self):
        src = _read("components/sidebar.py")
        self.assertIn("reg.implemented()", src)
        self.assertIn('key_prefix="nav"', src)
        self.assertNotIn('key_prefix="menu"', src)
        self.assertNotIn("popover", src)

    def test_all_pages_still_routed(self):
        src = _read("streamlit_app.py")
        for key in reg.implemented_keys():
            self.assertIn(f'"{key}":', src)

    def test_chatbot_docs_match_navigation_ui(self):
        sections = _read("knowledge.md").split("## ")
        nav = next(s for s in sections if s.startswith("Navigation map"))
        self.assertIn("shield", nav.lower())
        self.assertNotIn("☰", nav)
        if not config.SHOW_DEFAULT_SIDEBAR:
            text = _read("knowledge.md").lower()
            for obsolete in ("default sidebar", "streamlit sidebar", "streamlit's sidebar"):
                self.assertNotIn(obsolete, text)


if __name__ == "__main__":
    unittest.main()
