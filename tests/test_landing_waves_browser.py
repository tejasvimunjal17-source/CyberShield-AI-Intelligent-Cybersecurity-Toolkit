"""Rendering-engine test of the landing-hero capillary waves in real Chromium.

WHAT THIS IS: the real hero HTML (captured by running components.landing.render_landing()
against tests/fake_streamlit.py) and the real CSS from components/landing_css.py are loaded
into a hand-built page that places the shield in a flex column. Chromium then computes
styles, animations, geometry, overflow and hit-testing.

WHAT THIS IS NOT: it is not the real Streamlit app. Streamlit's own column widths, theme,
header and Community Cloud page are not reproduced, so it cannot prove how the hero looks
inside Streamlit.

Optional: skipped automatically when Playwright or a launchable Chromium is missing.
Playwright is NOT a project dependency.
"""

import importlib
import sys
import unittest
from unittest import mock

from tests.fake_streamlit import FakeStreamlit

try:
    from playwright.sync_api import sync_playwright
    HAVE_PLAYWRIGHT = True
except ImportError:  # pragma: no cover
    HAVE_PLAYWRIGHT = False

VIEWPORTS = {"phone": {"width": 360, "height": 740}, "tablet": {"width": 768, "height": 900},
             "desktop": {"width": 1280, "height": 800}}


def real_hero_and_css():
    fs = FakeStreamlit()
    with mock.patch.dict(sys.modules, {"streamlit": fs.st}):
        for name in [m for m in list(sys.modules) if m.split(".")[0] in ("components", "views")]:
            del sys.modules[name]
        landing = importlib.import_module("components.landing")
        fs.st.columns.side_effect = lambda spec, **kw: [
            mock.MagicMock() for _ in (range(spec) if isinstance(spec, int) else spec)]
        landing.render_landing()
        html, css = fs.all_markdown(), importlib.import_module("components.landing_css").landing_css()
        for name in [m for m in list(sys.modules) if m.split(".")[0] in ("components", "views")]:
            sys.modules.pop(name, None)
    start = html.index('<div class="cs-l-shield">')
    chips = html.index('class="cs-l-chips"', start)
    return html[start:html.index("</div>", chips) + len("</div>")], css


def stand_in_page() -> str:
    hero, css = real_hero_and_css()
    return f"""<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<style>html,body{{margin:0;background:#0B1628;color:#E6EEF8;font-family:system-ui,sans-serif}}
.hero{{display:flex;flex-wrap:wrap;gap:16px;padding:16px;box-sizing:border-box}}
.copy{{flex:1 1 300px;min-width:0}} .art{{flex:1 1 260px;min-width:0}}</style>{css}</head>
<body><div class="hero"><div class="copy"><div class="cs-l-h1">Hero text</div>
<a id="cta" href="#x" style="display:inline-block;padding:12px 20px">Get Started</a></div>
<div class="art">{hero}</div></div>
<script>window.hits=0;document.getElementById('cta').addEventListener('click',e=>{{e.preventDefault();window.hits++}});</script>
</body></html>"""


JS_GEOM = """() => { const r = s => document.querySelector(s).getBoundingClientRect();
  const sh = r('.cs-l-shield'), core = r('.cs-l-core');
  return {shield: [sh.x, sh.y, sh.width, sh.height], core: [core.x, core.y, core.width, core.height],
          doc: [document.documentElement.scrollWidth, document.documentElement.clientWidth,
                document.documentElement.scrollHeight]}; }"""


@unittest.skipUnless(HAVE_PLAYWRIGHT, "Playwright not installed (optional)")
class LandingWavesBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = stand_in_page()
        try:
            cls.pw = sync_playwright().start()
            cls.browser = cls.pw.chromium.launch()
        except Exception as exc:  # pragma: no cover
            if hasattr(cls, "pw"):
                cls.pw.stop()
            raise unittest.SkipTest(f"Chromium cannot be launched here: {exc}")

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def open(self, vp="desktop", reduced=False):
        ctx = self.browser.new_context(viewport=VIEWPORTS[vp],
                                       reduced_motion="reduce" if reduced else "no-preference")
        self.addCleanup(ctx.close)
        page = ctx.new_page()
        page.set_content(self.html)
        page.wait_for_timeout(150)
        return page

    def test_four_infinite_animations_run_on_the_hero_only(self):
        page = self.open()
        info = page.evaluate("""() => document.querySelector('.cs-l-shield').getAnimations({subtree: true})
            .map(a => [a.animationName, a.playState, a.effect.getComputedTiming().iterations])""")
        names = sorted(n for n, _, _ in info)
        self.assertEqual(names, ["cs-l-glint-spin", "cs-l-wave-out", "cs-l-wave-out", "cs-l-wave-out"])
        self.assertTrue(all(state == "running" and it == float("inf") or it is None for _, state, it in info)
                        or all(state == "running" for _, state, _ in info))
        total = page.evaluate("document.getAnimations().length")
        self.assertEqual(total, 4)   # nothing else on the page is animated by this patch

    def test_waves_start_at_the_core_diameter_and_stay_centred_on_the_shield(self):
        for vp in VIEWPORTS:
            page = self.open(vp)
            page.evaluate("document.getAnimations().forEach(a => a.pause())")
            g = page.evaluate(JS_GEOM)
            sx, sy, sw, sh = g["shield"]
            cx, cy, cw, ch = g["core"]
            for t in (0, 1500, 3300, 5200):
                rects = page.evaluate("""(t) => { return [...document.querySelectorAll('.cs-l-wave')].map(w => {
                    w.getAnimations().forEach(a => { a.pause(); a.currentTime = t + 8000; });   // past any negative delay
                    const r = w.getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; }); }""", t)
                for x, y, w, h in rects:
                    self.assertAlmostEqual(x + w / 2, sx + sw / 2, delta=1.0, msg=f"{vp} t={t} cx")
                    self.assertAlmostEqual(y + h / 2, sy + sh / 2, delta=1.0, msg=f"{vp} t={t} cy")
                    self.assertLessEqual(w, sw + 0.5, f"{vp}: wave wider than the hero box")
                    self.assertGreaterEqual(w, cw - 1.0, f"{vp}: wave smaller than the core")
            self.assertAlmostEqual(cx + cw / 2, sx + sw / 2, delta=1.0)   # core itself is centred

    def test_every_wave_is_born_at_the_core_edge_and_dies_at_the_outer_ring(self):
        # Deterministic: remove each wave's (negative) delay and jump to the very start / end of its cycle.
        for vp in VIEWPORTS:
            page = self.open(vp)
            res = page.evaluate("""() => { const core = document.querySelector('.cs-l-core').getBoundingClientRect();
              const sh = document.querySelector('.cs-l-shield').getBoundingClientRect();
              const rows = [];
              for (const w of document.querySelectorAll('.cs-l-wave')) {
                const a = w.getAnimations()[0]; a.effect.updateTiming({delay: 0}); a.pause();
                const dur = a.effect.getComputedTiming().duration;
                const at = p => { a.currentTime = p * dur; const c = getComputedStyle(w);
                                  return {w: w.getBoundingClientRect().width, o: parseFloat(c.opacity)}; };
                rows.push({start: at(0), peak: at(0.12), end: at(0.999999)});
              }
              return {core: core.width, shield: sh.width, rows}; }""")
            for row in res["rows"]:
                self.assertAlmostEqual(row["start"]["w"], res["core"], delta=1.0, msg=f"{vp}: not born at the core edge")
                self.assertEqual(row["start"]["o"], 0, f"{vp}: a ring pops into view")
                self.assertGreater(row["peak"]["o"], 0.2, f"{vp}: ring never becomes visible")
                self.assertAlmostEqual(row["end"]["w"], res["shield"], delta=1.5, msg=f"{vp}: not ending at the outer ring")
                self.assertLess(row["end"]["o"], 0.01, f"{vp}: ring still visible at the outer ring")

    def test_waves_never_leave_the_hero_box_at_any_phase(self):
        page = self.open("phone")
        bad = page.evaluate("""() => { const sh = document.querySelector('.cs-l-shield').getBoundingClientRect(); const out = [];
          for (const w of document.querySelectorAll('.cs-l-wave')) {
            w.getAnimations().forEach(a => a.pause());
            for (let t = 0; t <= 7000; t += 250) {
              w.getAnimations().forEach(a => a.currentTime = t + 8000);
              const r = w.getBoundingClientRect();
              if (r.left < sh.left - 0.6 || r.right > sh.right + 0.6 || r.top < sh.top - 0.6 || r.bottom > sh.bottom + 0.6)
                out.push([w.className, t]);
            } } return out; }""")
        self.assertEqual(bad, [])

    def test_glint_is_a_circle_inside_the_hero_box_and_only_rotates(self):
        # The glint is a square box with border-radius 50% that rotates about its centre. The browser's
        # bounding rectangle of a rotated square is larger than the circle that is actually painted, so the
        # invariants checked here are the un-rotated layout box and the circular shape, not getBoundingClientRect.
        page = self.open("phone")
        info = page.evaluate("""() => { const g = document.querySelector('.cs-l-glint'), s = document.querySelector('.cs-l-shield');
          const c = getComputedStyle(g);
          return {l: g.offsetLeft, t: g.offsetTop, w: g.offsetWidth, h: g.offsetHeight, sw: s.offsetWidth, sh: s.offsetHeight,
                  radius: c.borderRadius, origin: c.transformOrigin, w2: parseFloat(c.width), h2: parseFloat(c.height)}; }""")
        self.assertGreaterEqual(info["l"], 0)
        self.assertGreaterEqual(info["t"], 0)
        self.assertLessEqual(info["l"] + info["w"], info["sw"])
        self.assertLessEqual(info["t"] + info["h"], info["sh"])
        self.assertEqual(info["w"], info["h"])
        self.assertEqual(info["radius"], "50%")
        ox, oy = (float(v.rstrip("px")) for v in info["origin"].split())
        self.assertAlmostEqual(ox, info["w2"] / 2, delta=0.01)    # rotates about its own centre
        self.assertAlmostEqual(oy, info["h2"] / 2, delta=0.01)

    def test_worst_case_tight_container_still_has_no_horizontal_scroll(self):
        # The shield fills a container that is exactly as wide as the viewport, with the glint at 45 degrees.
        hero, css = real_hero_and_css()
        html = (f'<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">'
                f'<style>html,body{{margin:0}} #c{{width:200px}} {css}</style></head><body><div id="c">{hero}</div></body></html>')
        ctx = self.browser.new_context(viewport={"width": 200, "height": 400})
        self.addCleanup(ctx.close)
        page = ctx.new_page()
        page.set_content(html)
        page.evaluate("document.querySelectorAll('.cs-l-shield *').forEach(e => e.getAnimations().forEach(a => a.pause()))")
        page.evaluate("document.querySelector('.cs-l-glint').getAnimations().forEach(a => a.currentTime = 2000)")
        self.assertEqual(page.evaluate("getComputedStyle(document.querySelector('.cs-l-glint')).transform"),
                         "matrix(0.707107, 0.707107, -0.707107, 0.707107, 0, 0)")
        self.assertEqual(page.evaluate("document.documentElement.scrollWidth"), 200)

    def test_no_horizontal_scroll_and_layout_is_identical_with_or_without_waves(self):
        for vp in VIEWPORTS:
            page = self.open(vp)
            with_waves = page.evaluate(JS_GEOM)
            sw, cw, _ = with_waves["doc"]
            self.assertLessEqual(sw, cw, f"{vp}: horizontal overflow")
            page.evaluate("document.querySelectorAll('.cs-l-wave, .cs-l-glint').forEach(e => e.remove())")
            without = page.evaluate(JS_GEOM)
            self.assertEqual(with_waves, without, f"{vp}: the decorative elements changed the layout")

    def test_decorative_layers_do_not_block_clicks_or_touch(self):
        page = self.open("phone")
        info = page.evaluate("""() => { const sh = document.querySelector('.cs-l-shield').getBoundingClientRect();
          const hit = document.elementFromPoint(sh.x + sh.width / 2, sh.y + sh.height / 2);
          const edge = document.elementFromPoint(sh.x + sh.width * .5, sh.y + sh.height * .02);
          return {pe: [...document.querySelectorAll('.cs-l-wave, .cs-l-glint')].map(e => getComputedStyle(e).pointerEvents),
                  centre: hit.className, edge: edge.className,
                  hidden: [...document.querySelectorAll('.cs-l-wave, .cs-l-glint')].map(e => e.getAttribute('aria-hidden'))}; }""")
        self.assertEqual(set(info["pe"]), {"none"})
        self.assertEqual(set(info["hidden"]), {"true"})
        self.assertNotIn("wave", info["centre"] + info["edge"])
        self.assertNotIn("glint", info["centre"] + info["edge"])
        page.click("#cta")
        self.assertEqual(page.evaluate("window.hits"), 1)

    def test_only_transform_and_opacity_change_while_animating(self):
        page = self.open()
        changed = page.evaluate("""() => { const w = document.querySelector('.cs-l-wave.w1');
          const props = new Set();
          w.getAnimations().forEach(a => a.effect.getKeyframes().forEach(k => Object.keys(k).forEach(p => props.add(p))));
          return [...props].filter(p => !['offset','computedOffset','easing','composite'].includes(p)).sort(); }""")
        self.assertEqual(changed, ["opacity", "transform"])

    def test_reduced_motion_leaves_a_static_faint_ring_and_no_animation(self):
        for vp in ("phone", "desktop"):
            page = self.open(vp, reduced=True)
            self.assertEqual(page.evaluate("document.getAnimations().length"), 0, vp)
            ops = page.evaluate("""() => [...document.querySelectorAll('.cs-l-wave')].map(w => {
                const c = getComputedStyle(w); return [c.opacity, c.transform]; })""")
            self.assertEqual([o for o, _ in ops], ["0.22", "0", "0"])
            self.assertNotEqual(ops[0][1], "none")                 # the one faint ring is scaled (.74), not at the core size
            core_ok = page.evaluate("""() => { const c = getComputedStyle(document.querySelector('.cs-l-core'));
                return [c.opacity, c.display]; }""")
            self.assertEqual(core_ok, ["1", "flex"])               # the shield itself is untouched
            self.assertEqual(page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"), True)

    def test_motion_run_really_changes_what_is_painted(self):
        page = self.open("desktop")
        page.evaluate("document.getAnimations().forEach(a => a.pause())")
        def frame(t):
            page.evaluate("(t) => document.querySelectorAll('.cs-l-shield *').forEach(e => e.getAnimations().forEach(a => a.currentTime = t))", t)
            box = page.eval_on_selector(".cs-l-shield", "e => { const r=e.getBoundingClientRect(); return {x:r.x,y:r.y,width:r.width,height:r.height}; }")
            return page.screenshot(clip=box)
        self.assertNotEqual(frame(8700), frame(10900))   # different phases render differently


if __name__ == "__main__":
    unittest.main()
