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

## UI chrome (toolbar and navigation)

- **Navigation.** `SHOW_DEFAULT_SIDEBAR` in `config.py` (default `False`) controls whether the original sidebar is rendered. When off, nothing is written to `st.sidebar`, so Streamlit shows no sidebar, and navigation is provided by the custom shield drawer (see "Shield navigation drawer" below). Set the flag to `True` to restore the original Streamlit sidebar. `render_sidebar`, `go_to` and `current_page` are kept; the temporary `render_top_menu()` popover from Part 1 was removed.
- **Toolbar and header.** Streamlit documents `toolbarMode = "minimal"` as "show only options set externally (e.g. Streamlit Community Cloud)", so it KEEPS the Share/star/edit/GitHub items that Community Cloud injects; no toolbar mode removes them. `.streamlit/config.toml` therefore also sets `[ui] hideTopBar = true`, and `components/chrome.py` adds a CSS fallback: it hides the toolbar (`stToolbar`, `stToolbarActions`, `stAppDeployButton`, `stMainMenu`) and, because the shield navigation is a fixed element in the page body and does not use Streamlit's header, the header and decoration line too (`stHeader`, `stDecoration`). With the legacy sidebar enabled (`SHOW_DEFAULT_SIDEBAR = True`) only the toolbar is hidden, since that sidebar's collapse control lives in the header. The "Running..." status indicator is inside the toolbar and is hidden with it; the app's own spinners remain. All selectors are Streamlit internals and may stop matching in a future version; the controls would then reappear and nothing else breaks. Neither the config key nor the CSS has been verified in a browser. A private GitHub repository is the other practical option. Community Cloud's "Manage app" control lives outside the app and no selector targets it.

## Landing page and app shell

- **Two views.** `components/app_state.py` (no Streamlit import) holds `st.session_state["view"]`: `"landing"` (default for a new session) or `"app"`. `enter_app()` switches to `"app"`, sets the existing `"page"` key (default: Overview Dashboard) and optionally `"guide_open"`. It writes nothing else, so chat history and tool results are never reset.
- **Entry point.** `streamlit_app.py` calls `inject_css()`, then renders the landing page and returns early when the view is `"landing"`. Only the app branch renders the shield navigation (or the legacy sidebar), the selected page and CyberGuide AI.
- **Get Started** is a real `st.button` with an `on_click` callback (no manual `st.rerun()`, no query parameters, no JavaScript), so Streamlit's single automatic rerun shows the app. Feature-card buttons use the same callback with a registry page key. The landing top bar holds only the brand and the in-page Features/About links; the Get Started buttons are in the hero and the final call to action.
- **Modules.** Copy: `content/landing_content.py`. Rendering: `components/landing.py` (one function per section). CSS: `components/landing_css.py`, injected only on the landing view and scoped to `.cs-l-*` classes and `landing_*` keyed elements.
- **Refresh behavior.** Session state is per browser session, so a refresh shows the landing page again. Persisting the entry via a query parameter was deliberately not added to keep routing simple.
- **Tests.** `tests/test_landing.py` (state, copy accuracy, CSS safety, wiring) and `tests/test_landing_flow.py`, which runs the app against `tests/fake_streamlit.py`, a stand-in that records calls. It verifies control flow, not appearance.

## Shield navigation drawer

- **State.** `components/nav_state.py` (no Streamlit import) owns `st.session_state["cybershield_sidebar_open"]` (default `False`), `toggle_sidebar()`, `close_sidebar()` and `navigate(page)`. A toggle writes only that key, so the current page, chat history and tool results are never touched. `navigate()` sets the existing `"page"` key (ignoring unknown or planned keys) and closes the drawer. `nav_groups()` orders the implemented pages as Platform, Analysis, QR Tools, Learn, System, which gives the required eight-item order without changing the registry.
- **Rendering.** `components/shield_nav.py` draws a fixed top-left 🛡️ button and, only while open, a fixed left drawer built from a keyed `st.container`. Both use `on_click` callbacks, so there is no `st.rerun()` and no JavaScript. The active page's button gets a different widget key (`cs_navitem_active_*`) for CSS, the native "primary" type, and a "Current page" tooltip.
- **Styling.** `components/shield_nav_css.py` (no Streamlit import) targets only its own `st-key-*` classes and adds top padding so page content never sits under the shield. It does not touch Streamlit's header, toolbar or sidebar elements.
- **Shield ripple.** The shield button is circular and two thin cyan rings (the `::before`/`::after` of the fixed toggle container, half a cycle apart, 3.6 s) expand from behind it from 44 px to about 64 px while fading. Only `transform` and `opacity` are animated, with a linear fade-in and ease-out expansion set per keyframe. Rings are `pointer-events: none` and `z-index: -1` inside the toggle's stacking context, so the shield stays clickable and stable, and they stay inside the 64 px of top padding reserved for it. `prefers-reduced-motion: reduce` turns the animation off. The CSS is injected only by `render_shield_nav()`, so the landing page never gets it.
- **It is an overlay, not a push layout.** The drawer sits above the page (z-index above the chat panel, below the shield button). It starts closed because the viewport width cannot be known in Python and an open overlay would cover a phone screen. There is no backdrop.
- **Where it renders.** Only in the app view, after the landing branch returns, so the landing page never shows it.
- **Tests.** `tests/test_nav_state.py` (state, ordering, CSS safety) and `tests/test_shield_nav_flow.py` (flow against the `tests/fake_streamlit.py` stand-in). These verify control flow, not appearance. `tests/test_shield_ripple_browser.py` (optional, Chromium via Playwright, auto-skipped when unavailable) renders the real CSS in a stand-in page that imitates Streamlit's DOM; it is not the real app.
