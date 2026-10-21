# 🛡️ CyberShield AI

**Intelligent Security. Clear Insights. Safer Digital Experiences.**

An educational cybersecurity toolkit built with Python and Streamlit: inspect suspicious URLs, hash files, create and inspect QR codes, and learn the basics, with optional VirusTotal lookups and an AI guide (CyberGuide AI) powered by OpenRouter.

> Educational tool. It does not guarantee safety. Zero detections or "no heuristic signals" never prove that something is safe.

## What works today

A visitor first lands on a landing page (hero, features, how it works, about, footer). **Get Started** enters the app on the Overview Dashboard, where a 🛡️ shield button (top-left, with a subtle ripple animation that switches off for users who prefer reduced motion) opens the navigation sidebar and CyberGuide AI is available. The landing page itself shows neither. The sidebar lists all eight pages, highlights the current one, and closes when you choose a page; it starts closed. State is per browser session, so a refresh returns to the landing page.

| Module | What it does | Needs an API key? |
|---|---|---|
| Overview Dashboard | Service status, tool list | No |
| URL Security Scanner | Offline URL heuristics (never visits the link), defanged display, optional VirusTotal lookup, optional AI explanation | Optional |
| File Hash Analyzer | Local SHA-256/SHA-1/MD5, compare with a known hash, optional VirusTotal hash lookup | Optional |
| QR Code Generator | URL, text, Wi-Fi, email codes; color presets/custom colors; logo; size, border, error correction; PNG/JPG/SVG; decode check | No |
| QR Code Security Analyzer | Decodes an uploaded QR image locally, shows content as text, runs URL heuristics, optional VirusTotal lookup | Optional |
| Security Learning Center | Short static lessons | No |
| Settings & API Configuration | Shows whether keys are detected, how to set them | No |
| About | Data sharing table, limitations | No |
| **CyberGuide AI** (floating chat, every page) | Explains the app from `knowledge.md`; AI answers via OpenRouter, documentation fallback without it | Optional |

**Planned, not implemented:** AI Security Assistant (full page), Phishing Awareness Lab, Security Reports, QR frames/captions, QR PDF export, file/URL *submission* to VirusTotal (the app only reads existing reports).

## Configuration

| Name | Required? | Default |
|---|---|---|
| `OPENROUTER_API_KEY` | For AI answers only | none |
| `OPENROUTER_MODEL` | No | `openai/gpt-4o-mini` |
| `OPENROUTER_BASE_URL` | No | `https://openrouter.ai/api/v1` |
| `VIRUSTOTAL_API_KEY` | For VirusTotal lookups only | none |
| `APP_ENV` | No | `development` (set `production` to hide error details) |

The app starts and all local tools work with none of these set.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # optional; add keys if you have them
streamlit run streamlit_app.py
```

Run the tests:

```bash
python -m unittest discover -s tests -t . -v     # no extra tools needed
python -m pytest                                  # also works (pytest is in requirements.txt)
```

## Deploy to GitHub and Streamlit Community Cloud

1. Confirm `.env` and `.streamlit/secrets.toml` are **not** tracked (`git status`). They are in `.gitignore`.
2. `git init && git add . && git commit -m "CyberShield AI" ` then create a GitHub repo and push.
3. On Streamlit Community Cloud choose **Create app**, select the repo and branch, and set the main file to `streamlit_app.py`.
4. Open **Advanced settings → Secrets** and paste (only the keys you have):
   ```toml
   OPENROUTER_API_KEY = "..."
   VIRUSTOTAL_API_KEY = "..."
   APP_ENV = "production"
   ```
5. Deploy. After changing secrets later, reboot the app.

Preparing these files is not the same as deploying: this project has **not** been deployed or opened on Streamlit Community Cloud by its author tooling. Open your live URL and try each page before sharing it.

## Project layout

```
streamlit_app.py     entry point, router
app_registry.py      single source of truth for modules (navigation sidebar, dashboard, chatbot, tests)
config.py            secure config (env vars, then Streamlit secrets)
knowledge.md         CyberGuide AI's documentation (retrieved by section)
views/               one render() per page
components/          theme, navigation (shield drawer: shield_nav, nav_state, shield_nav_css; legacy sidebar), chrome CSS, landing page (landing, landing_css, app_state), cards, VirusTotal report UI, floating chat, Streamlit compat helper
backend/             url_analyzer, file_hashing, virustotal_client, openrouter_client, ai_explainer, security_utils
qr_tools/            generator (payloads, render, export), decoder (OpenCV)
cyberguide/          knowledge_base (retrieval), engine (answer logic)
content/             learning-center text, landing-page copy
tests/               unit tests (unittest-style; pytest-compatible)
docs/                architecture, setup, deployment, security, original project spec
```

`views/` is deliberately not named `pages/`: Streamlit auto-creates extra routes for a `pages/` folder.

## Testing status (what was and was not verified)

Last run in the development sandbox: **204 tests, all passed, 3 skipped** (`python -m unittest discover -s tests -t .`).

- Covered: URL heuristics, hashing against known vectors, payload builders, rendering/export, QR decoding (fixtures made by OpenCV's independent encoder), VirusTotal and OpenRouter clients **with mocked HTTP** (success, 404, 401/403, 429, 5xx, timeouts, malformed JSON, key never in error text, local rate guard), CyberGuide retrieval/fallback/redaction, consistency between `knowledge.md`, the registry and the router, the landing page, and the shield navigation drawer (state, ordering, routing, active highlight) via a stand-in Streamlit module.
- **Skipped (3):** generate→decode round trips that need the `qrcode` package, which was not installed in the sandbox. Run the tests on your machine after `pip install -r requirements.txt`; these should then execute.
- **Browser-engine test (optional):** `tests/test_shield_ripple_browser.py` loads the real shield CSS into a hand-built page that imitates Streamlit's DOM and checks it in Chromium via Playwright (animation curve, geometry, click-through, overflow, reduced motion). It is skipped automatically when Playwright or Chromium is missing; Playwright is not a project dependency.
- **Not verified:** the app running in real Streamlit (not installed in the sandbox), any live VirusTotal or OpenRouter request (no network or keys), the shield ripple and drawer inside the real Streamlit page or on Community Cloud, mobile layout on a real device, the floating-chat CSS in a browser, and the `qrcode` package's matrix API against the installed version.
- Pages were additionally executed against a stand-in `streamlit` module to catch name/signature errors. That proves the code paths run, not that they render correctly.

## Known limitations

- URL checks are heuristics; registered-domain detection is approximate (no full Public Suffix List).
- VirusTotal free tier: 4 lookups/minute, 500/day, non-commercial use. The app adds a process-wide 4/minute guard.
- AI output can be wrong and is labeled as an explanation, not a scan result.
- The Share / star / edit / GitHub icons are added by Streamlit Community Cloud. `toolbarMode = "minimal"` explicitly keeps them, so the app sets `[ui] hideTopBar = true` and also hides the toolbar and header with CSS selectors for Streamlit internals. Neither route has been checked in a browser, so the icons may still appear on your Streamlit version; see `docs/architecture.md`. If they do, send the element's `data-testid` (browser Inspect) so it can be targeted precisely, or deploy from a private repo. The Cloud "Manage app" control is outside the app and is not affected.
- The navigation sidebar is a fixed-position panel (same technique as the chat panel) that overlays the left side of the page. Its CSS (including the shield ripple) has been rendered in Chromium on a stand-in page, but not inside the real Streamlit app. There is no click-outside backdrop; close it with the shield button or by choosing a page. On phones it covers most of the width while open.
- The floating chat uses fixed-position CSS on a Streamlit container; it may need adjustment across Streamlit versions.
- Chat history lives in the browser session only.
- Refreshing the browser returns to the landing page (state is per session; no query parameters are used).
- The landing page's Features/About links are in-page anchors and the layout/CSS have not been inspected in a real browser. After clicking a lower Get Started button the app may open with the previous scroll position.
