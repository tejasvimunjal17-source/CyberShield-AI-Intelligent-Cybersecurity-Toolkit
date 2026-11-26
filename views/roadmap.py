"""Roadmap: a beginner cybersecurity learning path in eight stages.

Content lives in content/roadmap.py. Course links, cost and verification labels are read from
content/courses.py at render time (never copied), and in-app links are buttons whose on_click
callback is the existing go_to() helper, which only accepts registered pages (Streamlit runs
the callback before the rerun, so no st.rerun() is needed). Nothing is fetched from the network and no state
is written except the page change itself. All dataset text is HTML-escaped; '$' is neutralised
so Markdown never reads it as math. Streamlit columns stack on narrow screens.
"""

from __future__ import annotations

from html import escape

import streamlit as st

import app_registry as reg
from components.cards import badge
from components.compat import BUTTON_STRETCH
from components.header import page_header
from components.sidebar import go_to
from content.courses import VERIFIED, course_by_id
from content.roadmap import (DISCLAIMER, INTRO, NO_COURSE_NOTE, STAGES, Stage, stage_by_key)


def _h(text: str) -> str:
    return escape(text).replace("$", "&#36;")


def _md(text: str) -> str:
    return text.replace("$", "\\$")


def _bullets(items) -> str:
    return "\n".join(f"- {_md(i)}" for i in items)


def _strip() -> None:
    """Visual progression: numbered stage badges joined by arrows (they wrap on small screens)."""
    parts = [badge(f"{s.number}. {s.short}", "ok" if s.number == 1 else "neutral") for s in STAGES]  # badge() escapes
    st.markdown('<div class="cs-muted">' + " → ".join(parts) + "</div>", unsafe_allow_html=True)


def _card(stage: Stage) -> None:
    st.markdown(
        f'<div class="cs-card"><h4>{_h(stage.icon)} Stage {stage.number}: {_h(stage.title)}</h4>'
        f'<div>{badge(stage.duration, "neutral")}</div>'
        f'<div class="cs-muted">{_h(stage.summary)}</div></div>',
        unsafe_allow_html=True,
    )


def _course_lines(stage: Stage) -> list[str]:
    lines = []
    for cid in stage.course_ids:
        c = course_by_id(cid)
        if c is None:
            continue
        note = "" if c.verification == VERIFIED else " (details not fully verified; see the Courses page)"
        lines.append(f"- [{_md(c.title)}]({c.official_url}) ({_md(c.provider)}). "
                     f"Cost: {_md(c.cost_status)}. {_md(c.verification)}.{note}")
    return lines


def _resources(stage: Stage) -> None:
    st.markdown("**Suggested learning resources**")
    if stage.lessons:
        st.markdown("In the Security Learning Center: " + ", ".join(f"*{_md(t)}*" for t in stage.lessons) + ".")
    lines = _course_lines(stage)
    if lines:
        st.markdown("Recommended courses (optional, not required):\n" + "\n".join(lines))
        st.caption("Courses are suggestions. Finishing one does not guarantee a job or a certification.")
    else:
        st.caption(NO_COURSE_NOTE)
    if not stage.lessons and not lines:
        st.markdown("Search for the topics listed above in material you trust.")


def _links(stage: Stage) -> None:
    keys = [k for k in stage.pages if k in reg.implemented_keys()]
    if not keys:
        return
    for col, key in zip(st.columns(len(keys)), keys):
        with col:
            st.button(f"Open {reg.get_module(key).title}", key=f"roadmap_go_{stage.key}_{key}",
                      on_click=go_to, args=(key,), **BUTTON_STRETCH)


def _details(stage: Stage) -> None:
    left, right = st.columns(2)
    with left:
        st.markdown("**Learning objectives**")
        st.markdown(_bullets(stage.objectives))
        st.markdown("**Important concepts**")
        st.markdown("\n".join(f"- **{_md(t)}**: {_md(m)}" for t, m in stage.concepts))
    with right:
        st.markdown("**Skills to develop**")
        st.markdown(_bullets(stage.skills))
        st.markdown("**Recommended topics**")
        st.markdown(_bullets(stage.topics))
    st.markdown("**Practical activities**")
    st.markdown(_bullets(stage.activities))
    _resources(stage)
    st.markdown(f"**Expected learning outcome:** {_md(stage.outcome)}")
    nxt = stage_by_key(stage.next_key) if stage.next_key else None
    if nxt:
        st.markdown(f"**Recommended next stage:** Stage {nxt.number}, {_md(nxt.title)}.")
    else:
        st.markdown("**Recommended next stage:** none. Keep practising, and go deeper in the area you chose.")
    _links(stage)


def _quick_links() -> None:
    for col, key in zip(st.columns(2), ("learning_center", "courses")):
        with col:
            st.button(f"Open {reg.get_module(key).title}", key=f"roadmap_top_{key}",
                      on_click=go_to, args=(key,), **BUTTON_STRETCH)


def render() -> None:
    page_header("Roadmap", "A step-by-step path for learning cybersecurity from the beginning.")
    st.write(INTRO)
    st.info(DISCLAIMER)
    _strip()
    _quick_links()
    for stage in STAGES:
        _card(stage)
        with st.expander(f"Stage {stage.number} details: {stage.title}"):
            _details(stage)
