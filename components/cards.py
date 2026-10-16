"""Reusable presentational pieces. Every dynamic string is HTML-escaped:
URLs, QR contents and file names are untrusted and must never be rendered
as HTML."""

from __future__ import annotations

from html import escape

import streamlit as st

TONES = {"ok", "warn", "bad", "info", "neutral"}


def badge(text: str, tone: str = "neutral") -> str:
    tone = tone if tone in TONES else "neutral"
    return f'<span class="cs-badge cs-{tone}">{escape(text)}</span>'


def metric_card(label: str, value: str, caption: str = "") -> None:
    st.markdown(
        f'<div class="cs-card"><div class="cs-muted">{escape(label)}</div>'
        f'<div class="cs-metric">{escape(value)}</div>'
        f'<div class="cs-muted">{escape(caption)}</div></div>',
        unsafe_allow_html=True,
    )


def info_card(title: str, body: str, badge_html: str = "") -> None:
    st.markdown(
        f'<div class="cs-card"><h4>{escape(title)} {badge_html}</h4>'
        f'<div class="cs-muted">{escape(body)}</div></div>',
        unsafe_allow_html=True,
    )


def finding_card(severity: str, title: str, detail: str) -> None:
    sev = severity if severity in {"high", "medium", "low", "info"} else "info"
    st.markdown(
        f'<div class="cs-finding {sev}"><strong>{escape(title)}</strong> '
        f'{badge(sev, {"high": "bad", "medium": "warn", "low": "info"}.get(sev, "neutral"))}'
        f'<div class="cs-muted">{escape(detail)}</div></div>',
        unsafe_allow_html=True,
    )


def empty_state(message: str) -> None:
    st.info(message)
