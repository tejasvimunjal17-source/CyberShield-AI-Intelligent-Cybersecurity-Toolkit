# Setup

1. Python 3.10+ (`hashlib` flags used require 3.9+; `qrcode` and Streamlit require recent Pythons).
2. `python -m venv .venv`, activate it, `pip install -r requirements.txt`.
3. Optional keys: copy `.env.example` to `.env`, or `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`. Both targets are git-ignored.
4. `streamlit run streamlit_app.py`.
5. Check **Settings & API Configuration** to see which keys were detected ("detected" means set, not valid).

## Troubleshooting

- *VirusTotal buttons disabled:* `VIRUSTOTAL_API_KEY` not seen. Check the exact name, restart the app.
- *"rejected the API key":* wrong/revoked key or stray quotes/spaces.
- *CyberGuide shows "From app documentation":* AI not used; the note under the answer says why.
- *"qrcode package is not installed":* run `pip install -r requirements.txt`.
- *Upload rejected:* limit is 25 MB (`MAX_UPLOAD_MB` in `config.py` and `maxUploadSize` in `.streamlit/config.toml`; keep them equal).
