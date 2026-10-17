import unittest

import app_registry as reg
from components import nav_state
from components import shield_nav_css as css

EIGHT_TITLES_IN_ORDER = [
    "Overview Dashboard", "URL Security Scanner", "File Hash Analyzer", "QR Code Generator",
    "QR Code Security Analyzer", "Security Learning Center", "Settings & API Configuration",
    "About CyberShield AI",
]


class SidebarStateTests(unittest.TestCase):
    def test_state_variable_name_and_default(self):
        self.assertEqual(nav_state.SIDEBAR_KEY, "cybershield_sidebar_open")
        self.assertFalse(nav_state.DEFAULT_SIDEBAR_OPEN)
        self.assertFalse(nav_state.is_sidebar_open({}))

    def test_toggle_opens_then_closes(self):
        state = {}
        self.assertTrue(nav_state.toggle_sidebar(state))
        self.assertTrue(nav_state.is_sidebar_open(state))
        self.assertFalse(nav_state.toggle_sidebar(state))
        self.assertFalse(nav_state.is_sidebar_open(state))

    def test_repeated_toggles_follow_parity(self):
        state = {}
        for i in range(1, 12):
            nav_state.toggle_sidebar(state)
            self.assertEqual(nav_state.is_sidebar_open(state), i % 2 == 1)

    def test_toggle_never_changes_page_or_other_state(self):
        state = {"page": "file_analyzer", "view": "app", "guide_history": [1, 2], "url_analysis": "x"}
        before = {k: v for k, v in state.items()}
        for _ in range(4):
            nav_state.toggle_sidebar(state)
        after = {k: v for k, v in state.items() if k != nav_state.SIDEBAR_KEY}
        self.assertEqual(after, before)

    def test_navigate_each_implemented_page_sets_page_and_closes(self):
        for key in reg.implemented_keys():
            state = {nav_state.SIDEBAR_KEY: True, "page": "dashboard"}
            self.assertEqual(nav_state.navigate(state, key), key)
            self.assertEqual(state["page"], key)
            self.assertFalse(nav_state.is_sidebar_open(state))

    def test_selecting_the_active_page_is_harmless(self):
        state = {nav_state.SIDEBAR_KEY: True, "page": "settings", "guide_history": ["keep"]}
        self.assertEqual(nav_state.navigate(state, "settings"), "settings")
        self.assertFalse(nav_state.is_sidebar_open(state))
        self.assertEqual(state["guide_history"], ["keep"])

    def test_unknown_or_planned_page_keeps_current_page(self):
        for bad in ("nope", "phishing_lab", "reports", ""):
            state = {nav_state.SIDEBAR_KEY: True, "page": "qr_generator"}
            self.assertEqual(nav_state.navigate(state, bad), "qr_generator")
            self.assertEqual(state["page"], "qr_generator")
        state = {}
        self.assertEqual(nav_state.navigate(state, "nope"), reg.DEFAULT_PAGE)

    def test_navigate_does_not_touch_view_or_chat(self):
        state = {"view": "app", "guide_open": True, "guide_history": ["a"], nav_state.SIDEBAR_KEY: True}
        nav_state.navigate(state, "about")
        self.assertEqual((state["view"], state["guide_open"], state["guide_history"]), ("app", True, ["a"]))


class NavModelTests(unittest.TestCase):
    def flat(self):
        return [m for _, mods in nav_state.nav_groups() for m in mods]

    def test_exactly_the_eight_pages_in_the_required_order(self):
        self.assertEqual([m.title for m in self.flat()], EIGHT_TITLES_IN_ORDER)

    def test_every_implemented_page_appears_once_and_no_planned_page(self):
        keys = [m.key for m in self.flat()]
        self.assertEqual(sorted(keys), sorted(reg.implemented_keys()))
        self.assertEqual(len(keys), len(set(keys)))
        self.assertFalse({m.key for m in reg.planned()} & set(keys))

    def test_group_order(self):
        self.assertEqual([g for g, _ in nav_state.nav_groups()], ["Platform", "Analysis", "QR Tools", "Learn", "System"])


class ShieldCssTests(unittest.TestCase):
    def setUp(self):
        self.css = css.shield_nav_css()

    def test_valid_style_block(self):
        self.assertTrue(self.css.strip().startswith("<style>") and self.css.strip().endswith("</style>"))
        self.assertEqual(self.css.count("{"), self.css.count("}"))

    def test_keys_are_distinct_and_never_substrings_of_each_other(self):
        keys = [css.TOGGLE_BOX_KEY, css.TOGGLE_BTN_KEY, css.DRAWER_KEY]
        for a in keys:
            for b in keys:
                if a != b:
                    self.assertNotIn(a, b, f"{a} would also match {b}")
        for k in keys:
            self.assertIn(f"st-key-{k}", self.css)

    def test_toggle_sits_above_drawer(self):
        import re
        z = [int(n) for n in re.findall(r"z-index:\s*(\d+)", self.css)]
        self.assertGreater(max(z), min(z))
        toggle_block = self.css.split('st-key-cybershield_navtoggle_box"]')[1].split("}")[0]
        drawer_block = self.css.split('st-key-cybershield_navdrawer_panel"] {')[1].split("}")[0]
        self.assertGreater(int(re.search(r"z-index:\s*(\d+)", toggle_block).group(1)),
                           int(re.search(r"z-index:\s*(\d+)", drawer_block).group(1)))

    def test_does_not_touch_streamlit_chrome_or_hide_content(self):
        for forbidden in ("stSidebar", "stHeader", "stToolbar", "stMainMenu", "stMain\"", "stApp",
                          "visibility: hidden", "display: none", "overflow-x: hidden"):
            self.assertNotIn(forbidden, self.css)

    def test_has_mobile_rule_focus_state_reduced_motion_and_content_padding(self):
        for needle in ("@media (max-width: 640px)", "focus-visible", "prefers-reduced-motion",
                       ".block-container { padding-top: 4rem"):
            self.assertIn(needle, self.css)

    def test_touch_target_is_at_least_44px(self):
        self.assertIn("width: 44px; height: 44px", self.css)

    def test_no_external_resources_or_scripts(self):
        for forbidden in ("http://", "https://", "@import", "<script", "url("):
            self.assertNotIn(forbidden, self.css)

    def test_active_item_has_distinct_style(self):
        self.assertIn("st-key-cs_navitem_active_", self.css)
        self.assertIn("#22D3EE", self.css)


if __name__ == "__main__":
    unittest.main()
