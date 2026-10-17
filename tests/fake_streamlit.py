"""STAND-IN for the `streamlit` module, used only by flow tests.

It records what the app asks Streamlit to render (markdown, widget keys,
containers, popovers) and lets a test "press" a button by running its
on_click callback. It does NOT render anything and is not a substitute for
launching the real app in a browser.
"""

from __future__ import annotations

import os
import runpy
import sys
from unittest import mock


class Session(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError as exc:
            raise AttributeError(key) from exc

    def __setattr__(self, key, value):
        self[key] = value


class FakeStreamlit:
    def __init__(self):
        self.session = Session()
        self.callbacks: dict = {}
        self.button_keys: list = []
        self.button_labels: dict = {}
        self.markdown_calls: list = []
        self.st = self._build()

    def _build(self):
        st = mock.MagicMock(name="fake_streamlit")
        st.session_state = self.session
        st.secrets = {}

        def button(label, key=None, on_click=None, args=None, kwargs=None, **kw):
            self.button_keys.append(key)
            self.button_labels[key] = label
            if on_click is not None:
                self.callbacks[key] = (on_click, args or (), kwargs or {})
            return False

        def markdown(body, *a, **k):
            self.markdown_calls.append(str(body))

        st.button.side_effect = button
        st.markdown.side_effect = markdown
        st.form_submit_button.return_value = False
        st.text_input.return_value = ""
        st.text_area.return_value = ""
        st.file_uploader.return_value = None
        st.checkbox.return_value = False
        st.columns.side_effect = lambda spec, **k: [
            mock.MagicMock() for _ in range(spec if isinstance(spec, int) else len(spec))
        ]
        st.selectbox.side_effect = lambda label, options, index=0, **k: list(options)[index]
        st.slider.side_effect = lambda label, lo, hi, val, **k: val
        st.color_picker.side_effect = lambda label, val, **k: val
        return st

    # -- per-run helpers -----------------------------------------------------
    def run_app(self) -> None:
        """Execute streamlit_app.py once, like one Streamlit script run."""
        self.callbacks.clear()
        self.button_keys.clear()
        self.button_labels.clear()
        self.markdown_calls.clear()
        self.st.reset_mock(return_value=False, side_effect=False)
        for name in [m for m in list(sys.modules)
                     if m.split(".")[0] in ("views", "components", "streamlit_app", "content", "config")]:
            del sys.modules[name]
        with mock.patch.dict(sys.modules, {"streamlit": self.st}):
            runpy.run_module("streamlit_app", run_name="__main__")

    def press(self, key: str) -> None:
        """Simulate clicking a button: run its on_click callback (the next
        run_app() call plays the role of Streamlit's automatic rerun)."""
        fn, args, kwargs = self.callbacks[key]
        with mock.patch.dict(sys.modules, {"streamlit": self.st}):
            fn(*args, **kwargs)

    # -- inspection ---------------------------------------------------------
    def container_keys(self) -> list:
        return [c.kwargs.get("key") for c in self.st.container.call_args_list]

    def sidebar_calls(self) -> list:
        """Anything invoked on st.sidebar (the set_page_config kwarg
        'initial_sidebar_state' is deliberately not counted)."""
        return [c for c in self.st.mock_calls if str(c).startswith("call.sidebar")]

    def all_markdown(self) -> str:
        return "\n".join(self.markdown_calls)
