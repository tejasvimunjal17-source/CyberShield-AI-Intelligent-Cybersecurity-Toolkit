<div align="center">

# 🛡️ CyberShield AI

### Intelligent Security. Clear Insights. Safer Digital Experiences.

An educational cybersecurity toolkit built with Python and Streamlit.<br>
Inspect URLs, hash files, create and inspect QR codes, and learn the fundamentals, with optional VirusTotal lookups and an AI guide.

![Python](https://img.shields.io/badge/Python-3-0b1f3a?style=flat&logo=python&logoColor=22d3ee)
![Streamlit](https://img.shields.io/badge/Built%20with-Streamlit-0b1f3a?style=flat&logo=streamlit&logoColor=14b8a6)

</div>

<!--
SCREENSHOT PLACEHOLDER
No screenshot path was verified when this README was written.
To add one later: save an image in the repository (for example under docs/) and insert:

<p align="center"><img src="docs/screenshot.png" alt="CyberShield AI dashboard" width="800"></p>

Update the path to match the real file.
-->

> **Educational tool.** CyberShield AI cannot guarantee that a URL, file, or QR code is safe. Zero detections or "no heuristic signals" never prove safety.

---

## Contents

[Overview](#overview) · [Features](#features) · [QR Code Generator](#qr-code-generator) · [Shield navigation](#shield-navigation-and-animation) · [CyberGuide AI](#cyberguide-ai) · [Security and privacy](#security-and-privacy) · [Tech stack](#technology-stack) · [Installation](#installation-and-setup) · [Configuration](#configuration) · [Deployment](#deployment) · [Structure](#project-structure) · [Testing](#testing-and-verification) · [Roadmap](#roadmap) · [Limitations](#limitations-and-responsible-use) · [Contributing and license](#contributing-and-license)

---

## Overview

CyberShield AI is a learning-focused toolkit. It helps you:

- Inspect suspicious URLs with local heuristics.
- Calculate file hashes and optionally check them through VirusTotal.
- Generate customized QR codes.
- Decode QR images and inspect their contents.
- Learn cybersecurity basics.
- Get optional AI-powered explanations from CyberGuide AI.

### What stays local and what leaves your machine

| Type | Operations |
|---|---|
| 🔒 **Local processing** | URL heuristics (the link is never visited), file hashing, QR generation, QR decoding, learning content, documentation-based CyberGuide answers |
| 🌐 **External API calls (optional)** | VirusTotal hash, URL, and QR-URL lookups; opt-in VirusTotal submissions |
| 🤖 **Optional AI service** | CyberGuide AI and URL explanations through OpenRouter |

The app starts, and every local tool works, with no API keys configured.

---

## Features

The app opens on a landing page. **Get Started** enters the app on the Overview Dashboard, and the sidebar lists all eight pages.

| # | Page | What it does | API key |
|---|---|---|---|
| 1 | **Overview Dashboard** | Service status and tool list | None |
| 2 | **URL Security Scanner** | Offline URL heuristics, defanged URL display, optional VirusTotal lookup, optional AI explanation | Optional |
| 3 | **File Hash Analyzer** | Local SHA-256, SHA-1, and MD5; comparison with a known hash; optional VirusTotal hash lookup | Optional |
| 4 | **QR Code Generator** | URL, text, Wi-Fi, and email codes with styling and export options ([details](#qr-code-generator)) | None |
| 5 | **QR Code Security Analyzer** | Decodes an uploaded QR image locally, shows the content as text, runs URL heuristics, optional VirusTotal lookup | Optional |
| 6 | **Security Learning Center** | Short static lessons | None |
| 7 | **Settings & API Configuration** | Shows whether keys are detected and how to set them | None |
| 8 | **About CyberShield AI** | Data-sharing table and limitations | None |
| ★ | **CyberGuide AI** | Floating chat available on every app page ([details](#cyberguide-ai)) | Optional |

---

## QR Code Generator

### Available today

| Area | Capability |
|---|---|
| Content types | URL, text, Wi-Fi, email |
| Colors | Color presets and custom colors |
| Branding | Logo upload |
| Technical settings | Output size, border (quiet zone), error-correction level |
| Export | PNG, JPG, SVG |
| Verification | Decode check |

### Advanced customization roadmap

> **Status: planned or in progress.** Nothing in this table is presented as implemented.

| Category | Planned enhancements |
|---|---|
| Patterns and shapes | Rounded or dot-style modules, custom corner-eye styles, geometric patterns |
| Colors and design | Two-color gradients (linear and radial), optional transparent background |
| Branding | Centered logo with adjustable size and margin, reusable design presets |
| Frames and calls to action | Decorative frames, custom text such as "Scan Me" or "Visit Website", text and frame styling |
| Technical settings | Error-correction levels L, M, Q, and H as an explicit selector, extended quiet-zone control, high-resolution output |
| Export formats | PDF (planned); TIFF or EPS only if genuinely supported |
| Content types | vCard, WhatsApp, SMS, calendar events, hosted document links |

### About document QR codes

A normal QR code cannot embed a PDF, DOCX, or other document. It stores a **URL that points to a hosted copy** of the file. The planned "hosted document link" type will work this way.

---

## Shield navigation and animation

- A 🛡️ shield button (top-left, shown inside the app but not on the landing page) opens the navigation sidebar.
- The sidebar starts closed, highlights the current page, and closes when you choose a page.
- The shield has a subtle ripple animation that switches off for users who prefer reduced motion.

**Planned enhancement: capillary-wave ripples.** The intended effect is subtle, expanding ripples around the shield while preserving the existing interface. This enhancement is **not yet documented as deployed or browser-tested**.

---

## CyberGuide AI

CyberGuide AI is the in-app assistant, available from a floating chat on every app page.

- **Purpose:** explains how the app works and answers questions about its tools.
- **Knowledge base:** answers are drawn from the project's `knowledge.md`, retrieved by section.
- **OpenRouter:** when `OPENROUTER_API_KEY` is set, answers are generated through the OpenRouter API.
- **Without the AI service:** CyberGuide falls back to answers from the documentation.
- **Chat history** lives only in the browser session.

> AI-generated explanations may be inaccurate. They are explanations, not scan results or definitive security verdicts.

---

## Security and privacy

| Behavior | Detail |
|---|---|
| 🔒 URL checks | Heuristics run locally; the app never visits the submitted URL |
| 🔒 File hashing | SHA-256, SHA-1, and MD5 are computed locally |
| 🔒 File safety | Uploaded files are never executed |
| 🌐 VirusTotal | Lookups and submissions are optional and need `VIRUSTOTAL_API_KEY` |
| 🌐 New submissions | Never automatic. URL analysis requests and file uploads (up to 25 MB, original file name withheld) need a privacy-notes acknowledgment and a per-item confirmation |
| ⚠️ Shared files | Files uploaded to VirusTotal are shared with its security community. Do not upload confidential files |
| 🔑 API keys | Store them in environment variables or Streamlit secrets, never in source code |

No tool here can guarantee that a URL, file, or QR code is safe.

---

## Technology stack

| Technology | Role |
|---|---|
| Python | Application language |
| Streamlit | Web interface |
| VirusTotal API | Optional reputation lookups and submissions |
| OpenRouter API | Optional AI answers |
| `qrcode` | QR generation |
| OpenCV | QR decoding |
| pytest | Test runner (listed in `requirements.txt`; the suite also runs with `unittest`) |

Source: the previous README and its `qr_tools/` description. Check `requirements.txt` for the authoritative dependency list and versions.

---

## Installation and setup

**Prerequisites:** Python 3, Git, and optionally a VirusTotal and/or OpenRouter API key.

```bash
# 1. Clone (replace with your repository URL)
git clone <your-repository-url>
cd <repository-folder>

# 2. Create a virtual environment
python -m venv .venv

# 3. Activate it
source .venv/bin/activate          # macOS / Linux
.venv\Scripts\activate             # Windows

# 4. Install dependencies
pip install -r requirements.txt

# 5. Optional: configure API keys
cp .env.example .env               # Windows: copy .env.example .env

# 6. Run the app
streamlit run streamlit_app.py
```

**Run the tests:**

```bash
python -m unittest discover -s tests -t . -v
python -m pytest
```

---

## Configuration

| Variable | Required? | Default | Used for |
|---|---|---|---|
| `OPENROUTER_API_KEY` | Optional | none | AI answers and explanations |
| `OPENROUTER_MODEL` | Optional | `openai/gpt-4o-mini` | AI model selection |
| `OPENROUTER_BASE_URL` | Optional | `https://openrouter.ai/api/v1` | OpenRouter endpoint |
| `VIRUSTOTAL_API_KEY` | Optional | none | VirusTotal lookups and opt-in submissions |
| `APP_ENV` | Optional | `development` | Set to `production` to hide error details |

No configuration is required to run the local tools. Never commit real keys.

---

## Deployment

1. Confirm `.env` and `.streamlit/secrets.toml` are **not** tracked (`git status`). Both are listed in `.gitignore`.
2. Push the repository to GitHub.
3. On Streamlit Community Cloud choose **Create app**, select the repository and branch, and set the main file to `streamlit_app.py`.
4. Open **Advanced settings → Secrets** and add only the keys you have:
   ```toml
   OPENROUTER_API_KEY = "..."
   VIRUSTOTAL_API_KEY = "..."
   APP_ENV = "production"
   ```
5. Deploy. Reboot the app after changing secrets later.

> Preparing these instructions is not the same as deploying. This project has **not** been verified as deployed or opened on Streamlit Community Cloud. Open your live URL and test each page before sharing it.

---

## Project structure

```text
streamlit_app.py     Entry point and router
app_registry.py      Single source of truth for modules
config.py            Config: environment variables, then Streamlit secrets
knowledge.md         CyberGuide AI documentation
views/               One render() per page
components/          Theme, shield navigation, landing page, cards, VirusTotal UI, floating chat
backend/             URL analysis, hashing, VirusTotal and OpenRouter clients, AI explainer
qr_tools/            QR generator (payloads, render, export) and decoder (OpenCV)
cyberguide/          Knowledge retrieval and answer logic
content/             Learning-center and landing-page text
tests/               Unit tests (unittest-style, pytest-compatible)
docs/                Architecture, setup, deployment, security, original spec
```

`views/` is intentionally not named `pages/`, because Streamlit would create extra routes for a `pages/` folder.

---

## Testing and verification

> **Previous result, not a check of the current tree:** 204 tests, all passed, 3 skipped, run in a development sandbox with `python -m unittest discover -s tests -t .`

| Category | Status |
|---|---|
| Unit tests | URL heuristics, hashing against known vectors, payload builders, rendering and export, QR decoding, CyberGuide retrieval and fallback, registry and router consistency, landing page, shield navigation logic |
| Mocked API tests | VirusTotal and OpenRouter clients with mocked HTTP (success, 404, 401/403, 429, 5xx, timeouts, malformed JSON, key never in error text) |
| Browser test (optional) | `tests/test_shield_ripple_browser.py` checks shield CSS on a hand-built page in Chromium via Playwright; skipped without Playwright and Chromium |
| Live API tests | **Not run** (no network or keys) |
| Real Streamlit, device, deployment | **Not verified** |

**Skipped (3):** generate-then-decode QR round trips that need the `qrcode` package, which was missing in that sandbox. They should run after `pip install -r requirements.txt`.

---

## Roadmap

| Item | Status |
|---|---|
| Eight-page app, CyberGuide AI, shield navigation with ripple | Implemented (per previous README) |
| QR types: URL, text, Wi-Fi, email; PNG/JPG/SVG export | Implemented (per previous README) |
| Advanced QR customization (patterns, gradients, frames, extra formats and types) | Planned / in progress |
| Capillary-wave shield animation | Planned / in progress |
| Real-browser, device, and Community Cloud verification | Needs verification |
| AI Security Assistant page, Phishing Awareness Lab, Security Reports | Planned |
| VirusTotal uploads above 25 MB | Planned |

---

## Limitations and responsible use

- Heuristics can miss threats, and domain detection is approximate (no full Public Suffix List).
- Zero detections do not establish safety.
- VirusTotal's free tier allows 4 lookups per minute and 500 per day, for non-commercial use. The app adds a 4-per-minute guard.
- External submissions may disclose data to third parties.
- AI output may be incorrect.
- Browser rendering and deployment behavior vary by environment. The floating chat and sidebar use fixed-position CSS that may need adjustment across Streamlit versions.
- Community Cloud toolbar icons may still appear; see `docs/architecture.md`.
- Refreshing the browser returns to the landing page.

---

## Contributing and license

Issues and suggestions are welcome. Please follow any contribution notes in `docs/` and keep changes focused.

**License:** not yet specified. No license file was verified, so reuse rights are not granted by this README.

<div align="center"><sub>🛡️ CyberShield AI · educational use only</sub></div>
