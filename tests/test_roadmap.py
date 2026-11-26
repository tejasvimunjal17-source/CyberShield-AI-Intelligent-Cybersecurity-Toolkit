"""Roadmap (Phase 3): stage content, references to Courses / Learning Center / pages, rendering, navigation, docs.

Run against tests/fake_streamlit.py, a recording stand-in. These checks show what the app asks Streamlit to
render and how the Python control flow behaves. They do NOT show how the page looks in a real browser, and
they do not open any link or confirm that any course offer is still current.
"""

import ast
import importlib
import re
import sys
import unittest
from unittest import mock

import numpy  # noqa: F401  (import before the harness patches sys.modules, so this module also runs alone)

import app_registry as reg
from components import nav_state
from content import roadmap as data
from content.courses import COURSES, course_by_id
from content.learning_topics import TOPICS
from content.roadmap import DISCLAIMER, DURATION, NO_COURSE_NOTE, STAGES, Stage, stage_by_key
from cyberguide.knowledge_base import load_sections, retrieve
from tests.fake_streamlit import FakeStreamlit

REQUIRED_TITLES = [
    "Cybersecurity Fundamentals", "Computer and Operating System Fundamentals", "Networking Fundamentals",
    "Linux and Command-Line Basics", "Web Security Fundamentals", "Cybersecurity Tools and Practical Skills",
    "Security Operations and Threat Analysis", "Specialization and Career Preparation",
]
SECTION_LABELS = ("Learning objectives", "Important concepts", "Skills to develop", "Recommended topics",
                  "Practical activities", "Suggested learning resources", "Expected learning outcome",
                  "Recommended next stage")


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _stage_text(s: Stage) -> str:
    parts = [s.title, s.summary, s.outcome, *s.objectives, *s.skills, *s.topics, *s.activities,
             *(t + " " + m for t, m in s.concepts)]
    return " ".join(parts)


class ContentTests(unittest.TestCase):
    def test_eight_stages_in_the_required_order(self):
        self.assertEqual([s.title for s in STAGES], REQUIRED_TITLES)
        self.assertEqual([s.number for s in STAGES], list(range(1, 9)))
        keys = [s.key for s in STAGES]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(data.STAGE_KEYS, tuple(keys))

    def test_every_stage_has_every_required_part(self):
        for s in STAGES:
            for text in (s.title, s.short, s.icon, s.summary, s.outcome):
                self.assertTrue(text.strip(), s.key)
            self.assertGreaterEqual(len(s.objectives), 3, s.key)
            self.assertGreaterEqual(len(s.concepts), 5, s.key)
            self.assertGreaterEqual(len(s.skills), 3, s.key)
            self.assertGreaterEqual(len(s.topics), 4, s.key)
            self.assertGreaterEqual(len(s.activities), 3, s.key)
            for term, meaning in s.concepts:
                self.assertTrue(term.strip() and meaning.strip(), f"{s.key}: {term}")
                self.assertLessEqual(len(meaning), 170, f"{s.key}: '{term}' explanation is not short and simple")
            for item in (*s.objectives, *s.skills, *s.topics, *s.activities):
                self.assertTrue(item.strip())

    def test_next_stage_chain_is_correct(self):
        for a, b in zip(STAGES, STAGES[1:]):
            self.assertEqual(a.next_key, b.key, a.key)
            self.assertIs(stage_by_key(a.next_key), b)
        self.assertIsNone(STAGES[-1].next_key)
        self.assertIsNone(stage_by_key("nope"))

    def test_durations_are_self_paced_only(self):
        self.assertEqual(DURATION, "Self-paced")
        for s in STAGES:
            self.assertEqual(s.duration, "Self-paced", s.key)

    def test_roadmap_data_contains_no_links(self):
        blob = " ".join(_stage_text(s) for s in STAGES) + data.INTRO + data.DISCLAIMER + data.NO_COURSE_NOTE
        for bad in ("http://", "https://", "www.", "href", "<a ", "](", "<script"):
            self.assertNotIn(bad, blob.lower(), bad)
        src = _read("content/roadmap.py")
        self.assertNotIn("import streamlit", src)
        self.assertNotIn("https://", src)

    def test_course_references_exist_in_the_courses_data(self):
        for s in STAGES:
            for cid in s.course_ids:
                self.assertIsNotNone(course_by_id(cid), f"{s.key}: unknown course id {cid}")
            self.assertEqual(len(s.course_ids), len(set(s.course_ids)))

    def test_lesson_references_match_real_learning_center_titles(self):
        titles = {t for t, _ in TOPICS}
        for s in STAGES:
            for lesson in s.lessons:
                self.assertIn(lesson, titles, f"{s.key}: {lesson}")

    def test_page_references_are_real_implemented_pages_not_planned_ones(self):
        implemented = set(reg.implemented_keys())
        planned = {m.key for m in reg.planned()}
        for s in STAGES:
            for key in s.pages:
                self.assertIn(key, implemented, f"{s.key}: {key}")
                self.assertNotIn(key, planned)
                self.assertNotIn(key, ("dashboard", "roadmap"))
            self.assertEqual(len(s.pages), len(set(s.pages)))

    def test_links_to_courses_and_learning_center_are_present_where_relevant(self):
        for s in STAGES:
            if s.lessons:
                self.assertIn("learning_center", s.pages, s.key)
            if s.course_ids:
                self.assertIn("courses", s.pages, s.key)
            if not s.course_ids:
                self.assertNotIn("courses", s.pages, s.key)

    def test_stage_to_course_mapping(self):
        by = {s.key: s.course_ids for s in STAGES}
        self.assertEqual(by["fundamentals"], ("cisco-intro-cybersecurity", "ibm-cybersecurity-fundamentals",
                                              "ms-security-compliance-identity-concepts"))
        self.assertEqual(by["networking"], ("cisco-networking-essentials",))
        self.assertEqual(by["tools_practice"], ("cisco-ethical-hacker",))
        self.assertEqual(by["security_operations"], ("cisco-junior-cybersecurity-analyst", "ms-security-solutions-capabilities"))
        self.assertEqual(by["specialization"], ("google-cybersecurity-certificate", "fortinet-fcf-cybersecurity"))
        for no_course in ("computer_os", "linux_cli", "web_security"):
            self.assertEqual(by[no_course], (), no_course)          # no verified course: topics only

    def test_the_whole_catalogue_is_not_duplicated(self):
        used = [cid for s in STAGES for cid in s.course_ids]
        self.assertLess(len(set(used)), len(COURSES))
        self.assertEqual(len(used), len(set(used)))                  # no course repeated across stages
        self.assertTrue(all(len(s.course_ids) <= 3 for s in STAGES))
        for left_out in ("cisco-cybersecurity-essentials", "ibm-cybersecurity-fluency-pathway", "paloalto-free-fundamentals"):
            self.assertNotIn(left_out, used)

    def test_paid_courses_appear_only_where_clearly_optional(self):
        paid = [cid for s in STAGES for cid in s.course_ids if course_by_id(cid).cost_status == "Paid"]
        self.assertEqual(paid, ["google-cybersecurity-certificate"])
        self.assertEqual(stage_by_key("specialization").course_ids[0], paid[0])

    def test_no_job_or_certification_guarantees(self):
        blob = (" ".join(_stage_text(s) for s in STAGES) + data.INTRO + data.NO_COURSE_NOTE).lower()
        for bad in ("guarantee", "guaranteed", "you will get a job", "will be hired", "job-ready", "get certified"):
            self.assertNotIn(bad, blob, bad)
        d = DISCLAIMER.lower()
        self.assertIn("does not guarantee a job or a certification", d)
        self.assertIn("recommendations, not requirements", d)
        self.assertIn("separate exam", d)
        self.assertIn("written permission", d)

    def test_hands_on_activities_stay_on_systems_the_learner_owns(self):
        tools = stage_by_key("tools_practice")
        text = " ".join(tools.activities).lower()
        self.assertIn("that you own", text)
        self.assertIn("in that lab only", text)
        self.assertIn("authorization", " ".join(t.lower() for t, _ in tools.concepts))
        self.assertIn("router you own", " ".join(stage_by_key("networking").activities).lower())

    def test_credential_terms_are_not_confused(self):
        spec = {t: m for t, m in stage_by_key("specialization").concepts}
        self.assertIn("separate from a course", spec["Certification"])
        self.assertIn("not a professional certification", spec["Digital badge"])


class PageBase(unittest.TestCase):
    def setUp(self):
        self.fake = FakeStreamlit()
        self.st = self.fake.st
        self.st.button.return_value = False            # a bare MagicMock is truthy and would "click" every button
        self.mods = mock.patch.dict(sys.modules, {"streamlit": self.st})
        self.mods.start()
        self._purge()
        self.page = importlib.import_module("views.roadmap")

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
    def test_imports_and_renders_intro_disclaimer_and_all_stage_cards(self):
        self.page.render()
        self.st.title.assert_called_once_with("Roadmap")
        self.st.write.assert_called_once_with(data.INTRO)
        self.assertEqual(self.st.info.call_args.args[0], DISCLAIMER)
        html = self.html()
        self.assertEqual(html.count('class="cs-card"'), 8)
        for s in STAGES:
            self.assertIn(f"Stage {s.number}: {s.title}", html)
        self.assertEqual(html.count("Self-paced"), 8)

    def test_progress_strip_shows_all_eight_stages_in_order_without_double_escaping(self):
        self.page.render()
        strip = next(c.args[0] for c in self.st.markdown.call_args_list
                     if c.kwargs.get("unsafe_allow_html") and "→" in c.args[0])
        self.assertEqual(strip.count("cs-badge"), 8)
        self.assertEqual(strip.count("→"), 7)
        positions = [strip.index(f"{s.number}. ") for s in STAGES]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("Computers &amp; OS", strip)
        self.assertNotIn("&amp;amp;", strip)

    def test_each_stage_has_an_expander_with_every_required_section(self):
        self.page.render()
        labels = [c.args[0] for c in self.st.expander.call_args_list]
        self.assertEqual(labels, [f"Stage {s.number} details: {s.title}" for s in STAGES])
        md = self.md()
        for label in SECTION_LABELS:
            self.assertEqual(md.count(f"**{label}"), 8, label)
        for s in STAGES:
            self.assertIn(s.outcome, md)
            for t, m in s.concepts:
                self.assertIn(f"**{t}**: {m}", md)
            for a in s.activities:
                self.assertIn(a, md)

    def test_next_stage_is_shown_for_every_stage(self):
        self.page.render()
        md = self.md()
        for s in STAGES[:-1]:
            nxt = stage_by_key(s.next_key)
            self.assertIn(f"**Recommended next stage:** Stage {nxt.number}, {nxt.title}.", md)
        self.assertIn("**Recommended next stage:** none.", md)

    def test_details_use_two_columns_that_stack_on_mobile(self):
        self.page.render()
        widths = [c.args[0] for c in self.st.columns.call_args_list]
        self.assertTrue(all(isinstance(w, int) for w in widths))
        self.assertEqual(widths.count(2), 8 + 1 + sum(1 for s in STAGES if len(s.pages) == 2))   # details + top row + 2-button rows

    def test_course_links_come_from_the_courses_data_with_its_labels(self):
        self.page.render()
        md = self.md()
        course_urls = {c.official_url for c in COURSES}
        found = set(re.findall(r"\]\((https?://[^)\s]+)\)", md))
        self.assertTrue(found)
        self.assertTrue(found <= course_urls, f"URL not from the Courses data: {found - course_urls}")
        for s in STAGES:
            for cid in s.course_ids:
                c = course_by_id(cid)
                self.assertIn(f"]({c.official_url})", md)
                self.assertIn(f"Cost: {c.cost_status}. {c.verification}.", md)
                if c.verification != "Verified":
                    self.assertIn("details not fully verified", md)
        self.assertIn("Cost: Paid. Verified.", md)

    def test_recommended_courses_are_labelled_optional_and_no_course_stages_fall_back_to_topics(self):
        self.page.render()
        md = self.md()
        with_courses = sum(1 for s in STAGES if s.course_ids)
        self.assertEqual(md.count("Recommended courses (optional, not required)"), with_courses)
        captions = str(self.st.caption.call_args_list)
        self.assertEqual(captions.count(NO_COURSE_NOTE), 3)
        self.assertEqual(captions.count("Finishing one does not guarantee a job or a certification."), with_courses)

    def test_learning_center_lessons_are_named(self):
        self.page.render()
        md = self.md()
        for s in STAGES:
            for lesson in s.lessons:
                self.assertIn(f"*{lesson}*", md)

    def test_navigation_buttons_use_registered_pages_and_unique_keys(self):
        self.page.render()
        calls = self.st.button.call_args_list
        keys = [c.kwargs["key"] for c in calls]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertTrue(all(k.startswith("roadmap_") for k in keys))
        self.assertEqual(len(keys), 2 + sum(len(s.pages) for s in STAGES))
        for c in calls:
            title = c.args[0].removeprefix("Open ")
            self.assertIn(title, [m.title for m in reg.implemented()])
        labels = " ".join(c.args[0] for c in calls)
        self.assertIn("Open Courses", labels)
        self.assertIn("Open Security Learning Center", labels)
        self.assertNotIn("Phishing Awareness Lab", labels)
        self.assertFalse(self.st.link_button.called)

    def test_buttons_use_the_existing_go_to_helper_as_their_callback(self):
        self.page.render()
        by_key = {c.kwargs["key"]: c.kwargs for c in self.st.button.call_args_list}
        for s in STAGES:
            for page in s.pages:
                kw = by_key[f"roadmap_go_{s.key}_{page}"]
                self.assertIs(kw["on_click"], self.page.go_to)
                self.assertEqual(kw["args"], (page,))
        self.assertEqual(by_key["roadmap_go_networking_courses"]["args"], ("courses",))
        self.assertEqual(by_key["roadmap_top_courses"]["args"], ("courses",))
        self.assertEqual(by_key["roadmap_top_learning_center"]["args"], ("learning_center",))
        self.assertFalse(self.st.rerun.called)               # the callback runs before Streamlit's own rerun

    def test_dollar_signs_cannot_become_math(self):
        self.page.render()
        for text in (self.md(), self.html()):
            self.assertIsNone(re.search(r"(?<![\\])\$", text))

    def test_all_dataset_text_is_escaped(self):
        hostile = Stage("x", 1, "<script>alert(1)</script>", "<b>S</b>", "<i>", "<img src=x onerror=1>", ("US$5",),
                        (("<u>t</u>", "a & b"),), ("s",), ("t",), ("a",), "o", None)
        with mock.patch.object(self.page, "STAGES", (hostile,)):
            self.page.render()
        html = self.html()
        for raw in ("<script>", "<img", "<b>", "<i>"):
            self.assertNotIn(raw, html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("US\\$5", self.md())

    def test_rendering_writes_no_state_and_makes_no_network_calls(self):
        before = dict(self.fake.session)
        self.page.render()
        self.assertEqual(dict(self.fake.session), before)
        src = _read("views/roadmap.py")
        tree = ast.parse(src)
        imported = {n.names[0].name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import)}
        imported |= {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
        self.assertFalse(imported & {"requests", "backend", "config", "os", "subprocess", "urllib"})
        self.assertNotIn("Stage(", src)                         # content stays in content/roadmap.py
        self.assertNotIn("http://", src)
        self.assertNotIn("https://", src)                       # no URL is hard-coded in the view


class IntegrationTests(unittest.TestCase):
    def test_registry_entry_and_single_learn_group(self):
        m = reg.get_module("roadmap")
        self.assertEqual((m.key, m.title, m.icon, m.group, m.status), ("roadmap", "Roadmap", "🗺️", "Learn", "implemented"))
        self.assertIn("roadmap", reg.implemented_keys())
        self.assertEqual(len(reg.implemented_keys()), 11)
        groups = nav_state.nav_groups()
        names = [g for g, _ in groups]
        self.assertEqual(names.count("Learn"), 1)
        self.assertEqual(names, ["Platform", "Analysis", "QR Tools", "Protect", "Learn", "System"])
        self.assertEqual([x.key for x in dict(groups)["Learn"]], ["learning_center", "courses", "roadmap"])
        self.assertEqual(nav_state.NAV_GROUP_ORDER, ("Platform", "Analysis", "QR Tools", "Protect", "Learn", "System"))

    def test_router_wiring_and_sync_assertion_are_intact(self):
        src = _read("streamlit_app.py")
        for entry in ('"roadmap": roadmap.render,', '"courses": courses.render,', '"cyber_hygiene": cyber_hygiene.render,',
                      '"learning_center": learning_center.render,'):
            self.assertIn(entry, src)
        self.assertIn("assert set(PAGES) == set(reg.implemented_keys())", src)

    def test_navigate_opens_roadmap_and_closes_the_drawer(self):
        state = {nav_state.SIDEBAR_KEY: True, "page": "dashboard", "guide_history": ["keep"]}
        self.assertEqual(nav_state.navigate(state, "roadmap"), "roadmap")
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

    def test_roadmap_opens_through_the_shield_highlights_and_closes_the_drawer(self):
        self.fake.session["guide_history"] = [{"role": "user", "content": "keep"}]
        self.toggle()
        self.assertIn("cs_navitem_roadmap", self.fake.button_keys)
        self.assertIn("🗺️", self.fake.button_labels["cs_navitem_roadmap"])
        self.fake.press("cs_navitem_roadmap")
        self.assertEqual(self.fake.session["page"], "roadmap")
        self.assertFalse(self.fake.session[nav_state.SIDEBAR_KEY])
        self.fake.run_app()
        self.assertFalse(self.fake.st.error.called)
        self.fake.st.title.assert_called_with("Roadmap")
        self.toggle()
        active = [k for k in self.fake.button_keys if k and k.startswith("cs_navitem_active_")]
        self.assertEqual(active, ["cs_navitem_active_roadmap"])
        self.assertEqual(self.fake.session["guide_history"][0]["content"], "keep")
        keys = [k for k in self.fake.button_keys if k]
        self.assertEqual(len(keys), len(set(keys)), "duplicate widget keys")

    def test_roadmap_buttons_open_the_real_courses_and_learning_center_pages(self):
        for key, page, title in (("roadmap_top_courses", "courses", "Courses"),
                                 ("roadmap_top_learning_center", "learning_center", "Security Learning Center"),
                                 ("roadmap_go_fundamentals_cyber_hygiene", "cyber_hygiene", "Cyber Hygiene")):
            self.fake.session["page"] = "roadmap"
            self.fake.run_app()
            self.assertIn(key, self.fake.button_keys)
            self.fake.press(key)
            self.fake.run_app()
            self.assertEqual(self.fake.session["page"], page)
            self.assertFalse(self.fake.st.error.called, page)
            self.fake.st.title.assert_called_with(title)

    def test_existing_learn_and_protect_pages_still_open_from_the_drawer(self):
        for key in ("learning_center", "courses", "cyber_hygiene"):
            self.toggle()
            self.assertIn(f"cs_navitem_{key}", self.fake.button_keys)
            self.fake.press(f"cs_navitem_{key}")
            self.assertEqual(self.fake.session["page"], key)
            self.fake.run_app()
            self.assertFalse(self.fake.st.error.called, key)

    def test_dashboard_lists_roadmap_automatically(self):
        # dashboard.py is unchanged: it builds its tool cards from the registry.
        self.assertIn("Open Roadmap", self.fake.button_labels.values())
        self.assertIn("dash_open_roadmap", self.fake.button_keys)

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
        return [s for s in load_sections() if s.page == "roadmap"]

    def test_topics_exist_with_page_key_and_fit_the_engine_limit(self):
        secs = self.sections()
        self.assertEqual(len(secs), 2)
        body = " ".join(s.body for s in secs)
        for needle in ["page key roadmap", "Learn group", "Open Roadmap", "Self-paced", "eight stages",
                       "does not guarantee a job or a certification", "written permission", *REQUIRED_TITLES]:
            self.assertIn(needle, body, needle)
        for s in secs:
            self.assertLessEqual(len(s.body), 1800, "engine truncates sections at 1800 characters")

    def test_knowledge_matches_the_implementation(self):
        body = " ".join(s.body for s in self.sections())
        for s in STAGES:
            for lesson in s.lessons:
                self.assertIn(lesson, body, lesson)
        for needle in ("Introduction to Cybersecurity", "Networking Essentials", "Ethical Hacker",
                       "Junior Cybersecurity Analyst Career Path", "Google Cybersecurity Certificate", "FCF", "paid"):
            self.assertIn(needle, body, needle)
        low = body.lower()
        for not_implemented in ("internship", "government website", "coming soon"):
            self.assertNotIn(not_implemented, low)

    def test_question_retrieval(self):
        for q in ("Where do I start learning cybersecurity as a complete beginner?",
                  "What are the stages of the cybersecurity roadmap?",
                  "Which courses go with the security operations stage of the roadmap?"):
            top = [s.page for s in retrieve(q, k=3)]
            self.assertIn("roadmap", top, q)

    def test_documentation_counts_and_navigation_are_consistent(self):
        km = _read("knowledge.md")
        self.assertIn("lists all eleven pages", km)
        self.assertIn("Learn (Security Learning Center, Courses, Roadmap)", km)
        self.assertNotIn("lists all ten pages", km)
        nav = next(s for s in load_sections() if s.title == "Navigation sidebar and shield button")
        self.assertIn("Roadmap", nav.body)
        readme = _read("README.md")
        self.assertIn("all eleven pages", readme)
        self.assertNotIn("all ten pages", readme)
        self.assertIn("| Roadmap |", readme)
        arch = _read("docs/architecture.md")
        self.assertIn("## Roadmap", arch)
        self.assertIn("Security Learning Center, Courses, Roadmap, Settings & API Configuration", arch)
        self.assertIn("Platform, Analysis, QR Tools, Protect, Learn, System", arch)


if __name__ == "__main__":
    unittest.main()
