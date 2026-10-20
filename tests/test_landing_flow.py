"""Landing -> app flow, run against tests/fake_streamlit.py (a stand-in for
Streamlit, NOT a browser). Proves the Python control flow; it does not prove
how anything looks."""

import unittest

import app_registry as reg
from content import landing_content as copy
from tests.fake_streamlit import FakeStreamlit


class LandingFlowTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeStreamlit()

    def enter(self, key="landing_cta_hero"):
        self.fake.run_app()
        self.fake.press(key)
        self.fake.run_app()

    # --- State A: landing -----------------------------------------------------
    def test_fresh_visitor_sees_landing(self):
        self.fake.run_app()
        self.assertNotIn("view", self.fake.session)           # nothing set yet
        md = self.fake.all_markdown()
        self.assertIn("Cybersecurity", md)
        self.assertIn("Everything You Need to Start Investigating", md)
        self.assertIn("Ready to Explore CyberShield AI?", md)
        for key in ("landing_cta_hero", "landing_cta_final"):
            self.assertIn(key, self.fake.button_keys)
        self.assertNotIn("landing_cta_top", self.fake.button_keys, "top-bar Get Started was removed in Part 4")

    def test_landing_has_no_menu_chat_or_sidebar(self):
        self.fake.run_app()
        st = self.fake.st
        self.assertFalse(st.popover.called, "temporary menu must not render on landing")
        self.assertNotIn("cyberguide_fab", self.fake.container_keys())
        self.assertFalse([k for k in self.fake.button_keys
                          if k and k.startswith(("menu_", "nav_", "guide_", "cybershield_", "cs_nav"))])
        self.assertFalse([k for k in self.fake.container_keys() if k and k.startswith("cybershield_nav")],
                         "shield toggle/drawer must not render on landing")
        self.assertFalse(self.fake.sidebar_calls())

    def test_landing_does_not_show_dashboard_content(self):
        self.fake.run_app()
        self.assertFalse(self.fake.st.subheader.called)

    def test_landing_shows_all_six_feature_cards_with_buttons(self):
        self.fake.run_app()
        keys = self.fake.container_keys()
        for f in copy.FEATURES:
            self.assertIn(f"landing_card_{f.key}", keys)
            self.assertIn(f"landing_open_{f.key}", self.fake.button_keys)

    # --- Get Started -----------------------------------------------------------
    def test_each_get_started_button_opens_dashboard(self):
        for key in ("landing_cta_hero", "landing_cta_final"):
            self.fake = FakeStreamlit()
            self.enter(key)
            self.assertEqual(self.fake.session["view"], "app", key)
            self.assertEqual(self.fake.session["page"], "dashboard", key)
            subheaders = [c.args[0] for c in self.fake.st.subheader.call_args_list]
            self.assertIn("Service status", subheaders, key)

    # --- State B: application ---------------------------------------------------
    def test_app_state_has_shield_toggle_and_chat_and_no_sidebar(self):
        self.enter()
        st = self.fake.st
        self.assertFalse(st.popover.called, "old temporary menu must be gone")
        self.assertIn("cybershield_navtoggle_btn", self.fake.button_keys)
        self.assertIn("cyberguide_fab", self.fake.container_keys())
        self.assertIn("guide_toggle", self.fake.button_keys)
        self.assertFalse(self.fake.sidebar_calls())
        self.assertNotIn("landing_cta_top", self.fake.button_keys)

    def test_obsolete_menu_controls_are_gone_after_entering(self):
        self.assertEqual(len(reg.implemented_keys()), 8)
        self.enter()
        self.assertFalse([k for k in self.fake.button_keys if k and k.startswith("menu_")])
        self.assertNotIn("☰ Menu", self.fake.all_markdown())

    def test_every_page_renders_after_entering(self):
        for key in reg.implemented_keys():
            self.fake = FakeStreamlit()
            self.fake.run_app()
            self.fake.session["view"] = "app"
            self.fake.session["page"] = key
            self.fake.run_app()                                # raises on any page error
            self.assertFalse(self.fake.st.error.called, key)

    def test_feature_buttons_route_to_real_pages(self):
        for f in copy.FEATURES:
            self.fake = FakeStreamlit()
            self.fake.run_app()
            self.fake.press(f"landing_open_{f.key}")
            self.assertEqual(self.fake.session["view"], "app")
            self.assertEqual(self.fake.session["page"], f.page or "dashboard")
            self.assertEqual(bool(self.fake.session.get("guide_open")), f.open_guide, f.key)
            self.fake.run_app()
            self.assertFalse(self.fake.st.error.called, f.key)

    def test_unrelated_session_state_survives_entry(self):
        self.fake.session["guide_history"] = [{"role": "user", "content": "hello"}]
        self.fake.session["url_analysis"] = "keep-me"
        self.enter()
        self.assertEqual(self.fake.session["guide_history"][0]["content"], "hello")
        self.assertEqual(self.fake.session["url_analysis"], "keep-me")

    # --- Part 4: top bar and toolbar chrome -------------------------------------
    def test_topbar_shows_brand_features_and_about_only(self):
        self.fake.run_app()
        topbar = next(m for m in self.fake.markdown_calls if '<nav class="cs-l-nav">' in m)   # the HTML, not the CSS
        self.assertIn("CyberShield AI", topbar)
        self.assertIn('href="#features"', topbar)
        self.assertIn('href="#about"', topbar)
        self.assertNotIn("<button", topbar)
        self.assertNotIn("Get Started", topbar)

    def test_hero_cta_explore_features_and_footer_anchors_preserved(self):
        self.fake.run_app()
        md = self.fake.all_markdown()
        self.assertIn("landing_cta_hero", self.fake.button_keys)
        self.assertIn("landing_cta_final", self.fake.button_keys)
        self.assertIn("Explore Features", md)
        self.assertIn('id="features"', md)
        self.assertIn('id="about"', md)
        self.assertIn('id="how-it-works"', md)
        self.assertEqual(self.fake.button_labels["landing_cta_hero"], "Get Started")

    def test_no_empty_columns_left_in_topbar(self):
        # the only st.columns calls on the landing page are the hero, the nested hero
        # buttons, the three feature-card columns x2 and the final CTA
        self.fake.run_app()
        specs = [c.args[0] for c in self.fake.st.columns.call_args_list]
        self.assertNotIn([4, 1.3], specs)

    def test_toolbar_css_is_injected_once_on_landing_and_on_every_app_page(self):
        self.fake.run_app()
        landing_md = self.fake.all_markdown()
        self.assertEqual(landing_md.count('[data-testid="stToolbar"]'), 1)
        self.assertIn('[data-testid="stHeader"]', landing_md)
        for key in reg.implemented_keys():
            self.fake = FakeStreamlit()
            self.fake.run_app()
            self.fake.session["view"] = "app"
            self.fake.session["page"] = key
            self.fake.run_app()
            md = self.fake.all_markdown()
            self.assertEqual(md.count('[data-testid="stToolbar"]'), 1, key)
            self.assertIn('[data-testid="stHeader"]', md, key)
            self.assertIn("cybershield_navtoggle_btn", self.fake.button_keys, key)   # shield kept
            self.assertIn("cyberguide_fab", self.fake.container_keys(), key)         # chat kept

    # --- reruns / loops ---------------------------------------------------------
    def test_repeated_reruns_on_landing_are_stable(self):
        for _ in range(5):
            self.fake.run_app()
            self.assertFalse(self.fake.st.rerun.called)
        self.assertNotIn("view", self.fake.session)

    def test_repeated_reruns_in_app_are_stable(self):
        self.enter()
        for _ in range(5):
            self.fake.run_app()
            self.assertEqual(self.fake.session["view"], "app")
            self.assertEqual(self.fake.session["page"], "dashboard")
            self.assertFalse(self.fake.st.rerun.called)

    def test_navigation_inside_app_does_not_return_to_landing(self):
        self.enter()
        self.fake.session["page"] = "settings"        # what a navigation click writes
        self.fake.run_app()
        self.assertEqual(self.fake.session["view"], "app")
        self.assertIn("cybershield_navtoggle_btn", self.fake.button_keys)
        self.assertNotIn("landing_cta_top", self.fake.button_keys)
