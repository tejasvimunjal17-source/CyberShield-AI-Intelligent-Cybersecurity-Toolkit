"""Internships: a directory of internship programmes and discovery websites, with honest status labels.

Data and filtering live in content/internships.py (no Streamlit there). This module only renders. Nothing is
fetched from the network. Every dataset string is HTML-escaped before it reaches unsafe HTML, and '$' is
neutralised so Markdown never reads it as math. An application button appears only for an entry whose
application_status is "Applications Open" AND that has an official application_url (currently none do);
every other button is an "official website / platform / announcement" button. Widget state lives under the
`internships_*` session keys. Streamlit columns stack on narrow screens.
"""

from __future__ import annotations

from html import escape

import streamlit as st

import app_registry as reg
from components.cards import badge
from components.compat import BUTTON_STRETCH
from components.header import page_header
from components.sidebar import go_to
from content.internships import (ALL, APP_STATUSES, CATEGORIES, DISTINCTIONS, ENTRIES, FORMATS, INTRO, LAST_VERIFIED,
                                 OPEN, PAID_PROGRAMME, PAY, REGIONS, SAFETY_CHECKS, SAFETY_WARNING, TIPS,
                                 VERIFICATIONS, VERIFIED, CLOSED, Entry, entries_by_section, filter_entries)

K_QUERY = "internships_query"
K_CATEGORY = "internships_category"
K_REGION = "internships_region"
K_FORMAT = "internships_format"
K_PAY = "internships_pay"
K_STATUS = "internships_status"
K_VERIFY = "internships_verification"
FILTER_KEYS = (K_QUERY, K_CATEGORY, K_REGION, K_FORMAT, K_PAY, K_STATUS, K_VERIFY)

NOTICE = (f"Details were checked against official or reliable sources on {LAST_VERIFIED}, and anything not confirmed is "
          "marked Not stated or Unverified. Offers, dates and fees change, so confirm everything on the official site. "
          "No application link is shown unless an official source confirms an active application window.")


def _h(text: str) -> str:
    """Escape for HTML; '$' is neutralised so Markdown never treats it as math."""
    return escape(text).replace("$", "&#36;")


def _md(text: str) -> str:
    return text.replace("$", "\\$")


def _choice(value, options) -> str:
    return value if isinstance(value, str) and value in options else ALL


def _reset() -> None:
    """on_click callback: clear every Internships filter (touches only the internships_* keys)."""
    st.session_state[K_QUERY] = ""
    for key in FILTER_KEYS[1:]:
        st.session_state[key] = ALL


def _tone_verification(v: str) -> str:
    return "ok" if v == VERIFIED else "warn"


def _tone_status(s: str) -> str:
    return {OPEN: "ok", CLOSED: "warn"}.get(s, "neutral")


def _card(e: Entry) -> None:
    badges = [badge(e.verification, _tone_verification(e.verification)), badge(e.application_status, _tone_status(e.application_status))]
    if e.paid_programme:
        badges.append(badge(PAID_PROGRAMME, "warn"))
    note = f'<div class="cs-muted"><strong>{_h(e.status_note)}</strong></div>' if e.status_note else ""
    st.markdown(
        f'<div class="cs-card"><h4>{_h(e.name)}</h4>'
        f'<div class="cs-muted">Organiser: {_h(e.organizer)}<br>Type: {_h(e.category)}</div>'
        f'<div>{" ".join(badges)}</div>'
        f'<div class="cs-muted">{_h(e.description)}</div>'
        f'<div class="cs-muted"><strong>Eligibility:</strong> {_h(e.eligibility)}<br>'
        f'<strong>Location:</strong> {_h(e.location)}<br>'
        f'<strong>Format:</strong> {_h(e.work_format)}<br>'
        f'<strong>Pay or fee:</strong> {_h(e.pay_status)}. {_h(e.cost_note)}<br>'
        f'<strong>Duration:</strong> {_h(e.duration)}<br>'
        f'<strong>Certificate:</strong> {_h(e.certificate)}</div>'
        f'{note}'
        f'<div class="cs-muted">Last verified {_h(e.last_verified)}. Source: '
        f'<a href="{escape(e.source_url, quote=True)}" target="_blank" rel="noopener noreferrer">official or reliable source</a></div></div>',
        unsafe_allow_html=True,
    )
    if e.notes or e.search_terms:
        with st.expander("Details and what was not verified"):
            if e.notes:
                st.markdown("\n".join(f"- {_md(n)}" for n in e.notes))
            if e.search_terms:
                st.markdown("**Suggested search terms:** " + ", ".join(f"`{t}`" for t in e.search_terms))
    st.link_button(f"{e.button_label} → {e.name}", e.official_url)
    if e.application_url and e.application_status == OPEN:      # never true unless an official active URL is confirmed
        st.link_button(f"Apply Now → {e.name}", e.application_url)


def _filters() -> tuple[str, ...]:
    query = st.text_input("Search by name", key=K_QUERY, placeholder="For example: police, LinkedIn, CISA")
    a, b, c = st.columns(3)
    with a:
        category = st.selectbox("Category", [ALL, *CATEGORIES], key=K_CATEGORY)
        pay = st.selectbox("Paid, unpaid or fee-based", [ALL, *PAY], key=K_PAY)
    with b:
        region = st.selectbox("Location", [ALL, *REGIONS], key=K_REGION)
        status = st.selectbox("Application status", [ALL, *APP_STATUSES], key=K_STATUS)
    with c:
        work_format = st.selectbox("Remote, in-person or hybrid", [ALL, *FORMATS], key=K_FORMAT)
        verification = st.selectbox("Verification status", [ALL, *VERIFICATIONS], key=K_VERIFY)
    st.button("Reset filters", key="internships_reset", on_click=_reset)
    # Unexpected values (a tampered session, or a test double) fall back to "no filter".
    return (query if isinstance(query, str) else "", _choice(category, CATEGORIES), _choice(region, REGIONS),
            _choice(work_format, FORMATS), _choice(pay, PAY), _choice(status, APP_STATUSES),
            _choice(verification, VERIFICATIONS))


def _quick_links() -> None:
    for col, key in zip(st.columns(2), ("roadmap", "courses")):
        with col:
            st.button(f"Open {reg.get_module(key).title}", key=f"internships_top_{key}",
                      on_click=go_to, args=(key,), **BUTTON_STRETCH)


def _tips() -> None:
    st.subheader("Application Preparation Tips")
    st.caption("Practical, beginner-friendly steps. They improve your chances but cannot guarantee any outcome.")
    for title, points in TIPS:
        with st.expander(title):
            st.markdown("\n".join(f"- {_md(p)}" for p in points))


def _safety() -> None:
    st.subheader("Important Safety and Verification Advice")
    st.warning(SAFETY_WARNING)
    st.markdown("\n".join(f"- {_md(c)}" for c in SAFETY_CHECKS))


def render() -> None:
    page_header("Internships", "Where to look for cybersecurity internships, with honest labels about what was verified.")
    st.write(INTRO)
    st.info(NOTICE)
    with st.expander("How to read this page"):
        st.markdown("\n".join(f"- {_md(d)}" for d in DISTINCTIONS))
    _quick_links()
    query, category, region, work_format, pay, status, verification = _filters()
    matches = filter_entries(ENTRIES, query, category, region, work_format, pay, status, verification)
    st.caption(f"Showing {len(matches)} of {len(ENTRIES)} listings.")
    if not matches:
        st.info("No listings match your search and filters. Try a different search or press Reset filters.")
    for _key, title, note, entries in entries_by_section(matches):
        st.subheader(title)
        st.caption(note)
        for start in range(0, len(entries), 2):
            for col, entry in zip(st.columns(2), entries[start:start + 2]):
                with col:
                    _card(entry)
    _tips()
    _safety()
