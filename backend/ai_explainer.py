"""Optional AI explanation of URL heuristic findings.

Privacy: only the hostname and the finding TITLES are sent to OpenRouter,
never the full URL, path, query string, or any file. The result is an
explanation, not a scan result, and the UI labels it that way.
"""

from __future__ import annotations

from backend import openrouter_client as orc
from backend.url_analyzer import UrlAnalysis

_SYSTEM = (
    "You explain URL-analysis findings to a cybersecurity beginner in under 150 words. "
    "The findings are offline heuristics, not verified threat intelligence. Never declare the "
    "site safe or malicious. Give 2-3 practical defensive steps. Do not claim you visited the site."
)


def explain_url_findings(analysis: UrlAnalysis) -> str:
    if not analysis.valid:
        raise orc.OpenRouterError("Analyze a valid URL first.")
    titles = "; ".join(f.title for f in analysis.findings) or "no heuristic findings"
    user = (
        f"Hostname: {analysis.hostname}\nSignal level: {analysis.signal_level}\n"
        f"Findings: {titles}\nExplain what this means and what the user should do."
    )
    return orc.chat_completion(
        [{"role": "system", "content": _SYSTEM}, {"role": "user", "content": user}],
        max_tokens=350,
    )
