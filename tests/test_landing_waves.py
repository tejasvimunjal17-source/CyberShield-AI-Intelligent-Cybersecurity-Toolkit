"""Structural tests for the landing-hero capillary waves (no browser needed).

They check the source of components/landing.py and components/landing_css.py:
scoping, accessibility, reduced motion, and that only compositor-friendly
properties are animated. They do not prove how it looks; see
tests/test_landing_waves_browser.py for the (optional) rendering-engine checks.
"""

import re
import unittest

from components.landing_css import landing_css


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


CSS = landing_css()
NEW_START = CSS.index("/* ---------- hero shield: capillary waves")
NEW_END = CSS.index(".cs-l-chips { display: flex;")
NEW = CSS[NEW_START:NEW_END]
NEW_RULES = re.sub(r"/\*.*?\*/", "", NEW, flags=re.S)


class MarkupTests(unittest.TestCase):
    def setUp(self):
        self.src = _read("components/landing.py")

    def test_four_decorative_elements_are_aria_hidden(self):
        for cls in ('cs-l-wave w1', 'cs-l-wave w2', 'cs-l-wave w3', 'cs-l-glint'):
            self.assertIn(f'<div class="{cls}" aria-hidden="true"></div>', self.src, cls)

    def test_existing_shield_artwork_is_untouched_and_core_stays_on_top(self):
        self.assertIn('<div class="cs-l-shield"><div class="cs-l-ring r1"></div><div class="cs-l-ring r2"></div>', self.src)
        self.assertIn('<div class="cs-l-core">🛡️</div></div>', self.src)
        self.assertLess(self.src.index("cs-l-glint"), self.src.index("cs-l-core"))
        self.assertLess(self.src.index("cs-l-ring r2"), self.src.index("cs-l-wave w1"))

    def test_no_script_or_extra_widgets_added(self):
        import ast
        tree = ast.parse(self.src)
        strings = [n.value.lower() for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        for forbidden in ("<script", "<iframe", "javascript:"):
            self.assertFalse([t for t in strings if forbidden in t], forbidden)
        used = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        for forbidden in ("html", "rerun", "query_params"):
            self.assertNotIn(forbidden, used, forbidden)


class ExistingRulesPreservedTests(unittest.TestCase):
    def test_original_shield_rules_are_byte_identical(self):
        for rule in (
            ".cs-l-shield { position: relative; width: min(280px, 100%); aspect-ratio: 1 / 1; margin: 0 auto;\n"
            "  display: flex; align-items: center; justify-content: center; }",
            ".cs-l-ring { position: absolute; border-radius: 50%; border: 1px solid rgba(34,211,238,.28); }",
            ".cs-l-ring.r1 { inset: 0; }",
            ".cs-l-ring.r2 { inset: 14%; border-color: rgba(20,184,166,.38); }",
            "box-shadow: 0 0 40px rgba(34,211,238,.25); }",
            "  .cs-l-shield { width: min(210px, 70%); }",
        ):
            self.assertIn(rule, CSS)


class ScopingTests(unittest.TestCase):
    def test_every_new_selector_is_scoped_to_the_hero_shield(self):
        selectors = []
        for chunk in re.split(r"@keyframes[^{]+\{(?:[^{}]*\{[^}]*\})+\s*\}|@media[^{]+\{(?:[^{}]*\{[^}]*\})+\s*\}", NEW_RULES):
            selectors += [m.strip() for m in re.findall(r"([^{}]+)\{", chunk)]
        media = re.findall(r"@media[^{]+\{((?:[^{}]*\{[^}]*\})+)\s*\}", NEW_RULES)
        for body in media:
            selectors += [m.strip() for m in re.findall(r"([^{}]+)\{", body)]
        self.assertTrue(selectors)
        for sel in selectors:
            for part in sel.split(","):
                self.assertTrue(part.strip().startswith(".cs-l-shield "), part)

    def test_unique_names_and_no_collision_with_the_navigation_ripple(self):
        self.assertIn("@keyframes cs-l-wave-out", NEW)
        self.assertIn("@keyframes cs-l-glint-spin", NEW)
        self.assertNotIn("cs-ripple", CSS)
        self.assertNotIn("navtoggle", CSS)
        self.assertNotIn("::before", CSS)

    def test_nothing_global_is_touched(self):
        for forbidden in ("html", "body", ".stApp", ".block-container", "!important", "stSidebar", "stToolbar",
                          "stHeader", "display: none", "visibility: hidden", "url(", "http", "@import"):
            self.assertNotIn(forbidden, NEW_RULES, forbidden)


class AnimationQualityTests(unittest.TestCase):
    @staticmethod
    def _keyframes_body(name):
        start = NEW.index("{", NEW.index(f"@keyframes {name}")) + 1
        depth, k = 1, start
        while depth:
            depth += {"{": 1, "}": -1}.get(NEW[k], 0)
            k += 1
        return NEW[start:k - 1]

    def test_keyframes_animate_only_transform_and_opacity(self):
        for name in ("cs-l-wave-out", "cs-l-glint-spin"):
            body = re.sub(r"animation-timing-function:[^;]*;", "", self._keyframes_body(name))
            props = set(re.findall(r"([a-z-]+)\s*:", body))
            self.assertTrue(props and props <= {"transform", "opacity"}, (name, props))

    def test_waves_are_infinite_staggered_and_non_blocking(self):
        self.assertEqual(NEW_RULES.count("infinite"), 2)
        self.assertIn("animation-delay: -2.4s", NEW_RULES)
        self.assertIn("animation-delay: -4s", NEW_RULES)
        self.assertEqual(NEW_RULES.count("pointer-events: none"), 2)

    def test_waves_stay_inside_the_hero_box(self):
        self.assertIn("position: absolute; inset: 0;", NEW_RULES)   # full box, never larger
        self.assertIn("transform: scale(.46)", NEW_RULES)           # starts at the core's 46% diameter
        self.assertRegex(NEW_RULES, r"100%\s*\{ transform: scale\(1\); opacity: 0; \}")  # ends at the outer ring, invisible

    def test_no_heavy_effects(self):
        for heavy in ("filter", "blur", "backdrop", "box-shadow", "mix-blend"):
            self.assertNotIn(heavy, NEW_RULES, heavy)

    def test_reduced_motion_stops_all_motion_without_hiding_the_shield(self):
        m = re.search(r"@media \(prefers-reduced-motion: reduce\) \{(.*?)\n\}", NEW, flags=re.S)
        self.assertIsNotNone(m)
        block = m.group(1)
        self.assertIn(".cs-l-shield .cs-l-wave, .cs-l-shield .cs-l-glint { animation: none;", block)
        self.assertIn(".cs-l-wave.w1 { transform: scale(.74); opacity: .22; }", block)   # one still, faint ring
        self.assertNotIn("cs-l-core", block)
        self.assertNotIn("infinite", block)

    def test_css_block_stays_balanced(self):
        self.assertEqual(CSS.count("{"), CSS.count("}"))


if __name__ == "__main__":
    unittest.main()
