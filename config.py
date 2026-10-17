"""Central configuration for CyberShield AI.

Secrets are read from environment variables first, then Streamlit
secrets. Nothing is hardcoded. Values are read on every call (cheap)
so a key added in Settings/secrets is picked up without code changes.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:  # python-dotenv is optional at runtime
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=False)
except ImportError:  # pragma: no cover
    pass

APP_NAME = "CyberShield AI"
APP_TAGLINE = "Intelligent Security. Clear Insights. Safer Digital Experiences."
GUIDE_NAME = "CyberGuide AI"

# UI chrome. False = Streamlit's own sidebar is not rendered and the custom
# shield-button navigation drawer (components/shield_nav.py) is used instead.
# Set True to restore the original Streamlit sidebar exactly as it was.
SHOW_DEFAULT_SIDEBAR = False

# Keep in sync with [server] maxUploadSize in .streamlit/config.toml.
MAX_UPLOAD_MB = 25
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

DEFAULT_OPENROUTER_URL = "https://openrouter.ai/api/v1"
DEFAULT_OPENROUTER_MODEL = "openai/gpt-4o-mini"
DEFAULT_VIRUSTOTAL_URL = "https://www.virustotal.com/api/v3"


def _get_setting(key: str, default: str = "") -> str:
    value = os.getenv(key, "")
    if not value:
        try:
            import streamlit as st

            if key in st.secrets:
                value = str(st.secrets[key])
        except Exception:  # no Streamlit / no secrets file: fine
            value = ""
    return (value or default).strip()


@dataclass(frozen=True)
class OpenRouterConfig:
    api_key: str
    base_url: str
    model: str

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.base_url and self.model)


@dataclass(frozen=True)
class VirusTotalConfig:
    api_key: str
    base_url: str

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)


def get_openrouter_config() -> OpenRouterConfig:
    return OpenRouterConfig(
        api_key=_get_setting("OPENROUTER_API_KEY"),
        base_url=_get_setting("OPENROUTER_BASE_URL", DEFAULT_OPENROUTER_URL),
        model=_get_setting("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL),
    )


def get_virustotal_config() -> VirusTotalConfig:
    return VirusTotalConfig(
        api_key=_get_setting("VIRUSTOTAL_API_KEY"),
        base_url=_get_setting("VIRUSTOTAL_BASE_URL", DEFAULT_VIRUSTOTAL_URL),
    )


def get_app_env() -> str:
    return _get_setting("APP_ENV", "development")


def service_status() -> dict[str, bool]:
    """Booleans only. Never returns key values."""
    return {
        "openrouter": get_openrouter_config().is_configured,
        "virustotal": get_virustotal_config().is_configured,
    }
