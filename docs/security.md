# Security notes

| Concern | How it is handled |
|---|---|
| API keys | Env vars / Streamlit secrets only; never hardcoded, never displayed (UI shows booleans); `.gitignore` excludes `.env` and `secrets.toml`; clients put keys only in request headers; tests assert keys never appear in error text |
| Suspicious URLs | Analyzed as text only; the analyzer module has no network imports (a test checks this); links displayed defanged |
| Uploaded files | Hashed as bytes in 1 MiB chunks, 25 MB limit, never executed or stored; never sent to OpenRouter; sent to VirusTotal only if the user ticks a per-file confirmation and presses Upload (original file name withheld, content never logged) |
| QR images | Pixel limit, decoded locally, content shown as plain text; nothing opened |
| Untrusted HTML | All dynamic strings in custom HTML are escaped (`components/cards.py`); QR/URL/file content shown via `st.code` |
| AI privacy | Chat input clipped to 1000 chars, secret-like text redacted, bounded history; URL explanations send only hostname + finding titles |
| Rate limits / failures | Timeouts on every request; bounded retries for transient OpenRouter failures only (never 429); VirusTotal 4/min process-wide guard; friendly errors |
| Logging | Status codes and event names only; no keys, URLs, file contents or chat text |
| Session data | Held in per-session `st.session_state`; nothing persisted server-side |

Known gaps: the secret-redaction patterns are heuristic; the shared VirusTotal quota can be exhausted by other visitors; there is no authentication or per-user rate limiting on a public deployment.
