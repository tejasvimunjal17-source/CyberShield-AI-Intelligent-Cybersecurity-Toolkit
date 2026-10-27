"""Page-level tests for the QR Code Generator, run through tests/fake_streamlit.py.

The harness mimics Streamlit's rule that a widget's value lives in session_state[key] (so a callback that edits
session_state really changes the next run). It checks what the page asks Streamlit to show and download. It is NOT
a browser test: layout, touch targets and styling are not exercised here.
"""

import importlib
import io
import re
import sys
import unittest
from datetime import time
from unittest import mock

import numpy as np
from PIL import Image

from qr_tools import exporter as ex
from qr_tools import generator as gen
from tests.fake_streamlit import FakeStreamlit
from tests.qr_matrix import cv2_matrix
from tests.test_qr_render import png

K = "qrg_"


def type_key(category):
    return f"{K}type_{category}"
URL = "https://cybershield.example/menu?table=7"


class Upload(io.BytesIO):
    def __init__(self, data, name="logo.png"):
        super().__init__(data)
        self.name, self.size = name, len(data)


class Box:
    """st.container() stand-in: forwards every call to the shared mock so it is recorded."""
    def __init__(self, st):
        self._st = st

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def __getattr__(self, name):
        return getattr(self._st, name)


class PageBase(unittest.TestCase):
    def setUp(self):
        ex.clear_cache()
        self.fake = FakeStreamlit()
        st, ss = self.fake.st, self.fake.session
        self.values: dict = {}
        self.pressed: set = set()

        def widget(key, default):
            if key in self.values:
                ss[key] = self.values[key]
            elif key not in ss:
                ss[key] = default
            return ss[key]

        st.selectbox.side_effect = lambda label, options, index=0, key=None, **k: widget(key, list(options)[index])
        st.text_input.side_effect = lambda label, value="", key=None, **k: widget(key, value)
        st.text_area.side_effect = lambda label, value="", key=None, **k: widget(key, value)
        st.checkbox.side_effect = lambda label, value=False, key=None, **k: widget(key, value)
        st.slider.side_effect = lambda label, lo, hi, val, key=None, **k: widget(key, val)
        st.color_picker.side_effect = lambda label, val, key=None, **k: widget(key, val)
        st.date_input.side_effect = lambda label, value=None, key=None, **k: widget(key, value)
        st.time_input.side_effect = lambda label, value=None, key=None, **k: widget(key, value)
        st.file_uploader.side_effect = lambda label, type=None, key=None, **k: self.values.get(key)

        def button(label, key=None, on_click=None, **k):
            if on_click is not None:
                self.fake.callbacks[key] = on_click
            return key in self.pressed

        st.button.side_effect = button
        st.container.side_effect = lambda *a, **k: Box(st)
        self.st = st

        self.mods = mock.patch.dict(sys.modules, {"streamlit": st})
        self.mods.start()
        for name in [m for m in list(sys.modules) if m.split(".")[0] in ("views", "components")]:
            del sys.modules[name]
        self.page = importlib.import_module("views.qr_generator")
        patcher = mock.patch.object(gen, "make_matrix", side_effect=lambda d, ec="M": cv2_matrix(gen.build_text_payload(d), ec))
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        self.mods.stop()
        for name in [m for m in list(sys.modules) if m.split(".")[0] in ("views", "components")]:
            sys.modules.pop(name, None)
        ex.clear_cache()

    # helpers ---------------------------------------------------------------
    def set_url(self, url=URL):
        self.values[K + "f_url_url"] = url

    def run_page(self):
        for m in (self.st.image, self.st.download_button, self.st.error, self.st.warning, self.st.success, self.st.info,
                  self.st.code, self.st.caption):
            m.reset_mock()
        self.page.render()

    def shown_images(self):
        return [c.args[0] for c in self.st.image.call_args_list if isinstance(c.args[0], bytes)]

    def downloads(self):
        return self.st.download_button.call_args_list

    def texts(self, mock_):
        return " ".join(str(c.args[0]) for c in mock_.call_args_list if c.args)

    def download_bytes(self):
        d = self.downloads()
        self.assertEqual(len(d), 1)
        return d[0].kwargs["data"], d[0].kwargs


class ContentAndPreviewTests(PageBase):
    def test_empty_page_shows_a_hint_and_no_code_or_download(self):
        self.run_page()
        self.assertEqual(self.shown_images(), [])
        self.assertEqual(self.downloads(), [])
        self.assertFalse(self.st.error.called)                               # not an error: nothing typed yet
        self.assertIn("Enter your content", self.texts(self.st.info))

    def test_url_produces_preview_payload_check_and_png_download(self):
        self.set_url()
        self.run_page()
        self.assertEqual(len(self.shown_images()), 1)
        self.assertIn(URL, self.texts(self.st.code))
        self.assertIn("Test-read OK", self.texts(self.st.success))
        data, kw = self.download_bytes()
        self.assertEqual((kw["file_name"], kw["mime"]), ("cybershield_qr.png", "image/png"))
        self.assertEqual(Image.open(io.BytesIO(data)).format, "PNG")

    def test_preview_and_download_are_the_same_picture(self):
        self.set_url()
        self.run_page()
        shown = np.asarray(Image.open(io.BytesIO(self.shown_images()[0])).convert("RGB"))
        data, _ = self.download_bytes()
        self.assertTrue(np.array_equal(shown, np.asarray(Image.open(io.BytesIO(data)).convert("RGB"))))

    def test_changing_content_changes_the_payload_and_the_code(self):
        self.set_url()
        self.run_page()
        first, shown_first = self.download_bytes()[0], self.texts(self.st.code)
        self.set_url("https://other.example/path")
        self.run_page()
        self.assertNotEqual(self.download_bytes()[0], first)
        self.assertIn("https://other.example/path", self.texts(self.st.code))
        self.assertNotIn("other.example", shown_first)

    def test_changing_colors_updates_preview_and_download(self):
        self.set_url()
        self.run_page()
        before = (self.shown_images()[0], self.download_bytes()[0])
        self.values[K + "color_preset"] = "Cybersecurity blue"
        self.run_page()
        self.assertNotEqual(self.shown_images()[0], before[0])
        self.assertNotEqual(self.download_bytes()[0], before[1])
        px = Image.open(io.BytesIO(self.download_bytes()[0])).convert("RGB")
        self.assertIn((0x0B, 0x3C, 0x8C), {px.getpixel((x, y)) for x in range(0, px.width, 7) for y in range(0, px.height, 7)})

    def test_changing_size_changes_output_dimensions(self):
        self.set_url()
        sizes = {}
        for label, target in (("Small (512 px)", 512), ("Large (1024 px)", 1024)):
            self.values[K + "size"] = label
            self.run_page()
            w = Image.open(io.BytesIO(self.download_bytes()[0])).width
            sizes[target] = w
            self.assertLessEqual(w, target)
        self.assertLess(sizes[512], sizes[1024])

    def test_error_correction_and_quiet_zone_reach_the_output(self):
        self.set_url()
        self.run_page()
        base = Image.open(io.BytesIO(self.download_bytes()[0])).size
        self.values[K + "quiet"] = 8
        self.run_page()
        self.assertNotEqual(self.st.image.call_args.kwargs["caption"], "")
        self.assertIn("quiet zone 8 modules", self.st.image.call_args.kwargs["caption"])
        self.values[K + "ec"] = "H"
        self.run_page()
        self.assertIn("error correction H", self.st.image.call_args.kwargs["caption"])
        self.assertNotEqual(Image.open(io.BytesIO(self.download_bytes()[0])).size, base)

    def test_every_format_downloads_a_genuine_file_with_the_right_name_and_type(self):
        self.set_url()
        expect = {"PNG": ("cybershield_qr.png", "image/png", b"\x89PNG"), "JPG": ("cybershield_qr.jpg", "image/jpeg", b"\xff\xd8"),
                  "TIFF": ("cybershield_qr.tiff", "image/tiff", None), "SVG": ("cybershield_qr.svg", "image/svg+xml", b"<?xml"),
                  "PDF": ("cybershield_qr.pdf", "application/pdf", b"%PDF-")}
        for label, (name, mime, magic) in expect.items():
            self.values[K + "format"] = label
            self.run_page()
            data, kw = self.download_bytes()
            self.assertEqual((kw["file_name"], kw["mime"]), (name, mime), label)
            self.assertIn(f"Download {label}", self.downloads()[0].args[0])
            if magic:
                self.assertTrue(data.startswith(magic), label)
        self.assertIn("EPS is not offered", self.texts(self.st.caption))


class ContentTypeFlowTests(PageBase):
    def test_original_types_are_still_selectable_with_their_original_names(self):
        seen = {}
        for category in ("Basic", "Contact & communication"):
            self.values[K + "category"] = category
            self.run_page()
            seen[category] = [c.args[1] for c in self.st.selectbox.call_args_list if c.args[0] == "Content type"][-1]
        self.assertTrue({"URL", "Text", "Email"} <= set(seen["Basic"]))
        self.assertIn("Wi-Fi", seen["Contact & communication"])

    def test_switching_category_after_choosing_a_type_never_crashes(self):
        self.set_url()
        self.run_page()                                                       # Basic / URL is now remembered in session state
        for category in ("Contact & communication", "Social & business", "Files & documents", "Calendar", "Basic"):
            self.values[K + "category"] = category
            self.run_page()                                                   # must not raise (it did before the fix)
            offered = [c.args[1] for c in self.st.selectbox.call_args_list if c.args[0] == "Content type"][-1]
            self.assertTrue(offered)
        self.fake.session[type_key("Calendar")] = "URL"                       # even a corrupt remembered value is tolerated
        self.values[K + "category"] = "Calendar"
        self.run_page()
        self.assertTrue(self.st.selectbox.called)

    def test_a_calendar_event_with_only_a_title_is_valid_by_default(self):
        self.values.update({K + "category": "Calendar", type_key("Calendar"): "Calendar event", K + "f_calendar_title": "Standup"})
        self.run_page()
        self.assertFalse(self.st.error.called)
        self.assertIn("SUMMARY:Standup", self.texts(self.st.code))

    def test_original_size_labels_default_and_color_presets_are_preserved(self):
        self.set_url()
        self.run_page()
        options = {c.args[0]: list(c.args[1]) for c in self.st.selectbox.call_args_list}
        self.assertEqual(options["Output size"][:4], ["Small (512 px)", "Medium (768 px)", "Large (1024 px)", "Extra large (2048 px)"])
        self.assertIn("Print (4096 px)", options["Output size"])
        self.assertTrue({"Navy on white", "Teal on white"} <= set(options["Color preset"]))     # presets the old page offered
        self.assertEqual(options["Error correction"], ["L", "M", "Q", "H"])
        self.assertEqual(options["Download format"][:3], ["PNG", "JPG", "TIFF"])
        w = Image.open(io.BytesIO(self.download_bytes()[0])).width
        self.assertTrue(700 < w <= 768, w)                                                      # default stays Medium (768 px)
        self.assertEqual(self.st.selectbox.call_args_list[[c.args[0] for c in self.st.selectbox.call_args_list].index("Error correction")].kwargs["index"], 1)

    def test_wifi_payload_is_built_and_its_password_is_masked_on_screen(self):
        self.values.update({K + "category": "Contact & communication", type_key("Contact & communication"): "Wi-Fi", K + "f_wifi_ssid": "Cafe;1",
                            K + "f_wifi_password": "sup3rsecret"})
        self.run_page()
        shown = self.texts(self.st.code)
        self.assertIn("Cafe", shown)
        self.assertNotIn("sup3rsecret", shown)
        self.assertEqual(len(self.downloads()), 1)

    def test_calendar_event_and_file_link_types_work_through_the_page(self):
        self.values.update({K + "category": "Calendar", type_key("Calendar"): "Calendar event", K + "f_calendar_title": "Launch"})
        self.run_page()
        self.assertIn("BEGIN:VCALENDAR", self.texts(self.st.code))
        self.assertEqual(len(self.downloads()), 1)
        self.values.clear()
        self.fake.session.clear()
        self.values.update({K + "category": "Files & documents", type_key("Files & documents"): "Link to a hosted file",
                            K + "f_file_link_url": "https://example.com/menu.pdf"})
        self.run_page()
        self.assertIn("CyberShield AI does not host files", self.texts(self.st.info))
        self.assertIn("https://example.com/menu.pdf", self.texts(self.st.code))

    def test_invalid_input_gives_an_understandable_error_and_no_download(self):
        for bad, needle in (("javascript:alert(1)", "http"), ("https://user:pw@example.com", "username or password")):
            self.set_url(bad)
            self.run_page()
            self.assertIn(needle, self.texts(self.st.error))
            self.assertEqual(self.downloads(), [])
            self.assertEqual(self.shown_images(), [])

    def test_calendar_that_ends_before_it_starts_is_reported(self):
        self.values.update({K + "category": "Calendar", type_key("Calendar"): "Calendar event", K + "f_calendar_title": "x",
                            K + "f_calendar_end_time": time(8, 0)})
        self.run_page()
        self.assertIn("must end after it starts", self.texts(self.st.error))
        self.assertEqual(self.downloads(), [])

    def test_no_content_is_ever_fetched_or_opened(self):
        self.set_url()
        with mock.patch("socket.socket", side_effect=AssertionError("network used")), \
                mock.patch("socket.getaddrinfo", side_effect=AssertionError("dns used")):
            self.run_page()
        self.assertEqual(len(self.downloads()), 1)


class DesignFlowTests(PageBase):
    def test_style_presets_and_custom_shapes_change_the_picture(self):
        self.set_url()
        shots = set()
        for preset in ("Classic", "Rounded", "Circular", "Modern geometric"):
            self.values[K + "style_preset"] = preset
            self.run_page()
            shots.add(self.download_bytes()[0])
        self.assertEqual(len(shots), 4)
        self.values.update({K + "style_preset": "Custom", K + "pattern": "dots", K + "eye_outer": "square", K + "eye_inner": "circle"})
        self.run_page()
        self.assertEqual(len(self.downloads()), 1)

    def test_gradient_and_hex_color_controls(self):
        self.set_url()
        self.values.update({K + "color_preset": "Custom brand colors", K + "fill": "radial", K + "fg_hex": "#6d28d9", K + "fg2_hex": "#1d4ed8"})
        self.run_page()
        data = Image.open(io.BytesIO(self.download_bytes()[0])).convert("RGB")
        colors = {data.getpixel((x, y)) for x in range(0, data.width, 5) for y in range(0, data.height, 5)}
        self.assertGreater(len(colors), 30)                                   # a real gradient, not a flat color

    def test_invalid_hex_is_reported_next_to_the_color_and_the_picker_color_is_used(self):
        self.set_url()
        self.values.update({K + "color_preset": "Custom brand colors", K + "fg_hex": "red"})
        self.run_page()
        self.assertIn("hex value like #0B1628", self.texts(self.st.error))
        self.assertEqual(len(self.downloads()), 1)                             # falls back to the picker color

    def test_low_contrast_and_small_quiet_zone_warn_but_never_claim_safety(self):
        self.set_url()
        self.values.update({K + "color_preset": "Custom brand colors", K + "fg": "#CCCCCC", K + "quiet": 2})
        self.run_page()
        warnings = self.texts(self.st.warning)
        self.assertIn("Low contrast", warnings)
        self.assertIn("quiet zone", warnings)
        self.assertNotIn("safe", self.texts(self.st.success).lower())

    def test_transparent_png_is_really_transparent_and_jpg_explains_the_fill(self):
        self.set_url()
        self.values[K + "transparent"] = True
        self.run_page()
        self.assertEqual(Image.open(io.BytesIO(self.download_bytes()[0])).getpixel((1, 1))[3], 0)
        self.values[K + "format"] = "JPG"
        self.run_page()
        self.assertIn("cannot be transparent", self.texts(self.st.caption))

    def test_frame_and_label_reach_every_vector_format(self):
        self.set_url()
        self.values.update({K + "frame": "badge", K + "cta_choice": "Visit Website", K + "format": "SVG"})
        self.run_page()
        svg = self.download_bytes()[0].decode()
        self.assertIn("Visit Website", svg)
        self.values[K + "cta_choice"] = "Custom text"
        self.values[K + "cta_custom"] = "Menu <1> & more"
        self.run_page()
        svg = self.download_bytes()[0].decode()
        self.assertIn("Menu &lt;1&gt; &amp; more", svg)
        self.assertNotIn("<1>", svg)

    def test_too_long_label_is_reported(self):
        self.set_url()
        self.values.update({K + "frame": "badge", K + "cta_choice": "Custom text", K + "cta_custom": "x" * 31})
        self.run_page()
        self.assertTrue(self.st.error.called)
        self.assertEqual(self.downloads(), [])


class LogoFlowTests(PageBase):
    def test_valid_logo_changes_the_output_and_raises_error_correction(self):
        self.set_url()
        self.run_page()
        plain = self.download_bytes()[0]
        self.values[K + "logo"] = Upload(png())
        self.run_page()
        self.assertNotEqual(self.download_bytes()[0], plain)
        self.assertIn("error correction H", self.st.image.call_args.kwargs["caption"])
        self.assertIn("Test-read OK", self.texts(self.st.success))

    def test_user_can_decline_the_automatic_level_h_but_is_warned(self):
        self.set_url()
        self.values.update({K + "logo": Upload(png()), K + "ec_auto": False})
        self.run_page()
        self.assertIn("Q or H is recommended", self.texts(self.st.warning))
        self.assertIn("error correction M", self.st.image.call_args.kwargs["caption"])

    def test_logo_size_and_clear_space_are_applied(self):
        self.set_url()
        self.values[K + "logo"] = Upload(png())
        self.run_page()
        small = self.download_bytes()[0]
        self.values[K + "logo_pct"] = 18
        self.run_page()
        self.assertNotEqual(self.download_bytes()[0], small)

    def test_bad_uploads_are_rejected_by_content_and_never_used(self):
        self.set_url()
        self.run_page()
        plain = self.download_bytes()[0]
        for name, data in (("logo.png", b"<script>alert(1)</script>"), ("evil.png", b"MZ\x90\x00 program"),
                           ("logo.jpg", png()[:50]), ("big.png", b"\x89PNG" + b"0" * (1024 * 1024 + 1))):
            self.values[K + "logo"] = Upload(data, name)
            self.run_page()
            self.assertTrue(self.st.error.called, name)
            self.assertEqual(self.download_bytes()[0], plain, f"{name} must not change the code")

    def test_a_logo_too_big_for_the_code_is_refused_with_advice(self):
        self.values.update({K + "f_url_url": "https://a.co", K + "logo": Upload(png()), K + "logo_margin": 3, K + "ec": "H"})
        self.run_page()
        self.assertTrue(self.st.error.called)
        self.assertEqual(self.downloads(), [])


class SafetyAndFallbackTests(PageBase):
    def test_unreadable_design_warns_and_offers_a_one_click_safe_fallback(self):
        self.set_url()
        self.values.update({K + "style_preset": "Custom", K + "pattern": "dots", K + "eye_outer": "circle", K + "frame": "badge",
                            K + "cta_choice": "Scan Me"})
        with mock.patch.object(ex, "try_decode", return_value=("", "")):
            self.run_page()
        self.assertIn("could not read this design", self.texts(self.st.warning))
        self.assertIn("test-scan", self.texts(self.st.warning))
        self.assertIn(K + "safe", self.fake.callbacks)
        for key in (K + "style_preset", K + "frame"):
            self.values.pop(key)
        self.fake.callbacks[K + "safe"]()                                    # the user presses the button
        ss = self.fake.session
        self.assertEqual((ss[K + "style_preset"], ss[K + "color_preset"], ss[K + "frame"], ss[K + "transparent"]),
                         ("Classic", "Classic black and white", "none", False))
        self.run_page()
        self.assertIn("Test-read OK", self.texts(self.st.success))           # the fallback really is readable

    def test_mismatched_decode_is_an_error_not_a_pass(self):
        self.set_url()
        with mock.patch.object(ex, "try_decode", return_value=("https://evil.example", "OpenCV")):
            self.run_page()
        self.assertIn("DIFFERENT content", self.texts(self.st.error))

    def test_4096_px_raster_is_built_only_on_request_but_vector_is_immediate(self):
        self.set_url()
        self.values[K + "size"] = "Print (4096 px)"
        self.run_page()
        self.assertEqual(self.downloads(), [])
        self.pressed = {K + "prepare"}
        self.run_page()
        w, h = Image.open(io.BytesIO(self.download_bytes()[0])).size
        self.assertLessEqual(max(w, h), 4096)
        self.assertGreater(max(w, h), 4000)
        self.pressed = set()
        self.values[K + "format"] = "SVG"
        self.run_page()
        self.assertEqual(len(self.downloads()), 1)

    def test_html_embed_code_is_offered_on_request_and_escapes_alt_text(self):
        self.set_url()
        self.values.update({K + "embed": True, K + "alt": 'a" onerror="x'})
        self.run_page()
        html_calls = [c for c in self.st.code.call_args_list if c.kwargs.get("language") == "html"]
        self.assertEqual(len(html_calls), 1)
        snippet = html_calls[0].args[0]
        self.assertTrue(snippet.startswith('<img src="data:image/svg+xml;base64,'))
        self.assertIn("&quot;", snippet)
        self.assertNotIn('" onerror="', snippet)

    def test_unrelated_changes_do_not_regenerate_the_preview_or_the_check(self):
        self.set_url()
        with mock.patch.object(ex, "preview_png", wraps=ex.preview_png) as pp, mock.patch.object(ex, "verify", wraps=ex.verify) as vf:
            self.run_page()
            self.values[K + "format"] = "SVG"          # only the download format changes
            self.run_page()
            self.values[K + "format"] = "PDF"
            self.run_page()
            self.assertEqual((pp.call_count, vf.call_count), (1, 1))
            self.set_url("https://changed.example")
            self.run_page()
            self.assertEqual((pp.call_count, vf.call_count), (2, 2))

    def test_page_source_has_no_network_clients_secrets_or_raw_html_injection(self):
        for path in ("views/qr_generator.py", "qr_tools/exporter.py", "qr_tools/payloads.py", "qr_tools/design.py",
                     "qr_tools/scene.py", "qr_tools/render_svg.py", "qr_tools/render_pdf.py", "qr_tools/render_raster.py"):
            src = open(path, encoding="utf-8").read()
            for bad in ("import requests", "urllib.request", "http.client", "socket", "openrouter", "virustotal", "OPENROUTER",
                        "API_KEY", "unsafe_allow_html", "subprocess", "os.system", "eval(", "exec("):
                self.assertNotIn(bad, src, f"{path}: {bad}")


if __name__ == "__main__":
    unittest.main()
