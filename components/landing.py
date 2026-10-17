"""Landing page (entry screen). One small function per section.

All interactive controls are real Streamlit buttons using on_click callbacks
(no manual st.rerun, no query parameters, no JavaScript). The only anchors
are in-page links (#features, #about, ...). Every dynamic string is escaped
even though the copy is static, so the habit stays safe if copy ever changes.
"""

from __future__ import annotations

from html import escape

import streamlit as st

from components import app_state
from components.compat import BUTTON_STRETCH
from components.landing_css import landing_css
from config import APP_NAME, APP_TAGLINE
from content import landing_content as copy


def _enter(page: str | None = None, open_guide: bool = False) -> None:
    app_state.enter_app(st.session_state, page=page, open_guide=open_guide)


def _get_started(key: str) -> None:
    st.button("Get Started", key=key, type="primary", on_click=_enter, **BUTTON_STRETCH)


def _heading(kicker: str, title: str, anchor: str = "") -> None:
    anchor_html = f'<div id="{escape(anchor)}"></div>' if anchor else ""
    st.markdown(
        f'{anchor_html}<div class="cs-l-kicker">{escape(kicker)}</div>'
        f'<div class="cs-l-h2" role="heading" aria-level="2">{escape(title)}</div>',
        unsafe_allow_html=True,
    )


def _topbar() -> None:
    with st.container(key="landing_topbar"):
        left, right = st.columns([4, 1.3], vertical_alignment="center")
        with left:
            st.markdown(
                f'<div class="cs-l-bar"><div class="cs-l-brand"><span class="cs-l-logo">🛡️</span>'
                f'<span>{escape(APP_NAME)}</span></div>'
                '<nav class="cs-l-nav"><a href="#features" target="_self">Features</a>'
                '<a href="#about" target="_self">About</a></nav></div>',
                unsafe_allow_html=True,
            )
        with right:
            _get_started("landing_cta_top")


def _hero() -> None:
    with st.container(key="landing_hero"):
        left, right = st.columns([3, 2], vertical_alignment="center")
        with left:
            st.markdown(
                f'<div class="cs-l-eyebrow">{escape(APP_TAGLINE)}</div>'
                '<div class="cs-l-h1" role="heading" aria-level="1">Your Smarter '
                '<span class="cs-l-grad">Cybersecurity</span> Toolkit</div>'
                f'<p class="cs-l-lead">{escape(copy.HERO_DESCRIPTION)}</p>',
                unsafe_allow_html=True,
            )
            primary, secondary = st.columns(2)
            with primary:
                _get_started("landing_cta_hero")
            with secondary:
                st.markdown('<a class="cs-l-btn2" href="#features" target="_self">Explore Features</a>',
                            unsafe_allow_html=True)
        with right:
            chips = "".join(f"<span>{escape(c)}</span>" for c in copy.HERO_CHIPS)
            st.markdown(
                '<div class="cs-l-shield"><div class="cs-l-ring r1"></div><div class="cs-l-ring r2"></div>'
                '<div class="cs-l-core">🛡️</div></div>'
                f'<div class="cs-l-chips">{chips}</div>',
                unsafe_allow_html=True,
            )


def _features() -> None:
    _heading("Features", copy.FEATURES_HEADING, anchor="features")
    for start in (0, 3):
        for col, feature in zip(st.columns(3), copy.FEATURES[start:start + 3]):
            with col, st.container(key=f"landing_card_{feature.key}"):
                st.markdown(
                    f'<div class="cs-l-icon">{escape(feature.icon)}</div>'
                    f'<div class="cs-l-ctitle">{escape(feature.title)}</div>'
                    f'<div class="cs-l-cdesc">{escape(feature.description)}</div>',
                    unsafe_allow_html=True,
                )
                st.button(feature.cta, key=f"landing_open_{feature.key}", on_click=_enter,
                          kwargs={"page": feature.page, "open_guide": feature.open_guide},
                          **BUTTON_STRETCH)


def _how_it_works() -> None:
    _heading("Process", copy.HOW_HEADING, anchor="how-it-works")
    steps = "".join(
        f'<div class="cs-l-step"><div class="cs-l-num">{i}</div>'
        f'<div class="cs-l-ctitle">{escape(title)}</div><div class="cs-l-cdesc">{escape(text)}</div></div>'
        for i, (title, text) in enumerate(copy.STEPS, start=1)
    )
    st.markdown(f'<div class="cs-l-steps">{steps}</div>', unsafe_allow_html=True)


def _about() -> None:
    _heading("About", copy.ABOUT_HEADING, anchor="about")
    notes = "".join(f'<div class="cs-l-note">{escape(n)}</div>' for n in copy.TRUST_NOTES)
    st.markdown(
        f'<div class="cs-l-about"><p>{escape(copy.ABOUT_INTRO)}</p><div class="cs-l-notes">{notes}</div></div>',
        unsafe_allow_html=True,
    )


def _final_cta() -> None:
    with st.container(key="landing_final"):
        st.markdown(
            f'<div class="cs-l-final"><div class="cs-l-h2" role="heading" aria-level="2">'
            f'{escape(copy.FINAL_HEADING)}</div><p>{escape(copy.FINAL_TEXT)}</p></div>',
            unsafe_allow_html=True,
        )
        _, middle, _ = st.columns([1, 1, 1])
        with middle:
            _get_started("landing_cta_final")


def _footer() -> None:
    links = "".join(f'<a href="{escape(href)}" target="_self">{escape(label)}</a>'
                    for label, href in copy.FOOTER_LINKS)
    st.markdown(
        f'<div class="cs-l-footer"><strong>{escape(APP_NAME)}</strong><br>{escape(APP_TAGLINE)}<br>'
        f'<span>{escape(copy.FOOTER_NOTICE)}</span><br>{links}</div>',
        unsafe_allow_html=True,
    )


def render_landing() -> None:
    st.markdown(landing_css(), unsafe_allow_html=True)
    _topbar()
    _hero()
    _features()
    _how_it_works()
    _about()
    _final_cta()
    _footer()
