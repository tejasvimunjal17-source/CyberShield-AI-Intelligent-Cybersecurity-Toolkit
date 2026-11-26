"""Courses (Phase 2): dataset rules, search/filters, page rendering, navigation, CyberGuide docs.

Run against tests/fake_streamlit.py, a recording stand-in. These checks show what the app asks Streamlit
to render and how the Python control flow behaves. They do NOT show how the page looks in a real browser,
and they do not open any provider link or confirm that any offer is still current.
"""

import importlib
import re
import sys
import unittest
from unittest import mock

import numpy  # noqa: F401  (import before the harness patches sys.modules, so this module also runs alone)

import app_registry as reg
from components import nav_state
from content import courses as data
from content.courses import (ALL, COSTS, COURSES, CREDENTIALS, DIFFICULTIES, OFFICIAL_URL_HOSTS, PROVIDERS,
                             SOURCE_URL_HOSTS, Course, filter_courses, group_by_provider)
from cyberguide.knowledge_base import load_sections, retrieve
from tests.fake_streamlit import FakeStreamlit

# Every URL the dataset may contain. Each was found on an official provider page during the 2026-11-26
# research (see PHASE2_PROGRESS.md). A new link must be opened and added here by a person: this set is the
# guard against invented links.
VERIFIED_URLS = frozenset({
    # provider websites (supplied as official)
    "https://www.netacad.com/", "https://skillsbuild.org/", "https://grow.google/", "https://learn.microsoft.com/",
    "https://training.fortinet.com/", "https://www.paloaltonetworks.com/", "https://cloud.google.com/learn",
    # Cisco
    "https://www.netacad.com/courses/ethical-hacker?courseLang=en-US",
    "https://skillsforall.com/career-path/cybersecurity",
    "https://www.cisco.com/site/us/en/learn/training-certifications/certifications/support-technician/faq.html",
    "https://www.cisco.com/site/us/en/learn/training-certifications/certifications/ethical-hacker/program.html",
    # IBM
    "https://skillsbuild.org/college-students/course-catalog/cybersecurity-fundamentals",
    "https://skillsbuild.org/college-students/course-catalog/cybersecurity-fluency-pathway",
    # Google
    "https://grow.google/certificates/en_us/certificates/cybersecurity",
    # Microsoft
    "https://learn.microsoft.com/en-us/training/paths/describe-concepts-of-security-compliance-identity/",
    "https://learn.microsoft.com/en-us/training/paths/describe-capabilities-of-microsoft-security-solutions",
    "https://learn.microsoft.com/en-us/training/paths/describe-capabilities-of-microsoft-identity-access",
    # Fortinet
    "https://training.fortinet.com/course/index.php/Certification:FCF_Cybersecurity",
    "https://www.fortinet.com/training/cybersecurity-professionals.html",
    # Palo Alto Networks
    "https://paloaltonetworks.com/cyberpedia/free-cybersecurity-education-courses",
})

PLACEHOLDER_WORDS = ("example.com", "todo", "tbd", "xxx", "lorem", "placeholder", "localhost", "127.0.0.1",
                     "prelogin", "test.netacad", "authoring")


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _text(c: Course) -> str:
    return " ".join([c.title, c.description, c.duration, c.eligibility, *c.details]).lower()


def _by_id(cid):
    return next(c for c in COURSES if c.id == cid)


class DatasetTests(unittest.TestCase):
    def test_provider_categories_in_catalogue_order(self):
        self.assertEqual([p.name for p in PROVIDERS],
                         ["Cisco Networking Academy", "IBM SkillsBuild", "Google", "Microsoft Learn",
                          "Fortinet Training Institute", "Palo Alto Networks"])
        for c in COURSES:
            self.assertIn(c.provider, [p.name for p in PROVIDERS])

    def test_dataset_structure_and_unique_ids(self):
        ids = [c.id for c in COURSES]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(COURSES), 13)
        for c in COURSES:
            for field in ("id", "title", "provider", "description", "difficulty", "cost_status",
                          "certificate_status", "duration", "eligibility", "official_url", "category",
                          "last_verified", "source_url", "verification"):
                self.assertTrue(getattr(c, field).strip(), f"{c.id}.{field}")
            self.assertIn(c.difficulty, DIFFICULTIES, c.id)
            self.assertIn(c.cost_status, COSTS, c.id)
            self.assertIn(c.certificate_status, CREDENTIALS, c.id)
            self.assertIn(c.verification, data.VERIFICATION_LEVELS, c.id)
            self.assertRegex(c.last_verified, r"^\d{4}-\d{2}-\d{2}$")
            self.assertTrue(re.fullmatch(r"[a-z0-9-]+", c.id), c.id)

    def test_urls_are_https_official_and_verified(self):
        urls = []
        for c in COURSES:
            for url, hosts in ((c.official_url, OFFICIAL_URL_HOSTS), (c.source_url, SOURCE_URL_HOSTS)):
                self.assertTrue(url.startswith("https://"), url)
                self.assertIn(url.split("/")[2], hosts, f"{c.id}: {url}")
                urls.append(url)
        for p in PROVIDERS:
            urls.append(p.website)
            if p.resource:
                urls.append(p.resource[1])
        for url in urls:
            self.assertIn(url, VERIFIED_URLS, f"unverified link: {url}")
            self.assertNotIn(" ", url)

    def test_no_placeholder_or_staging_urls_or_text(self):
        blob = " ".join(_text(c) + " " + c.official_url + " " + c.source_url for c in COURSES).lower()
        for word in PLACEHOLDER_WORDS:
            self.assertNotIn(word, blob, word)

    def test_catalogue_links_are_always_partially_verified(self):
        for c in COURSES:
            if c.official_url == data.provider_for(c.provider).website:
                self.assertEqual(c.verification, data.PARTIAL, c.id)
        self.assertEqual({c.id for c in COURSES if c.verification == data.PARTIAL},
                         {"cisco-intro-cybersecurity", "cisco-networking-essentials",
                          "cisco-cybersecurity-essentials", "fortinet-fcf-cybersecurity", "paloalto-free-fundamentals"})

    def test_catalogue_decisions(self):
        titles = [c.title for c in COURSES]
        for wanted in ("Introduction to Cybersecurity", "Networking Essentials", "Ethical Hacker",
                       "Junior Cybersecurity Analyst Career Path", "Cybersecurity Essentials"):
            self.assertIn(wanted, titles)
        blob = " ".join(_text(c) for c in COURSES) + " ".join(p.name.lower() + p.note.lower() for p in PROVIDERS)
        self.assertNotIn("network support and security", blob)     # excluded: official details unverified
        self.assertNotIn("isc2", blob)                              # excluded for now
        self.assertNotIn("certified in cybersecurity", blob)
        google = [c for c in COURSES if c.provider == "Google"]
        self.assertEqual([c.id for c in google], ["google-cybersecurity-certificate"])
        resource = data.provider_for("Google").resource
        self.assertEqual(resource[1], "https://cloud.google.com/learn")
        self.assertIn("not a verified course", resource[0])

    def test_google_certificate_is_paid_and_never_called_free(self):
        g = _by_id("google-cybersecurity-certificate")
        self.assertEqual(g.cost_status, "Paid")
        self.assertEqual(g.certificate_status, "Completion certificate (paid programme)")
        self.assertIn("not a free course", " ".join(g.details).lower())
        self.assertIn("coursera", g.description.lower())

    def test_no_free_certificate_claims_anywhere(self):
        blob = " ".join(_text(c) for c in COURSES) + " ".join(p.note.lower() for p in PROVIDERS)
        self.assertNotIn("free certificate", blob)
        self.assertNotIn("free exam", blob.replace("does not include a free exam", ""))
        for c in COURSES:
            if c.cost_status == "Free":
                self.assertNotEqual(c.certificate_status, "Completion certificate (paid programme)", c.id)

    def test_cisco_credential_and_exam_distinctions(self):
        eh = _by_id("cisco-ethical-hacker")
        self.assertEqual((eh.cost_status, eh.certificate_status), ("Free", "Digital badge"))
        t = _text(eh)
        for needle in ("capture the flag", "cisco u", "certificate also requires"):
            self.assertIn(needle, t)
        self.assertEqual(eh.official_url, "https://www.netacad.com/courses/ethical-hacker?courseLang=en-US")
        jca = _by_id("cisco-junior-cybersecurity-analyst")
        self.assertEqual((jca.cost_status, jca.certificate_status, jca.verification),
                         ("Free", "Digital badge", data.VERIFIED))
        t = _text(jca)
        for needle in ("ccst cybersecurity exam", "us$125", "separate professional certification", "about 120 hours"):
            self.assertIn(needle, t)

    def test_cybersecurity_essentials_is_distinct_from_the_career_path(self):
        ce = _by_id("cisco-cybersecurity-essentials")
        jca = _by_id("cisco-junior-cybersecurity-analyst")
        self.assertNotEqual(ce.official_url, jca.official_url)
        self.assertNotEqual(ce.title, jca.title)
        self.assertIn("instructor-led", _text(ce))
        self.assertIn("different from the free self-paced junior cybersecurity analyst career path", _text(ce))
        self.assertIn("junior cybersecurity analyst career path", _text(ce))
        self.assertEqual((ce.cost_status, ce.certificate_status), ("Unverified", "Unverified"))
        self.assertIn("cybersecurity essentials", _text(jca))      # explains the replacement
        self.assertIn("not the same as cybersecurity essentials", _text(jca))

    def test_microsoft_paths_do_not_claim_cost_or_credential_and_flag_the_paid_exam(self):
        paths = [c for c in COURSES if c.provider == "Microsoft Learn"]
        self.assertEqual(len(paths), 3)
        for c in paths:
            self.assertEqual((c.cost_status, c.certificate_status, c.duration), ("Unverified", "None verified", "Unverified"))
            self.assertIn("sc-900 certification exam is separate and paid", _text(c))
            self.assertTrue(c.official_url.startswith("https://learn.microsoft.com/en-us/training/paths/"))

    def test_ibm_facts(self):
        f = _by_id("ibm-cybersecurity-fundamentals")
        p = _by_id("ibm-cybersecurity-fluency-pathway")
        self.assertIn("7.5 hours", f.duration)
        self.assertIn("54 hours", p.duration)
        self.assertEqual(f.certificate_status, "Digital badge")
        self.assertEqual(p.certificate_status, "Unverified")
        self.assertIn("not a professional certification", _text(f))

    def test_fortinet_and_palo_alto_carry_no_invented_details(self):
        fort = _text(_by_id("fortinet-fcf-cybersecurity"))
        pan = _text(_by_id("paloalto-free-fundamentals"))
        for name in ("introduction to the threat landscape", "getting started in cybersecurity",
                     "technical introduction to cybersecurity", "nse 1", "nse 2"):
            self.assertNotIn(name, fort)
        for name in ("network security fundamentals", "cloud security fundamentals", "security operations fundamentals",
                     "cybersecurity foundation", "cybersecurity essentials", "hours"):
            self.assertNotIn(name, pan)
        for c in (_by_id("fortinet-fcf-cybersecurity"), _by_id("paloalto-free-fundamentals")):
            self.assertEqual(c.duration, "Unverified")
            self.assertEqual(c.verification, data.PARTIAL)
        self.assertEqual(_by_id("paloalto-free-fundamentals").certificate_status, "Unverified")
        self.assertIn("academic institutions", pan)

    def test_unsupported_details_stay_unverified(self):
        for cid in ("cisco-networking-essentials", "cisco-cybersecurity-essentials", "cisco-ethical-hacker"):
            self.assertEqual(_by_id(cid).duration, "Unverified")
        for cid in ("cisco-networking-essentials", "cisco-cybersecurity-essentials"):
            self.assertEqual(_by_id(cid).cost_status, "Unverified")


class FilterTests(unittest.TestCase):
    def ids(self, **kw):
        return [c.id for c in filter_courses(COURSES, **kw)]

    def test_no_filters_returns_everything_in_order(self):
        self.assertEqual(self.ids(), [c.id for c in COURSES])
        self.assertEqual(self.ids(query="   ", provider=ALL), [c.id for c in COURSES])
        self.assertEqual(len(filter_courses(COURSES, query=None)), 13)

    def test_search_by_course_name(self):
        self.assertEqual(self.ids(query="ethical"), ["cisco-ethical-hacker"])
        self.assertEqual(self.ids(query="ETHICAL hacker"), ["cisco-ethical-hacker"])
        self.assertEqual(self.ids(query="junior analyst"), ["cisco-junior-cybersecurity-analyst"])
        self.assertIn("ibm-cybersecurity-fundamentals", self.ids(query="fundamentals"))
        self.assertEqual(self.ids(query="entra"), ["ms-entra-identity-access"])

    def test_search_does_not_match_description_only_words(self):
        self.assertEqual(self.ids(query="coursera"), [])          # appears only in a description

    def test_empty_results(self):
        self.assertEqual(self.ids(query="zzzz-no-such-course"), [])
        self.assertEqual(self.ids(provider="Google", cost="Free"), [])
        self.assertEqual(group_by_provider([]), [])

    def test_provider_filter(self):
        self.assertEqual(len(self.ids(provider="Cisco Networking Academy")), 5)
        self.assertEqual(len(self.ids(provider="IBM SkillsBuild")), 2)
        self.assertEqual(self.ids(provider="Google"), ["google-cybersecurity-certificate"])
        self.assertEqual(len(self.ids(provider="Microsoft Learn")), 3)
        self.assertEqual(self.ids(provider="Not a provider"), [])

    def test_difficulty_filter(self):
        self.assertEqual(set(self.ids(difficulty="Beginner")),
                         {"cisco-intro-cybersecurity", "cisco-junior-cybersecurity-analyst", "ms-entra-identity-access"})
        self.assertEqual(self.ids(difficulty="Intermediate"), [])
        self.assertEqual(len(self.ids(difficulty="Not stated")), 10)

    def test_cost_status_filter(self):
        self.assertEqual(self.ids(cost="Paid"), ["google-cybersecurity-certificate"])
        free = set(self.ids(cost="Free"))
        self.assertNotIn("google-cybersecurity-certificate", free)
        self.assertEqual(free, {"cisco-intro-cybersecurity", "cisco-ethical-hacker", "cisco-junior-cybersecurity-analyst",
                                "ibm-cybersecurity-fundamentals", "ibm-cybersecurity-fluency-pathway",
                                "fortinet-fcf-cybersecurity", "paloalto-free-fundamentals"})
        self.assertEqual(set(self.ids(cost="Unverified")),
                         {"cisco-networking-essentials", "cisco-cybersecurity-essentials",
                          "ms-security-compliance-identity-concepts", "ms-security-solutions-capabilities",
                          "ms-entra-identity-access"})
        self.assertEqual(sum(len(self.ids(cost=c)) for c in COSTS), 13)

    def test_credential_status_filter(self):
        self.assertEqual(self.ids(credential="Completion certificate (paid programme)"), ["google-cybersecurity-certificate"])
        self.assertEqual(len(self.ids(credential="None verified")), 3)
        self.assertIn("cisco-ethical-hacker", self.ids(credential="Digital badge"))
        self.assertEqual(sum(len(self.ids(credential=c)) for c in CREDENTIALS), 13)

    def test_filters_combine_with_and(self):
        self.assertEqual(self.ids(provider="Cisco Networking Academy", cost="Free", credential="Digital badge",
                                  difficulty="Beginner"),
                         ["cisco-intro-cybersecurity", "cisco-junior-cybersecurity-analyst"])
        self.assertEqual(self.ids(query="essentials", cost="Free"), [])
        self.assertEqual(self.ids(query="essentials", cost="Unverified"),
                         ["cisco-networking-essentials", "cisco-cybersecurity-essentials"])

    def test_group_by_provider_keeps_catalogue_order_and_omits_empty(self):
        groups = group_by_provider(filter_courses(COURSES, cost="Free"))
        self.assertEqual([p.key for p, _ in groups], ["cisco", "ibm", "fortinet", "paloalto"])
        self.assertEqual(sum(len(c) for _, c in groups), 7)


class PageBase(unittest.TestCase):
    def setUp(self):
        self.fake = FakeStreamlit()
        self.st = self.fake.st
        self.st.tabs.side_effect = lambda labels: [mock.MagicMock() for _ in labels]
        self.values = {}
        self.st.text_input.side_effect = lambda *a, **k: self.values.get("query", "")
        self.st.selectbox.side_effect = lambda label, options, **k: self.values.get(label, ALL)
        self.mods = mock.patch.dict(sys.modules, {"streamlit": self.st})
        self.mods.start()
        self._purge()
        self.page = importlib.import_module("views.courses")

    def tearDown(self):
        self._purge()
        self.mods.stop()

    @staticmethod
    def _purge():
        for name in [m for m in list(sys.modules) if m.split(".")[0] in ("views", "components")]:
            del sys.modules[name]

    def html(self):
        return "\n".join(c.args[0] for c in self.st.markdown.call_args_list if c.kwargs.get("unsafe_allow_html"))

    def md(self):
        return "\n".join(c.args[0] for c in self.st.markdown.call_args_list if not c.kwargs.get("unsafe_allow_html"))


class PageRenderTests(PageBase):
    def test_imports_and_renders_header_notice_and_all_cards(self):
        self.page.render()
        self.st.title.assert_called_once_with("Courses")
        self.assertIn("change, rename or withdraw", self.st.info.call_args_list[0].args[0])
        html = self.html()
        self.assertEqual(html.count('class="cs-card"'), 13)
        for c in COURSES:
            self.assertIn(c.title.replace("&", "&amp;"), html)
        self.assertEqual(self.st.subheader.call_count, 6)
        self.assertIn("Showing 13 of 13 courses.", str(self.st.caption.call_args_list))

    def test_cards_show_status_cost_credential_duration_eligibility_and_source(self):
        self.page.render()
        html = self.html()
        for label in ("Provider:", "Level:", "Credential:", "Duration:", "Eligibility:", "Cost: Free", "Cost: Paid",
                      "Cost: Unverified", "Verified", "Partially verified", "checked 2026-11-26"):
            self.assertIn(label, html)
        for c in COURSES:
            self.assertIn(c.source_url, html)
        self.assertEqual(html.count("target=\"_blank\" rel=\"noopener noreferrer\""), 13)

    def test_official_buttons_have_unique_labels_and_right_urls(self):
        self.page.render()
        calls = self.st.link_button.call_args_list
        self.assertEqual([c.args[1] for c in calls], [c.official_url for c in COURSES])
        labels = [c.args[0] for c in calls]
        self.assertEqual(len(labels), len(set(labels)))          # duplicate link buttons would raise in Streamlit
        # Only the three Cisco entries link to a catalogue page; the rest link to a specific official page.
        self.assertEqual(sum(l.startswith("Open official catalogue") for l in labels), 3)
        self.assertEqual(sum(l.startswith("Visit Official Course") for l in labels), 10)
        self.assertTrue(all(c.args[1].startswith("https://") for c in calls))

    def test_two_column_layout_and_expanders(self):
        self.page.render()
        widths = [c.args[0] for c in self.st.columns.call_args_list]
        self.assertTrue(all(w == 2 for w in widths))
        expected_rows = sum((len(cs) + 1) // 2 for _, cs in group_by_provider(COURSES)) + 1   # +1: filter row
        self.assertEqual(len(widths), expected_rows)
        self.assertEqual(self.st.expander.call_count, 1 + sum(1 for c in COURSES if c.details))

    def test_google_resource_link_is_a_link_not_a_card(self):
        self.page.render()
        md = self.md()
        self.assertIn("https://cloud.google.com/learn", md)
        self.assertIn("not a verified course", md)

    def test_filter_widgets_use_only_courses_keys_and_reset_button(self):
        self.page.render()
        for call in list(self.st.text_input.call_args_list) + list(self.st.selectbox.call_args_list):
            self.assertTrue(call.kwargs["key"].startswith("courses_"))
        self.assertEqual(self.st.text_input.call_count, 1)
        self.assertEqual(self.st.selectbox.call_count, 4)
        options = {c.args[0]: c.args[1] for c in self.st.selectbox.call_args_list}
        self.assertEqual(options["Provider"][0], ALL)
        self.assertEqual(options["Cost"], [ALL, *COSTS])
        self.assertEqual(options["Difficulty"], [ALL, *DIFFICULTIES])
        self.assertEqual(options["Credential"], [ALL, *CREDENTIALS])
        self.assertEqual(self.st.button.call_args.kwargs["key"], "courses_reset")
        self.assertIs(self.st.button.call_args.kwargs["on_click"], self.page._reset)

    def test_search_and_filters_change_what_is_rendered(self):
        self.values["query"] = "ethical"
        self.page.render()
        self.assertEqual(self.st.link_button.call_count, 1)
        self.assertIn("Showing 1 of 13 courses.", str(self.st.caption.call_args_list))
        self.st.reset_mock()
        self.values.update({"query": "", "Provider": "Google"})
        self.page.render()
        self.assertEqual([c.args[1] for c in self.st.link_button.call_args_list],
                         ["https://grow.google/certificates/en_us/certificates/cybersecurity"])
        self.st.reset_mock()
        self.values.update({"Provider": ALL, "Cost": "Paid"})
        self.page.render()
        self.assertEqual(self.st.link_button.call_count, 1)

    def test_empty_results_show_a_message_and_no_cards(self):
        self.values["query"] = "zzzz-no-such-course"
        self.page.render()
        self.assertFalse(self.st.link_button.called)
        self.assertEqual(self.html().count('class="cs-card"'), 0)
        self.assertIn("No courses match", self.st.info.call_args_list[-1].args[0])
        self.assertIn("Showing 0 of 13 courses.", str(self.st.caption.call_args_list))
        self.assertTrue(self.st.button.called)              # the reset button is still available

    def test_unexpected_widget_values_fall_back_to_no_filter(self):
        self.values.update({"Provider": "Hacked Provider", "Cost": 42, "query": 7})
        self.page.render()
        self.assertEqual(self.st.link_button.call_count, 13)

    def test_reset_clears_only_the_courses_filter_keys(self):
        self.fake.session.update({"courses_query": "x", "courses_provider": "Google", "courses_cost": "Paid",
                                  "courses_difficulty": "Beginner", "courses_credential": "Digital badge",
                                  "page": "courses", "guide_history": ["keep"]})
        self.page._reset()
        s = self.fake.session
        self.assertEqual((s["courses_query"], s["courses_provider"], s["courses_cost"],
                          s["courses_difficulty"], s["courses_credential"]), ("", ALL, ALL, ALL, ALL))
        self.assertEqual((s["page"], s["guide_history"]), ("courses", ["keep"]))

    def test_dollar_signs_cannot_become_math(self):
        self.page.render()
        for text in [self.md(), self.html()]:
            self.assertIsNone(re.search(r"(?<![\\])\$", text), "unescaped $ would be parsed as LaTeX")
        self.assertIn("US\\$125", self.md())
        self.assertIn("US\\$49", self.md())

    def test_all_dataset_text_is_escaped_before_html(self):
        hostile = Course("x", "<script>alert(1)</script>", "Google", "<img src=x onerror=1>", "Beginner", "Free",
                         "Digital badge", "<b>1h</b>", "a & b", "https://grow.google/", "c", "2026-11-26",
                         'https://grow.google/"onmouseover="x', data.VERIFIED, ("US$5 and US$6", "<i>x</i>"))
        with mock.patch.object(self.page, "COURSES", (hostile,)):
            with mock.patch.object(self.page, "group_by_provider",
                                   lambda cs: [(data.provider_for("Google"), list(cs))]):
                self.page.render()
        html = self.html()
        self.assertNotIn("<script>", html)
        self.assertNotIn("<img", html)
        self.assertNotIn("<b>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("a &amp; b", html)
        self.assertNotIn('"onmouseover="', html)
        self.assertIn("US\\$5 and US\\$6", self.md())

    def test_rendering_writes_no_state_and_makes_no_network_or_other_widgets(self):
        before = dict(self.fake.session)
        self.page.render()
        self.assertEqual(dict(self.fake.session), before)
        for name in ("file_uploader", "checkbox", "text_area", "rerun"):
            self.assertFalse(getattr(self.st, name).called, name)
        src = _read("views/courses.py")
        for banned in ("import requests", "import urllib", "import subprocess", "import os", "from backend", "from config"):
            self.assertNotIn(banned, src)
        self.assertNotIn("COURSES = (", src)               # data stays in content/courses.py
        self.assertNotIn("Course(\"", src)


class IntegrationTests(unittest.TestCase):
    def test_registry_entry_and_single_learn_group(self):
        m = reg.get_module("courses")
        self.assertEqual((m.key, m.title, m.icon, m.group, m.status), ("courses", "Courses", "🎓", "Learn", "implemented"))
        self.assertIn("courses", reg.implemented_keys())
        groups = nav_state.nav_groups()
        names = [g for g, _ in groups]
        self.assertEqual(names.count("Learn"), 1)
        self.assertEqual(names, ["Platform", "Analysis", "QR Tools", "Protect", "Learn", "System"])
        self.assertEqual([m.key for m in dict(groups)["Learn"]], ["learning_center", "courses"])
        self.assertEqual(nav_state.NAV_GROUP_ORDER, ("Platform", "Analysis", "QR Tools", "Protect", "Learn", "System"))

    def test_router_wiring_and_sync_assertion_are_intact(self):
        src = _read("streamlit_app.py")
        self.assertIn('"courses": courses.render,', src)
        self.assertIn('"cyber_hygiene": cyber_hygiene.render,', src)
        self.assertIn('"learning_center": learning_center.render,', src)
        self.assertIn("assert set(PAGES) == set(reg.implemented_keys())", src)

    def test_navigate_opens_courses_and_closes_the_drawer(self):
        state = {nav_state.SIDEBAR_KEY: True, "page": "dashboard", "guide_history": ["keep"]}
        self.assertEqual(nav_state.navigate(state, "courses"), "courses")
        self.assertFalse(nav_state.is_sidebar_open(state))
        self.assertEqual(state["guide_history"], ["keep"])


class ShieldFlowTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeStreamlit()
        self.fake.st.tabs.side_effect = lambda labels: [mock.MagicMock() for _ in labels]
        self.fake.run_app()
        self.fake.press("landing_cta_hero")
        self.fake.run_app()

    def toggle(self):
        self.fake.press("cybershield_navtoggle_btn")
        self.fake.run_app()

    def test_courses_opens_through_the_shield_highlights_and_closes_the_drawer(self):
        self.fake.session["guide_history"] = [{"role": "user", "content": "keep"}]
        self.toggle()
        self.assertIn("cs_navitem_courses", self.fake.button_keys)
        self.assertIn("🎓", self.fake.button_labels["cs_navitem_courses"])
        self.assertIn("Courses", self.fake.button_labels["cs_navitem_courses"])
        self.fake.press("cs_navitem_courses")
        self.assertEqual(self.fake.session["page"], "courses")
        self.assertFalse(self.fake.session[nav_state.SIDEBAR_KEY])
        self.fake.run_app()
        self.assertFalse(self.fake.st.error.called)
        self.fake.st.title.assert_called_with("Courses")
        self.assertEqual(self.fake.st.link_button.call_count, 13)
        self.toggle()
        active = [k for k in self.fake.button_keys if k and k.startswith("cs_navitem_active_")]
        self.assertEqual(active, ["cs_navitem_active_courses"])
        self.assertEqual(self.fake.session["guide_history"][0]["content"], "keep")
        keys = [k for k in self.fake.button_keys if k]
        self.assertEqual(len(keys), len(set(keys)), "duplicate widget keys")

    def test_learning_center_and_cyber_hygiene_still_open_from_the_drawer(self):
        for key, title in (("learning_center", None), ("cyber_hygiene", "Cyber Hygiene")):
            self.toggle()
            self.assertIn(f"cs_navitem_{key}", self.fake.button_keys)
            self.fake.press(f"cs_navitem_{key}")
            self.assertEqual(self.fake.session["page"], key)
            self.fake.run_app()
            self.assertFalse(self.fake.st.error.called, key)
            if title:
                self.fake.st.title.assert_called_with(title)

    def test_dashboard_lists_courses_automatically(self):
        # dashboard.py is unchanged: it builds its tool cards from the registry.
        self.assertIn("Open Courses", self.fake.button_labels.values())
        self.assertIn("dash_open_courses", self.fake.button_keys)

    def test_every_page_renders(self):
        for key in reg.implemented_keys():
            fake = FakeStreamlit()
            fake.st.tabs.side_effect = lambda labels: [mock.MagicMock() for _ in labels]
            fake.run_app()
            fake.session["view"] = "app"
            fake.session["page"] = key
            fake.run_app()
            self.assertFalse(fake.st.error.called, key)


class KnowledgeTests(unittest.TestCase):
    def sections(self):
        return [s for s in load_sections() if s.page == "courses"]

    def test_topics_exist_with_page_key_and_fit_the_engine_limit(self):
        secs = self.sections()
        self.assertEqual(len(secs), 2)
        body = " ".join(s.body for s in secs)
        for needle in ("page key courses", "Learn group", "Cisco Networking Academy", "IBM SkillsBuild", "Google",
                       "Microsoft Learn", "Fortinet", "Palo Alto Networks", "Reset filters", "Verified",
                       "Partially verified", "digital badge", "completion certificate", "SC-900", "US$125",
                       "Cybersecurity Essentials", "Junior Cybersecurity Analyst Career Path", "paid Coursera"):
            self.assertIn(needle, body, needle)
        for s in secs:
            self.assertLessEqual(len(s.body), 1800, "engine truncates sections at 1800 characters")

    def test_knowledge_matches_the_implementation(self):
        body = " ".join(s.body for s in self.sections())
        for p in PROVIDERS:
            self.assertIn(p.name.split(" Training")[0], body)
        for c in COURSES:
            if c.id in ("cisco-ethical-hacker", "ibm-cybersecurity-fundamentals", "ibm-cybersecurity-fluency-pathway"):
                self.assertIn(c.title, body)
        low = body.lower()
        self.assertNotIn("network support and security", low)
        self.assertNotIn("isc2", low)
        self.assertNotIn("free certificate", low)
        self.assertNotIn("planned", low)

    def test_question_retrieval(self):
        for q in ("Where can I find cybersecurity courses?", "Is the Google Cybersecurity Certificate free?",
                  "What is the difference between Cybersecurity Essentials and the Junior Cybersecurity Analyst Career Path?",
                  "Does Microsoft Learn SC-900 training give a free certification?"):
            top = [s.page for s in retrieve(q, k=3)]
            self.assertIn("courses", top, q)

    def test_documentation_counts_and_navigation_are_consistent(self):
        km = _read("knowledge.md")
        self.assertIn("lists all ten pages", km)
        self.assertIn("Learn (Security Learning Center, Courses)", km)
        nav = next(s for s in load_sections() if s.title == "Navigation sidebar and shield button")
        self.assertIn("Courses", nav.body)
        readme = _read("README.md")
        self.assertIn("all ten pages", readme)
        self.assertIn("| Courses |", readme)
        self.assertIn("November 26, 2026", readme)
        arch = _read("docs/architecture.md")
        self.assertIn("## Courses directory", arch)
        self.assertIn("Platform, Analysis, QR Tools, Protect, Learn, System", arch)
        self.assertIn("Security Learning Center, Courses, Settings & API Configuration", arch)
        self.assertNotIn("eight-item", arch)


if __name__ == "__main__":
    unittest.main()
