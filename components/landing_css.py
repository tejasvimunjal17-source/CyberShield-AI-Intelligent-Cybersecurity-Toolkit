"""Landing-page CSS. No Streamlit import (unit-testable).

Scope: styles only landing classes (.cs-l-*) and keyed containers/buttons
named landing_* (Streamlit adds a `st-key-<key>` class to keyed elements,
the same mechanism the floating CyberGuide panel already relies on). It does
not touch Streamlit's header, toolbar or sidebar (Part 1 owns those) and is
injected only while the landing view is shown, so nothing leaks into the app.
"""

from __future__ import annotations

_CSS = """
<style>
.stApp {
  background:
    radial-gradient(1000px 520px at 12% -5%, rgba(34,211,238,.13), transparent 60%),
    radial-gradient(900px 480px at 100% 0%, rgba(20,184,166,.10), transparent 55%),
    #0B1628;
}
.block-container { max-width: 1120px; padding-top: 1rem; padding-bottom: 3rem; }

/* ---------- top bar ---------- */
.st-key-landing_topbar {
  padding: 10px 16px; border: 1px solid #24405F; border-radius: 16px;
  background: rgba(18,35,61,.72);
}
.cs-l-bar { display: flex; align-items: center; justify-content: space-between; gap: 8px 22px; flex-wrap: wrap; }
.cs-l-brand { display: flex; align-items: center; gap: 10px; font-weight: 800;
  font-size: 1.15rem; letter-spacing: -.01em; color: #E6EEF8; }
.cs-l-logo { display: inline-flex; width: 36px; height: 36px; align-items: center;
  justify-content: center; border-radius: 10px; border: 1px solid rgba(34,211,238,.4);
  background: linear-gradient(135deg, rgba(34,211,238,.25), rgba(20,184,166,.18)); }
.cs-l-nav a { color: #9DB0C8 !important; text-decoration: none !important; font-weight: 600;
  padding: 6px 10px; border-radius: 8px; }
.cs-l-nav a:hover { color: #E6EEF8 !important; background: rgba(34,211,238,.10); }

/* ---------- hero ---------- */
.st-key-landing_hero {
  margin-top: 18px; padding: clamp(18px, 4vw, 44px); border: 1px solid #24405F; border-radius: 22px;
  background: linear-gradient(135deg, rgba(18,35,61,.95), rgba(11,22,40,.85));
  box-shadow: 0 0 60px rgba(34,211,238,.07);
}
.cs-l-eyebrow { display: inline-block; padding: 4px 12px; border-radius: 999px; font-size: .82rem;
  font-weight: 600; color: #22D3EE; border: 1px solid rgba(34,211,238,.35);
  background: rgba(34,211,238,.08); margin-bottom: 14px; }
.cs-l-h1 { font-size: clamp(2rem, 5.2vw, 3.3rem); font-weight: 800; line-height: 1.08;
  letter-spacing: -.025em; color: #E6EEF8; margin: 0 0 14px 0; }
.cs-l-grad { background: linear-gradient(90deg, #22D3EE, #14B8A6); -webkit-background-clip: text;
  background-clip: text; color: transparent; }
.cs-l-lead { font-size: 1.08rem; line-height: 1.6; color: #9DB0C8; max-width: 38rem; margin: 0 0 18px 0; }

.cs-l-shield { position: relative; width: min(280px, 100%); aspect-ratio: 1 / 1; margin: 0 auto;
  display: flex; align-items: center; justify-content: center; }
.cs-l-ring { position: absolute; border-radius: 50%; border: 1px solid rgba(34,211,238,.28); }
.cs-l-ring.r1 { inset: 0; }
.cs-l-ring.r2 { inset: 14%; border-color: rgba(20,184,166,.38); }
.cs-l-core { width: 46%; aspect-ratio: 1 / 1; border-radius: 50%; display: flex; align-items: center;
  justify-content: center; font-size: clamp(2.4rem, 8vw, 3.6rem);
  background: radial-gradient(circle, rgba(34,211,238,.28), rgba(34,211,238,.04) 70%);
  box-shadow: 0 0 40px rgba(34,211,238,.25); }
/* ---------- hero shield: capillary waves (decorative, landing-only) ----------
   Four aria-hidden elements inside .cs-l-shield. Each wave is a full-box circle drawn as a thin
   gradient ring (a faint leading ripple, a bright crest, a fading trail) that grows from the
   core's diameter (scale .46) out to the existing outer ring (scale 1) and fades, so nothing
   leaves the illustration box and the page size never changes. Only transform and opacity
   animate. The glint is a slow light sweep along the existing inner ring. */
.cs-l-shield .cs-l-wave { position: absolute; inset: 0; border-radius: 50%; pointer-events: none;
  opacity: 0; transform: scale(.46); will-change: transform, opacity;
  background: radial-gradient(closest-side, transparent 0, transparent 89.5%, rgba(34,211,238,.09) 90.8%,
    transparent 92.2%, transparent 95%, rgba(34,211,238,.08) 96.2%, rgba(94,234,212,.62) 98.4%,
    rgba(56,189,248,.14) 99.5%, transparent 100%);
  --cs-l-peak: .5; animation: cs-l-wave-out 6.6s linear infinite; }
.cs-l-shield .cs-l-wave.w2 { --cs-l-peak: .36; animation-duration: 7.2s; animation-delay: -2.4s; }
.cs-l-shield .cs-l-wave.w3 { --cs-l-peak: .26; animation-duration: 6s; animation-delay: -4s; }
/* Linear fade-in so a ring never pops into view, then ease-out like a ripple slowing as it spreads. */
@keyframes cs-l-wave-out {
  0%   { transform: scale(.46); opacity: 0; animation-timing-function: linear; }
  12%  { transform: scale(.54); opacity: var(--cs-l-peak, .4); animation-timing-function: cubic-bezier(.22,.61,.36,1); }
  100% { transform: scale(1); opacity: 0; }
}
.cs-l-shield .cs-l-glint { position: absolute; inset: 14%; border-radius: 50%; pointer-events: none; opacity: .55;
  background: conic-gradient(from 0deg, transparent 0deg, rgba(186,230,253,.55) 28deg, transparent 62deg,
    transparent 190deg, rgba(94,234,212,.45) 226deg, transparent 262deg, transparent 360deg);
  -webkit-mask-image: radial-gradient(closest-side, transparent calc(100% - 3px), #000 calc(100% - 2px),
    #000 calc(100% - .5px), transparent 100%);
  mask-image: radial-gradient(closest-side, transparent calc(100% - 3px), #000 calc(100% - 2px),
    #000 calc(100% - .5px), transparent 100%);
  will-change: transform; animation: cs-l-glint-spin 16s linear infinite; }
@keyframes cs-l-glint-spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) {
  .cs-l-shield .cs-l-wave, .cs-l-shield .cs-l-glint { animation: none; will-change: auto; }
  .cs-l-shield .cs-l-wave { opacity: 0; }
  .cs-l-shield .cs-l-wave.w1 { transform: scale(.74); opacity: .22; }   /* one still, faint ring */
  .cs-l-shield .cs-l-glint { opacity: .3; transform: rotate(40deg); }
}
.cs-l-chips { display: flex; gap: 8px; flex-wrap: wrap; justify-content: center; margin-top: 14px; }
.cs-l-chips span { font-size: .8rem; padding: 4px 10px; border-radius: 999px; color: #9DB0C8;
  border: 1px solid #24405F; background: rgba(18,35,61,.8); }

/* ---------- buttons ---------- */
[class*="st-key-landing_cta"] button {
  background: linear-gradient(135deg, #22D3EE, #14B8A6) !important; border: none !important;
  border-radius: 12px !important; min-height: 44px; font-weight: 700 !important;
  box-shadow: 0 6px 18px rgba(34,211,238,.22);
}
[class*="st-key-landing_cta"] button, [class*="st-key-landing_cta"] button * { color: #06121F !important; }
[class*="st-key-landing_cta"] button:hover { filter: brightness(1.07); }
[class*="st-key-landing_open_"] button {
  background: transparent !important; border: 1px solid rgba(34,211,238,.45) !important;
  border-radius: 10px !important;
}
[class*="st-key-landing_open_"] button, [class*="st-key-landing_open_"] button * { color: #22D3EE !important; }
[class*="st-key-landing_open_"] button:hover { background: rgba(34,211,238,.10) !important; }
.cs-l-btn2 { display: flex; align-items: center; justify-content: center; min-height: 44px; width: 100%;
  box-sizing: border-box; border-radius: 12px; font-weight: 700; text-decoration: none !important;
  color: #22D3EE !important; border: 1px solid rgba(34,211,238,.55); }
.cs-l-btn2:hover { background: rgba(34,211,238,.10); }

/* ---------- sections ---------- */
.cs-l-kicker { text-align: center; color: #14B8A6; font-weight: 700; font-size: .85rem;
  letter-spacing: .08em; text-transform: uppercase; margin-top: 56px; }
.cs-l-h2 { text-align: center; font-size: clamp(1.5rem, 3.6vw, 2.15rem); font-weight: 800;
  letter-spacing: -.02em; color: #E6EEF8; margin: 6px 0 22px 0; }

[class*="st-key-landing_card_"] {
  min-height: 262px; padding: 16px; border: 1px solid #24405F; border-radius: 16px; background: #12233D;
}
[class*="st-key-landing_card_"]:hover { border-color: rgba(34,211,238,.5); }
.cs-l-icon { display: inline-flex; width: 42px; height: 42px; align-items: center; justify-content: center;
  border-radius: 12px; font-size: 1.25rem; background: rgba(34,211,238,.10);
  border: 1px solid rgba(34,211,238,.28); margin-bottom: 10px; }
.cs-l-ctitle { font-weight: 700; font-size: 1.05rem; color: #E6EEF8; margin-bottom: 6px; }
.cs-l-cdesc { color: #9DB0C8; font-size: .93rem; line-height: 1.55; }

.cs-l-steps { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 14px; }
.cs-l-step { padding: 18px; border: 1px solid #24405F; border-radius: 16px; background: #12233D; }
.cs-l-num { display: inline-flex; width: 32px; height: 32px; align-items: center; justify-content: center;
  border-radius: 50%; font-weight: 800; color: #06121F; margin-bottom: 10px;
  background: linear-gradient(135deg, #22D3EE, #14B8A6); }

.cs-l-about { padding: clamp(16px, 3vw, 28px); border: 1px solid #24405F; border-radius: 18px; background: #12233D; }
.cs-l-about p { color: #9DB0C8; line-height: 1.6; margin: 0 0 14px 0; }
.cs-l-notes { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 10px; }
.cs-l-note { padding: 12px 14px; border-radius: 12px; border: 1px solid #24405F; border-left: 4px solid #FBBF24;
  background: rgba(11,22,40,.7); color: #E6EEF8; font-size: .92rem; line-height: 1.5; }

.st-key-landing_final {
  margin-top: 56px; padding: clamp(20px, 4vw, 40px); border: 1px solid #24405F; border-radius: 22px;
  background: linear-gradient(135deg, rgba(34,211,238,.12), rgba(20,184,166,.07) 55%, rgba(18,35,61,.9));
}
.cs-l-final { text-align: center; }
.cs-l-final .cs-l-h2 { margin-bottom: 8px; }
.cs-l-final p { color: #9DB0C8; margin: 0 auto 8px auto; max-width: 34rem; }

.cs-l-footer { margin-top: 48px; padding-top: 22px; border-top: 1px solid #24405F; color: #9DB0C8;
  font-size: .9rem; text-align: center; line-height: 1.6; }
.cs-l-footer strong { color: #E6EEF8; }
.cs-l-footer a { color: #9DB0C8 !important; text-decoration: none !important; margin: 0 8px; }
.cs-l-footer a:hover { color: #22D3EE !important; }

@media (max-width: 640px) {
  .block-container { padding-left: .8rem; padding-right: .8rem; }
  .cs-l-nav a { padding: 6px 8px; }
  .cs-l-kicker { margin-top: 40px; }
  [class*="st-key-landing_card_"] { min-height: 0; }
  .cs-l-shield { width: min(210px, 70%); }
}
</style>
"""


def landing_css() -> str:
    return _CSS
