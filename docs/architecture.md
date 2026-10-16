# Architecture

Three layers, as in the project spec:

- **Platform:** `streamlit_app.py` (router, safety net), `app_registry.py` (module list), `config.py`, `components/` (theme, sidebar, cards, shared VirusTotal UI).
- **Tools:** `backend/url_analyzer.py`, `backend/file_hashing.py`, `backend/virustotal_client.py`, `qr_tools/`. Pure Python, no Streamlit imports, unit-tested.
- **CyberGuide AI:** `components/cyberguide_chat.py` (floating UI), `cyberguide/engine.py` (answer logic), `cyberguide/knowledge_base.py` (retrieval over `knowledge.md`).

## Key decisions

- **Registry as single source of truth.** The sidebar, dashboard, chatbot navigation buttons and tests all read `app_registry.py`. `streamlit_app.py` asserts the router matches it, and a test checks `knowledge.md` mentions every implemented module and labels planned ones as planned.
- **Retrieval, not a vector DB.** `knowledge.md` is ~20 short sections. Title-weighted keyword overlap finds the right ones; only the top 3 go into the prompt.
- **Honest chatbot.** The model receives documentation plus booleans saying whether keys are set. It cannot run tools. Answers are labeled "AI-generated explanation" or "From app documentation"; when the AI is unavailable the reason is shown.
- **One QR matrix, one style.** Preview, decode check and downloads all derive from the same matrix and `QRStyle`. The `qrcode` package only supplies the matrix; PNG/JPG/SVG rendering is in `qr_tools/generator.py`.
- **Separation of services.** OpenRouter and VirusTotal clients share nothing; local tools import neither.
- **`views/` not `pages/`** to avoid Streamlit's automatic multipage routing.
- **Reference project.** Patterns reused from Sahay AI: keyed fixed-position container for the floating chat, config-dataclass style, bounded-retry OpenRouter client that never leaks the key. No Sahay code, features, credentials or wellness content were carried over.
