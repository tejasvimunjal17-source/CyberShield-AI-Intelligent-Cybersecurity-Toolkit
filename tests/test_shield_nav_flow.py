"""Shield toggle + drawer flow, run against tests/fake_streamlit.py (a
stand-in that records calls). This verifies the Python control flow and
state handling. It does NOT prove the fixed-position drawer looks or behaves
correctly in a browser."""

import unittest

import app_registry as reg
from components import nav_state
from components.shield_nav_css import DRAWER_KEY, TOGGLE_BOX_KEY, TOGGLE_BTN_KEY
from tests.fake_streamlit import FakeStreamlit

SIDEBAR = nav_state.SIDEBAR_KEY


def item_key(page, active_page):
    return f"cs_navitem_active_{page}" if page == active_page else f"cs_navitem_{page}"


class ShieldNavFlowTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeStreamlit()
        self.fake.run_app()
        self.fake.press("landing_cta_top")      # Get Started
        self.fake.run_app()

    def toggle(self):
        self.fake.press(TOGGLE_BTN_KEY)
        self.fake.run_app()

    def is_open(self):
        return DRAWER_KEY in self.fake.container_keys()

    # --- landing stays clean (fresh visitor) -------------------------------------
    def test_landing_has_no_shield_drawer_menu_or_chat(self):
        fake = FakeStreamlit()
        fake.run_app()
        self.assertNotIn(TOGGLE_BTN_KEY, fake.button_keys)
        self.assertFalse([k for k in fake.container_keys() if k in (TOGGLE_BOX_KEY, DRAWER_KEY, "cyberguide_fab")])
        self.assertFalse(fake.st.popover.called)
        self.assertFalse([k for k in fake.button_keys if k and k.startswith("cs_nav")])
        self.assertIn("landing_cta_top", fake.button_keys)          # existing CTA intact

    def test_get_started_still_opens_dashboard_with_shield(self):
        self.assertEqual(self.fake.session["view"], "app")
        self.assertEqual(self.fake.session["page"], "dashboard")
        self.assertIn(TOGGLE_BTN_KEY, self.fake.button_keys)
        self.assertIn(TOGGLE_BOX_KEY, self.fake.container_keys())

    # --- application shows toggle; drawer starts closed ------------------------------
    def test_app_shows_toggle_and_starts_closed(self):
        self.assertFalse(self.is_open())
        self.assertFalse(self.fake.session[SIDEBAR])
        self.assertFalse([k for k in self.fake.button_keys if k and k.startswith("cs_nav")])

    def test_toggle_has_shield_label_and_tooltips(self):
        self.assertEqual(self.fake.button_labels[TOGGLE_BTN_KEY], "🛡️")
        kwargs = [c.kwargs for c in self.fake.st.button.call_args_list if c.kwargs.get("key") == TOGGLE_BTN_KEY][0]
        self.assertEqual(kwargs["help"], "Open navigation")
        self.toggle()
        kwargs = [c.kwargs for c in self.fake.st.button.call_args_list if c.kwargs.get("key") == TOGGLE_BTN_KEY][0]
        self.assertEqual(kwargs["help"], "Close navigation")

    # --- open / close preserve the page ----------------------------------------------
    def test_open_and_close_preserve_current_page(self):
        self.fake.session["page"] = "file_analyzer"
        self.fake.run_app()
        self.toggle()
        self.assertTrue(self.is_open())
        self.assertEqual(self.fake.session["page"], "file_analyzer")
        self.toggle()
        self.assertFalse(self.is_open())
        self.assertEqual(self.fake.session["page"], "file_analyzer")

    def test_repeated_toggles_work_and_never_change_page(self):
        self.fake.session["page"] = "about"
        for i in range(1, 7):
            self.toggle()
            self.assertEqual(self.is_open(), i % 2 == 1)
            self.assertEqual(self.fake.session["page"], "about")
            self.assertEqual(self.fake.session["view"], "app")

    # --- drawer content ----------------------------------------------------------------
    def test_open_drawer_lists_all_eight_pages_with_labels(self):
        self.toggle()
        for key in reg.implemented_keys():
            k = item_key(key, "dashboard")
            self.assertIn(k, self.fake.button_keys, key)
            module = reg.get_module(key)
            self.assertIn(module.title, self.fake.button_labels[k])
            self.assertIn(module.icon, self.fake.button_labels[k])
        self.assertEqual(len([k for k in self.fake.button_keys if k and k.startswith("cs_navitem_")]), 8)
        for m in reg.planned():
            self.assertNotIn(m.title, " ".join(self.fake.button_labels.values()))

    def test_drawer_has_branding(self):
        self.toggle()
        md = self.fake.all_markdown()
        self.assertIn("CyberShield AI", md)
        self.assertIn("Intelligent Security. Clear Insights.", md)

    # --- navigation ---------------------------------------------------------------------
    def test_every_item_routes_to_its_page_closes_drawer_and_page_renders(self):
        for key in reg.implemented_keys():
            self.setUp()
            self.fake.session["guide_history"] = [{"role": "user", "content": "keep"}]
            self.toggle()
            self.fake.press(item_key(key, "dashboard"))
            self.assertEqual(self.fake.session["page"], key)
            self.assertFalse(self.fake.session[SIDEBAR], f"drawer should close after choosing {key}")
            self.assertEqual(self.fake.session["view"], "app")
            self.fake.run_app()
            self.assertFalse(self.fake.st.error.called, key)
            self.assertFalse(self.is_open())
            self.assertEqual(self.fake.session["guide_history"][0]["content"], "keep")

    def test_active_page_indicator_follows_navigation(self):
        for target in ("url_scanner", "settings", "learning_center"):
            self.toggle()
            self.fake.press(item_key(target, self.fake.session["page"]))
            self.fake.run_app()
            self.toggle()
            self.assertIn(f"cs_navitem_active_{target}", self.fake.button_keys)
            self.assertEqual(len([k for k in self.fake.button_keys if k and k.startswith("cs_navitem_active_")]), 1)
            self.toggle()  # close for next loop

    def test_selecting_the_already_active_page_is_safe(self):
        self.toggle()
        self.fake.press("cs_navitem_active_dashboard")
        self.fake.run_app()
        self.assertEqual(self.fake.session["page"], "dashboard")
        self.assertFalse(self.is_open())
        self.assertFalse(self.fake.st.error.called)

    # --- old menu gone, no duplicate navigation ------------------------------------------
    def test_no_obsolete_menu_and_no_duplicate_navigation(self):
        for opened in (False, True):
            if opened:
                self.toggle()
            self.assertFalse(self.fake.st.popover.called)
            self.assertNotIn("☰ Menu", self.fake.all_markdown())
            self.assertFalse([k for k in self.fake.button_keys if k and (k.startswith("menu_") or k.startswith("nav_"))])
            self.assertFalse(self.fake.sidebar_calls())
            keys = [k for k in self.fake.button_keys if k]
            self.assertEqual(len(keys), len(set(keys)), "duplicate widget keys")

    # --- CyberGuide preserved -------------------------------------------------------------
    def test_cyberguide_available_with_drawer_closed_and_open(self):
        for opened in (False, True):
            if opened:
                self.toggle()
            self.assertIn("cyberguide_fab", self.fake.container_keys())
            self.assertIn("guide_toggle", self.fake.button_keys)

    def test_chat_state_survives_toggle_and_navigation(self):
        self.fake.session["guide_history"] = [{"role": "user", "content": "q"}]
        self.fake.session["guide_open"] = True
        self.toggle()
        self.fake.press(item_key("about", "dashboard"))
        self.fake.run_app()
        self.assertEqual(self.fake.session["guide_history"], [{"role": "user", "content": "q"}])
        self.assertTrue(self.fake.session["guide_open"])

    # --- rerun stability --------------------------------------------------------------------
    def test_repeated_reruns_are_stable_open_and_closed(self):
        for opened in (False, True):
            if opened:
                self.toggle()
            snapshot = dict(self.fake.session)
            for _ in range(5):
                self.fake.run_app()
                self.assertFalse(self.fake.st.rerun.called)
            self.assertEqual(dict(self.fake.session), snapshot)
            self.assertEqual(self.is_open(), opened)

    def test_sidebar_state_not_reset_by_navigation_inside_app(self):
        self.toggle()
        self.fake.session["page"] = "settings"      # e.g. a CyberGuide 'Open <page>' button
        self.fake.run_app()
        self.assertTrue(self.fake.session[SIDEBAR])
        self.assertEqual(self.fake.session["page"], "settings")


if __name__ == "__main__":
    unittest.main()
