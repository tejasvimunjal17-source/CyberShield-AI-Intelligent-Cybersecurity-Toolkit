"""Rendering-engine test of the shield ripple CSS in real Chromium.

WHAT THIS IS: the real CSS from components/shield_nav_css.py is loaded into a
hand-built HTML page that imitates Streamlit's structure (keyed containers
carry `st-key-<key>` classes, an inner scroll container, a flex vertical block).
Chromium then computes styles, animations, geometry and hit-testing.

WHAT THIS IS NOT: it is not the real Streamlit app, so it cannot show how the
shield and rings look inside Streamlit's actual DOM, header, theme or Community
Cloud page.

Optional: skipped automatically when Playwright or a launchable Chromium is not
installed. Playwright is NOT a project dependency.
"""

import re
import unittest

from components.shield_nav_css import shield_nav_css

try:
    from playwright.sync_api import sync_playwright
    HAVE_PLAYWRIGHT = True
except ImportError:  # pragma: no cover
    HAVE_PLAYWRIGHT = False

DESKTOP = {"width": 1280, "height": 800}
MOBILE = {"width": 390, "height": 844}
PERIOD_MS = 3600


def stand_in_page() -> str:
    css = shield_nav_css().replace("<style>", "").replace("</style>", "")
    return f"""<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<style>
html,body {{ margin:0; height:100%; background:#0B1628; color:#E6EEF8; font-family:system-ui,sans-serif; }}
.stApp {{ height:100vh; overflow:auto; }}
.block-container {{ max-width:1100px; margin:0 auto; padding:6rem 1rem 3rem; }}
.stVerticalBlock {{ display:flex; flex-direction:column; gap:1rem; }}
.stElementContainer {{ width:100%; }}
button {{ font:inherit; cursor:pointer; color:inherit; }}
{css}
</style></head><body>
<div class="stApp"><div class="block-container">
  <h1 id="first">Overview Dashboard</h1><p>Page content that must stay readable and clickable.</p>
  <p style="height:1400px">Tall content so the inner container scrolls.</p>
</div></div>
<a id="under" href="#x" style="position:absolute;left:36px;top:52px;width:40px;height:20px;display:block;background:#345">u</a>
<div class="stVerticalBlock st-key-cybershield_navtoggle_box">
  <div class="stElementContainer st-key-cybershield_navtoggle_btn"><div class="stButton"><div><button id="shield">🛡️</button></div></div></div>
</div>
<script>
window.clicks = 0; window.under = 0;
document.getElementById('shield').addEventListener('click', () => window.clicks++);
document.getElementById('under').addEventListener('click', e => {{ e.preventDefault(); window.under++; }});
</script></body></html>"""


JS_PSEUDO = """(pseudo) => { const b = document.querySelector('[class*="st-key-cybershield_navtoggle_box"]');
  const c = getComputedStyle(b, pseudo);
  return {animationName: c.animationName, iteration: c.animationIterationCount, pe: c.pointerEvents,
          position: c.position, z: c.zIndex, w: c.width, h: c.height, radius: c.borderRadius, opacity: c.opacity}; }"""

JS_SAMPLE = """(count) => { const b = document.querySelector('[class*="st-key-cybershield_navtoggle_box"]');
  const anims = b.getAnimations({subtree: true}).filter(a => a.animationName === 'cs-ripple');
  anims.forEach(a => a.pause());
  const out = [];
  for (const a of anims) {
    const rows = [];
    for (let i = 0; i < count; i++) {          // t in [0, 3600): 3600 itself wraps to the next cycle
      a.currentTime = (i / count) * 3600;
      const c = getComputedStyle(b, a.effect.pseudoElement);
      const m = c.transform === 'none' ? 1 : parseFloat(c.transform.slice(7));
      rows.push({t: a.currentTime, opacity: parseFloat(c.opacity), scale: m});
    }
    out.push({pseudo: a.effect.pseudoElement, delay: a.effect.getTiming().delay,
              duration: a.effect.getTiming().duration, rows});
  }
  return out; }"""


@unittest.skipUnless(HAVE_PLAYWRIGHT, "Playwright is not installed (optional)")
class ShieldRippleBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        try:
            cls.browser = cls.pw.chromium.launch()
        except Exception as exc:  # no Chromium binary
            cls.pw.stop()
            raise unittest.SkipTest(f"Chromium not launchable: {str(exc).splitlines()[0][:100]}")

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def open(self, viewport=DESKTOP, reduced=False):
        ctx = self.browser.new_context(viewport=viewport, reduced_motion="reduce" if reduced else "no-preference")
        self.addCleanup(ctx.close)
        page = ctx.new_page()
        page.set_content(stand_in_page())
        return page

    # ---- the rings ------------------------------------------------------------
    def test_ring_pseudo_elements_computed_styles(self):
        page = self.open()
        for pseudo in ("::before", "::after"):
            c = page.evaluate(JS_PSEUDO, pseudo)
            self.assertEqual(c["animationName"], "cs-ripple", pseudo)
            self.assertEqual(c["iteration"], "infinite", pseudo)
            self.assertEqual(c["pe"], "none", pseudo)
            self.assertEqual(c["position"], "absolute", pseudo)
            self.assertEqual(c["z"], "-1", pseudo)
            self.assertEqual((c["w"], c["h"]), ("44px", "44px"), pseudo)
            self.assertEqual(c["radius"], "50%", pseudo)

    def test_two_staggered_rings_with_smooth_fade_and_small_growth(self):
        page = self.open()
        count = 36
        rings = {r["pseudo"]: r for r in page.evaluate(JS_SAMPLE, count)}
        self.assertEqual(sorted(rings), ["::after", "::before"])
        first, second = rings["::before"], rings["::after"]
        self.assertEqual((first["delay"], second["delay"]), (0, -1800))
        self.assertEqual((first["duration"], second["duration"]), (PERIOD_MS, PERIOD_MS))
        o1 = [r["opacity"] for r in first["rows"]]
        s1 = [r["scale"] for r in first["rows"]]
        o2 = [r["opacity"] for r in second["rows"]]
        s2 = [r["scale"] for r in second["rows"]]

        # ring 1 runs from the start of its cycle: begins invisible at scale 1
        self.assertAlmostEqual(o1[0], 0, places=2)
        self.assertAlmostEqual(s1[0], 1.0, places=2)
        # bounds for BOTH rings: never flashes, never grows beyond 1.45
        for o, sc in ((o1, s1), (o2, s2)):
            self.assertLessEqual(max(o), 0.51, "peak opacity stays at about .5 (no flashing)")
            self.assertGreaterEqual(max(o), 0.45)
            self.assertGreaterEqual(min(o), 0)
            self.assertGreaterEqual(min(sc), 0.999)
            self.assertLessEqual(max(sc), 1.451)
        # ring 1: rings only ever expand, and fade out monotonically after the peak
        self.assertEqual(s1, sorted(s1))
        peak = o1.index(max(o1))
        self.assertEqual(o1[peak:], sorted(o1[peak:], reverse=True))
        self.assertLess(o1[-1], 0.06, "ring is nearly invisible just before it restarts")
        self.assertGreater(s1[-1], 1.43, "ring has reached its full size by the end of the cycle")
        # smoothness: no abrupt opacity jumps (including across the wrap-around)
        for o in (o1, o2):
            steps = [abs(b - a) for a, b in zip(o + o[:1], (o + o[:1])[1:])]
            self.assertLess(max(steps), 0.2)
        # stagger: ring 2 is exactly ring 1 shifted by half a period
        shift = count // 2
        for i in range(count):
            self.assertAlmostEqual(o2[i], o1[(i + shift) % count], delta=0.02)
            self.assertAlmostEqual(s2[i], s1[(i + shift) % count], delta=0.02)

    def test_rings_stay_inside_viewport_and_reserved_top_padding(self):
        page = self.open()
        box = page.evaluate("""() => {const r = document.querySelector('[class*="st-key-cybershield_navtoggle_box"]').getBoundingClientRect();
                               return {x:r.x,y:r.y,w:r.width,h:r.height}}""")
        self.assertEqual(box, {"x": 12, "y": 10, "w": 44, "h": 44})
        cx, cy = box["x"] + 22, box["y"] + 22
        reach = 22 * 1.45
        self.assertGreaterEqual(cx - reach, 0)
        self.assertGreaterEqual(cy - reach, 0)
        padding_top = page.evaluate("parseFloat(getComputedStyle(document.querySelector('.block-container')).paddingTop)")
        self.assertEqual(padding_top, 64)
        self.assertLessEqual(cy + reach, padding_top + 0.5, "rings stay inside the top padding reserved for the shield")
        first = page.evaluate("document.getElementById('first').getBoundingClientRect().top")
        self.assertGreaterEqual(first, padding_top)

    # ---- the shield stays stable and clickable ------------------------------------------
    def test_button_geometry_is_stable_while_animating(self):
        page = self.open()
        rects = []
        for t in (0, 700, 1500, 2600, 3500):
            page.evaluate(f"document.getAnimations({{subtree:true}}).forEach(a => {{a.pause(); a.currentTime = {t};}})")
            rects.append(page.evaluate("""() => {const r = document.getElementById('shield').getBoundingClientRect();
                                         return [r.x, r.y, r.width, r.height]}"""))
        self.assertEqual(len({tuple(r) for r in rects}), 1)
        self.assertEqual(rects[0][2:], [44, 44])
        radius = page.evaluate("getComputedStyle(document.getElementById('shield')).borderRadius")
        self.assertEqual(radius, "50%")

    def test_shield_is_clickable_while_rings_animate(self):
        page = self.open()
        page.mouse.click(34, 32)                              # button centre
        page.click("#shield")                                  # Playwright's own actionability checks
        page.focus("#shield")
        page.keyboard.press("Enter")                           # keyboard activation
        self.assertEqual(page.evaluate("window.clicks"), 3)

    def test_rings_do_not_intercept_pointer_events(self):
        page = self.open()
        # (46, 58) is inside the largest ring's reach but outside the button: it must hit the page element underneath.
        page.mouse.click(46, 58)
        self.assertEqual(page.evaluate("window.under"), 1)
        self.assertEqual(page.evaluate("window.clicks"), 0)
        hit = page.evaluate("document.elementFromPoint(46, 58).id")
        self.assertEqual(hit, "under")

    # ---- overflow ----------------------------------------------------------------------------
    def test_no_scrollbars_or_extra_scroll_height_on_desktop_and_mobile(self):
        for viewport in (DESKTOP, MOBILE):
            page = self.open(viewport)
            def measure():
                return page.evaluate("""() => {const s = document.querySelector('.stApp'), d = document.documentElement;
                    return {docW: d.scrollWidth - d.clientWidth, appW: s.scrollWidth - s.clientWidth, appH: s.scrollHeight}}""")
            animated = measure()
            page.add_style_tag(content='[class*="st-key-cybershield_navtoggle_box"]::before,'
                                       '[class*="st-key-cybershield_navtoggle_box"]::after{animation:none!important}')
            still = measure()
            self.assertEqual(animated["docW"], 0, viewport)
            self.assertEqual(animated["appW"], 0, viewport)
            self.assertEqual(animated["appH"], still["appH"], f"rings must not add scroll height at {viewport}")

    # ---- reduced motion -------------------------------------------------------------------------
    def test_reduced_motion_disables_ripples_but_not_the_button(self):
        page = self.open(reduced=True)
        for pseudo in ("::before", "::after"):
            c = page.evaluate(JS_PSEUDO, pseudo)
            self.assertEqual(c["animationName"], "none", pseudo)
            self.assertEqual(c["opacity"], "0", pseudo)
        count = page.evaluate("""() => document.querySelector('[class*="st-key-cybershield_navtoggle_box"]')
                                 .getAnimations({subtree:true}).filter(a => a.animationName === 'cs-ripple').length""")
        self.assertEqual(count, 0)
        page.click("#shield")
        self.assertEqual(page.evaluate("window.clicks"), 1)
        visible = page.evaluate("getComputedStyle(document.getElementById('shield')).visibility")
        self.assertEqual(visible, "visible")


if __name__ == "__main__":
    unittest.main()
