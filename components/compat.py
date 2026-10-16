"""Streamlit version compatibility.

Newer Streamlit releases deprecate `use_container_width=True` in favor of
`width="stretch"`. Rather than guess which one the installed version
accepts, inspect its signature once and expose the right keyword.
"""

from __future__ import annotations

import inspect

import streamlit as st


def _stretch_kwargs(func) -> dict:
    try:
        params = inspect.signature(func).parameters
    except (TypeError, ValueError):
        params = {}
    return {"width": "stretch"} if "width" in params else {"use_container_width": True}


BUTTON_STRETCH = _stretch_kwargs(st.button)
DATAFRAME_STRETCH = _stretch_kwargs(st.dataframe)
