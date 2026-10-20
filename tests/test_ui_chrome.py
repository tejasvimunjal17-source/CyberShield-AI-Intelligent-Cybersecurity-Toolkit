import ast
import unittest

import app_registry as reg
import config
from components.chrome import HEADER_SELECTORS, SIDEBAR_SELECTORS, TOOLBAR_SELECTORS, chrome_css


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

    def test_header_hidden_only_when_custom_navigation_is_in_use(self):
        # Part 4: the shield navigation does not depend on Streamlit's header, so it is
        # hidden with the custom navigation. The legacy sidebar's collapse control lives
        # in the header, so in legacy mode only the toolbar is hidden.
        for sel in HEADER_SELECTORS:
            self.assertIn(sel, chrome_css(True))
            self.assertNotIn(sel, chrome_css(False))

    def test_toolbar_selectors_cover_share_github_edit_menu_and_deploy(self):
        joined = " ".join(TOOLBAR_SELECTORS)
        for needle in ("stToolbar", "stToolbarActions", "stAppDeployButton", "stMainMenu"):
            self.assertIn(needle, joined)

    def test_never_targets_app_content_or_platform_controls(self):
        css = chrome_css(True)
        for forbidden in ("stMain\"", "stApp\"", "stAppViewContainer", "block-container", "stMarkdown",
                          "stButton", "stVerticalBlock", "visibility: hidden",
                          "viewerBadge", "manage", "Manage", "st-key-"):
            self.assertNotIn(forbidden, css, forbidden)

    def test_hides_with_display_none_only(self):
        for line in chrome_css(True).splitlines():
            if "{" in line:
                self.assertIn("display: none !important", line)

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
