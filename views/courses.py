"""Courses: a provider-based directory of cybersecurity courses and learning paths.

Data and filtering live in content/courses.py (no Streamlit there). This module only renders:
search and filter widgets, provider sections and two-column course cards (Streamlit columns
stack into one column on narrow screens). Nothing is fetched from the network, and every
dataset string is HTML-escaped before it reaches unsafe HTML. Widget state is kept under the
`courses_*` session keys only.
"""

from __future__ import annotations

from html import escape

import streamlit as st

from components.cards import badge
from components.header import page_header
from content.courses import (ALL, COSTS, COURSES, CREDENTIALS, DIFFICULTIES, LAST_VERIFIED, PROVIDER_NAMES,
                             VERIFIED, Course, Provider, filter_courses, group_by_provider, provider_for)

K_QUERY = "courses_query"
K_PROVIDER = "courses_provider"
K_DIFFICULTY = "courses_difficulty"
K_COST = "courses_cost"
K_CREDENTIAL = "courses_credential"
FILTER_KEYS = (K_QUERY, K_PROVIDER, K_DIFFICULTY, K_COST, K_CREDENTIAL)

NOTICE = ("Providers can change, rename or withdraw courses, prices and credentials at any time. "
          f"Facts below were checked against official provider pages on {LAST_VERIFIED}. Anything not "
          "confirmed is marked Unverified or Not stated. Always confirm on the provider's site before you enroll.")

LEGEND = (
    "**Verified**: the facts shown were read on an official provider page.",
    "**Partially verified**: the course exists, but some details (or the direct course link) could not be confirmed.",
    "**Digital badge**: proof of completing a course. It is not a professional certification.",
    "**Completion certificate**: issued by a (paid) programme for finishing it.",
    "**Professional certification exam**: a separate, usually paid test (for example Cisco CCST or Microsoft SC-900). "
    "Free training does not mean a free exam.",
)


def _h(text: str) -> str:
    """Escape for HTML. '$' is also neutralised so Markdown never treats prices as math."""
    return escape(text).replace("$", "&#36;")


def _md(text: str) -> str:
    return text.replace("$", "\\$")


def _choice(value, options) -> str:
    return value if isinstance(value, str) and value in options else ALL


def _reset() -> None:
    """on_click callback: clear every Courses filter (touches only the courses_* keys)."""
    st.session_state[K_QUERY] = ""
    for key in FILTER_KEYS[1:]:
        st.session_state[key] = ALL


def _is_catalogue(course: Course) -> bool:
    return course.official_url == provider_for(course.provider).website


def _card(course: Course) -> None:
    prov = provider_for(course.provider)
    verify_tone = "ok" if course.verification == VERIFIED else "warn"
    cost_tone = {"Free": "ok", "Paid": "warn"}.get(course.cost_status, "neutral")
    source = escape(course.source_url, quote=True)
    st.markdown(
        f'<div class="cs-card"><h4>{_h(course.title)}</h4>'
        f'<div class="cs-muted">{_h(prov.icon)} Provider: {_h(course.provider)}</div>'
        f'<div>{badge(course.verification, verify_tone)} {badge("Cost: " + course.cost_status, cost_tone)}</div>'
        f'<div class="cs-muted"><strong>Level:</strong> {_h(course.difficulty)}<br>'
        f'<strong>Credential:</strong> {_h(course.certificate_status)}<br>'
        f'<strong>Duration:</strong> {_h(course.duration)}<br>'
        f'<strong>Eligibility:</strong> {_h(course.eligibility)}</div>'
        f'<div class="cs-muted">{_h(course.description)}</div>'
        f'<div class="cs-muted">Source: <a href="{source}" target="_blank" rel="noopener noreferrer">'
        f'official page</a> (checked {_h(course.last_verified)})</div></div>',
        unsafe_allow_html=True,
    )
    if course.details:
        with st.expander("Credential, exam and verification details"):
            st.markdown("\n".join(f"- {_md(d)}" for d in course.details))
    label = "Open official catalogue" if _is_catalogue(course) else "Visit Official Course"
    st.link_button(f"{label} → {course.title}", course.official_url)


def _provider_header(provider: Provider) -> None:
    st.subheader(f"{provider.icon} {provider.name}")
    st.caption(provider.note)
    st.markdown(f"Official website: [{provider.website}]({provider.website})")
    if provider.resource:
        label, url = provider.resource
        st.markdown(f"Resource link: [{_md(label)}]({url})")


def _filters() -> tuple[str, str, str, str, str]:
    query = st.text_input("Search by course name", key=K_QUERY, placeholder="For example: ethical, fundamentals")
    left, right = st.columns(2)
    with left:
        provider = st.selectbox("Provider", [ALL, *PROVIDER_NAMES], key=K_PROVIDER)
        cost = st.selectbox("Cost", [ALL, *COSTS], key=K_COST)
    with right:
        difficulty = st.selectbox("Difficulty", [ALL, *DIFFICULTIES], key=K_DIFFICULTY)
        credential = st.selectbox("Credential", [ALL, *CREDENTIALS], key=K_CREDENTIAL)
    st.button("Reset filters", key="courses_reset", on_click=_reset)
    # Unexpected values (a tampered session, or a test double) fall back to "no filter".
    return (query if isinstance(query, str) else "",
            _choice(provider, PROVIDER_NAMES), _choice(difficulty, DIFFICULTIES),
            _choice(cost, COSTS), _choice(credential, CREDENTIALS))


def render() -> None:
    page_header("Courses", "Cybersecurity courses and learning paths, with honest free, paid and credential labels.")
    st.info(NOTICE)
    with st.expander("How to read these cards"):
        st.markdown("\n".join(f"- {line}" for line in LEGEND))
    query, provider, difficulty, cost, credential = _filters()
    matches = filter_courses(COURSES, query, provider, difficulty, cost, credential)
    st.caption(f"Showing {len(matches)} of {len(COURSES)} courses.")
    if not matches:
        st.info("No courses match your search and filters. Try a different search or press Reset filters.")
        return
    for prov, courses in group_by_provider(matches):
        _provider_header(prov)
        for start in range(0, len(courses), 2):
            for col, course in zip(st.columns(2), courses[start:start + 2]):
                with col:
                    _card(course)
