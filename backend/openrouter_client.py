"""OpenRouter chat client (OpenAI-compatible Chat Completions).

Pattern adapted from the Sahay AI reference client (requests + bounded
retries for transient failures only, friendly errors, never leaks the key),
rewritten for CyberShield AI's config. The model is configurable through
OPENROUTER_MODEL.

The API key is only ever placed in the Authorization header. It is never
logged or included in exception messages.
"""

from __future__ import annotations

import re
import time

import requests

from backend.logging_config import get_logger
from config import get_openrouter_config

logger = get_logger(__name__)

REQUEST_TIMEOUT_SECONDS = 25
MAX_RETRIES = 1            # total attempts = MAX_RETRIES + 1; transient failures only
RETRY_BACKOFF_SECONDS = 1.0
DEFAULT_MAX_TOKENS = 500

_THINK_RE = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)


class OpenRouterError(RuntimeError):
    """Base error. str(exc) is user-safe."""


class OpenRouterNotConfiguredError(OpenRouterError):
    pass


class OpenRouterTimeoutError(OpenRouterError):
    pass


class OpenRouterRateLimitError(OpenRouterError):
    pass


class OpenRouterResponseError(OpenRouterError):
    pass


def _post(payload: dict) -> requests.Response:
    cfg = get_openrouter_config()
    url = f"{cfg.base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {cfg.api_key}",
        "Content-Type": "application/json",
        "X-Title": "CyberShield AI",
    }
    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
            last_exc = exc
            logger.warning("OpenRouter network problem (attempt %d)", attempt + 1)
        else:
            if response.status_code >= 500 and attempt < MAX_RETRIES:
                logger.warning("OpenRouter server error %s (attempt %d)", response.status_code, attempt + 1)
            else:
                return response
        if attempt < MAX_RETRIES:
            time.sleep(RETRY_BACKOFF_SECONDS * (2 ** attempt))
    raise OpenRouterTimeoutError(
        "The AI service could not be reached in time. Local tools still work; try the AI again shortly."
    ) from last_exc


def chat_completion(messages: list[dict], *, temperature: float = 0.3,
                    max_tokens: int = DEFAULT_MAX_TOKENS) -> str:
    cfg = get_openrouter_config()
    if not cfg.is_configured:
        raise OpenRouterNotConfiguredError(
            "OPENROUTER_API_KEY is not set, so AI answers are unavailable. "
            "Add it to Streamlit secrets or your environment."
        )

    response = _post({
        "model": cfg.model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    })

    status = response.status_code
    if status == 429:
        raise OpenRouterRateLimitError("The AI service is rate-limited right now. Wait a moment and retry.")
    if status in (401, 403):
        logger.error("OpenRouter auth failure (status %s)", status)
        raise OpenRouterError("The AI service rejected the API key. Check OPENROUTER_API_KEY.")
    if status == 404 or status == 400:
        logger.error("OpenRouter request rejected (status %s)", status)
        raise OpenRouterError("The AI service rejected the request. Check that OPENROUTER_MODEL is a valid model id.")
    if status >= 400:
        logger.error("OpenRouter error (status %s)", status)
        raise OpenRouterError(f"The AI service returned an error (HTTP {status}).")

    try:
        content = response.json()["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise OpenRouterResponseError("The AI service returned an unexpected response.") from exc

    if not isinstance(content, str) or not content.strip():
        raise OpenRouterResponseError("The AI service returned an empty answer.")
    cleaned = _THINK_RE.sub("", content).strip()
    if not cleaned:
        raise OpenRouterResponseError("The AI service returned an empty answer.")
    return cleaned
