# Deployment (GitHub + Streamlit Community Cloud)

Checklist:

- [ ] `git status` shows no `.env`, no `.streamlit/secrets.toml`.
- [ ] `requirements.txt` installs cleanly in a fresh virtualenv.
- [ ] `python -m unittest discover -s tests -t .` passes locally (including the `qrcode` round-trip tests).
- [ ] Repo pushed to GitHub.
- [ ] Streamlit Cloud app created, main file `streamlit_app.py`.
- [ ] Secrets pasted in Advanced settings → Secrets; `APP_ENV = "production"`.
- [ ] After deploy, manually test: each page loads, generate + download a QR code, hash a small file, analyze a URL, open CyberGuide AI.

Only after that checklist can the app be called deployed. If a key was ever committed, revoke it and create a new one; deleting the commit is not enough.

Note: Streamlit Community Cloud apps are public by default and all visitors share your VirusTotal quota (4/minute, 500/day) and OpenRouter spend. Consider usage limits on your OpenRouter key.
