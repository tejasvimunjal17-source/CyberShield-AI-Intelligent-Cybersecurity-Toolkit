"""Internships (Phase 4): dataset rules, search/filters, page rendering, navigation, CyberGuide docs.

Run against tests/fake_streamlit.py, a recording stand-in. These checks show what the app asks Streamlit to
render and how the Python control flow behaves. They do NOT show how the page looks in a real browser, and
they do not open any link or confirm that any programme, date or fee is still current.
"""

import dataclasses
import importlib
import re
import sys
import unittest
from unittest import mock

import numpy  # noqa: F401  (import before the harness patches sys.modules, so this module also runs alone)

import app_registry as reg
from components import nav_state
from content import internships as data
from content.internships import (ALL, APP_STATUSES, CATEGORIES, ENTRIES, FORMATS, NEXT_CYCLE_NOTE, OFFICIAL_HOSTS, PAY,
                                 REGIONS, SAFETY_WARNING, SOURCE_HOSTS, TIPS, VERIFICATIONS, Entry, entries_by_section,
                                 entry_by_id, filter_entries)
from cyberguide.knowledge_base import load_sections, retrieve
from tests.fake_streamlit import FakeStreamlit

# Every URL the dataset may contain. Each was found on an official page (or, for the GPCSSI announcement and the
# PTI report, an identified announcement or news source) during the 2026-11-26 research. A new link must be opened
# and added here by a person: this set is the guard against invented links.
VERIFIED_URLS = frozenset({
    "https://internship.aicte-india.org",
    "https://aicte.gov.in/sites/default/files/AICTE%20Advertisement%20for%20intern.pdf",
    "https://www.cisa.gov/pathways-interns",
    "https://niccs.cisa.gov/resources/internships-apprenticeships",
    "https://x.com/tandonrakshit/status/2050208882602201333",
    "https://theprint.in/india/gurugram-gpcssi-2025-launched-to-promote-cybersecurity-awareness/2645253",
    "https://simplify.jobs/internships", "https://simplify.jobs/",
    "https://github.com/paralax/awesome-cybersecurity-internships",
    "https://joinhandshake.com/",
    "https://www.indeed.com/",
    "https://www.glassdoor.com/",
    "https://www.linkedin.com/", "https://www.linkedin.com/help/linkedin/answer/154",
    "https://theinterngroup.com/career-fields/cyber-security-internships",
    "https://theinterngroup.com/resources/faq",
})

REQUIRED_IDS = ("aicte-national-internship-portal", "cisa-cyber-it-internships", "gpcssi", "simplify",
                "awesome-cybersecurity-internships", "handshake", "indeed", "glassdoor", "linkedin", "api-intern-group")
PLATFORM_IDS = ("simplify", "handshake", "indeed", "glassdoor", "linkedin")
PLACEHOLDER_WORDS = ("example.com", "todo", "tbd", "xxx", "lorem", "placeholder", "localhost", "127.0.0.1",
                     "forms.gle", "docs.google.com/forms", "bit.ly")


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _text(e: Entry) -> str:
    return " ".join([e.name, e.organizer, e.description, e.eligibility, e.location, e.cost_note, e.duration,
                     e.certificate, e.status_note, *e.notes]).lower()


def _e(entry_id: str) -> Entry:
    return entry_by_id(entry_id)


class DatasetTests(unittest.TestCase):
    def test_required_listings_present_with_stable_unique_ids(self):
        ids = [e.id for e in ENTRIES]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(tuple(ids), REQUIRED_IDS)
        self.assertEqual(data.ENTRY_IDS, REQUIRED_IDS)
        for i in ids:
            self.assertRegex(i, r"^[a-z0-9-]+$")

    def test_required_fields_and_vocabularies(self):
        for e in ENTRIES:
            for field in ("id", "name", "organizer", "section", "category", "description", "eligibility", "location",
                          "region", "work_format", "pay_status", "cost_note", "duration", "certificate",
                          "application_status", "official_url", "official_kind", "button_label", "source_url",
                          "last_verified", "verification"):
                self.assertTrue(str(getattr(e, field)).strip(), f"{e.id}.{field}")
            self.assertIn(e.section, ("government", "programme", "discovery"))
            self.assertIn(e.category, CATEGORIES, e.id)
            self.assertIn(e.region, REGIONS, e.id)
            self.assertIn(e.work_format, FORMATS, e.id)
            self.assertIn(e.pay_status, PAY, e.id)
            self.assertIn(e.application_status, APP_STATUSES, e.id)
            self.assertIn(e.verification, VERIFICATIONS, e.id)
            self.assertIn(e.official_kind, ("official", "announcement"))
            self.assertRegex(e.last_verified, r"^\d{4}-\d{2}-\d{2}$")

    def test_urls_are_https_allow_listed_and_in_the_verified_list(self):
        for e in ENTRIES:
            for url, hosts in ((e.official_url, OFFICIAL_HOSTS), (e.source_url, SOURCE_HOSTS),
                               *[(u, SOURCE_HOSTS) for u in e.extra_sources]):
                self.assertTrue(url.startswith("https://"), f"{e.id}: {url}")
                self.assertIn(url.split("/")[2], hosts, f"{e.id}: {url}")
                self.assertIn(url, VERIFIED_URLS, f"{e.id}: unverified link {url}")
                self.assertNotIn(" ", url)

    def test_no_placeholder_old_form_or_unverified_domain_links(self):
        blob = " ".join(_text(e) + " " + e.official_url + " " + e.source_url + " " + (e.application_url or "") for e in ENTRIES)
        for word in PLACEHOLDER_WORDS:
            self.assertNotIn(word, blob, word)
        urls = " ".join(e.official_url + " " + e.source_url + " " + " ".join(e.extra_sources) for e in ENTRIES)
        self.assertNotIn("theinternsgroup.com", urls)            # unverified domain supplied by the user: never linked
        self.assertNotIn("cybersecurityjobs.com", urls.lower())  # excluded: no official page or listing confirmed

    def test_no_application_link_exists_and_nothing_is_marked_open(self):
        for e in ENTRIES:
            self.assertIsNone(e.application_url, e.id)
            self.assertNotEqual(e.application_status, data.OPEN, e.id)
            if e.application_url is not None:                      # the invariant for any future entry
                self.assertEqual(e.application_status, data.OPEN)
                self.assertTrue(e.application_url.startswith("https://"))

    def test_excluded_listings_are_absent(self):
        blob = " ".join(e.name.lower() + e.organizer.lower() for e in ENTRIES)
        self.assertNotIn("cybersecurityjobs", blob)
        self.assertNotIn("cybersecjobs", blob)
        self.assertNotIn("isc2", blob)

    def test_gpcssi_is_closed_partially_verified_and_not_overclaimed(self):
        g = _e("gpcssi")
        self.assertEqual((g.application_status, g.verification, g.official_kind), (data.CLOSED, data.PARTIAL, "announcement"))
        self.assertIn(NEXT_CYCLE_NOTE, g.status_note)
        self.assertEqual(NEXT_CYCLE_NOTE, "Next application cycle not yet officially announced. Check official announcements for updates.")
        self.assertEqual(g.button_label, "View Announcement Source")
        self.assertIn("6 May 2026", g.status_note)
        self.assertIn("not an official government portal", " ".join(g.notes))
        self.assertIn("old registration forms are deliberately not linked", " ".join(g.notes))
        self.assertTrue(g.official_url.startswith("https://x.com/tandonrakshit/"))
        self.assertEqual(g.pay_status, "Not stated")
        self.assertIn("not confirmed by an official source", g.cost_note)
        self.assertTrue(g.certificate.startswith("Unverified"))
        self.assertIn("training programme, not an employment internship", g.description)
        t = _text(g)
        for unconfirmed in ("malware analysis", "reverse engineering", "forensic", "dav public school", "stipend of"):
            self.assertNotIn(unconfirmed, t, unconfirmed)
        self.assertIn("partly virtual", t)                         # format varies by edition, so never plain "in-person"
        self.assertEqual(g.work_format, "Varies")

    def test_cisa_citizenship_and_international_eligibility_are_explicit(self):
        c = _e("cisa-cyber-it-internships")
        self.assertEqual((c.region, c.verification, c.application_status), ("United States", data.VERIFIED, data.UNCONFIRMED))
        for needle in ("U.S. citizenship is required", "can only employ U.S. citizens", "enrolled student",
                       "not open to international students, including students from India"):
            self.assertIn(needle, c.eligibility)
        self.assertNotIn("indian students can", _text(c))
        self.assertNotIn("indian students are eligible", _text(c))
        self.assertIn("10 to 12 weeks", c.duration)
        self.assertIn("individual USAJOBS vacancies", c.status_note)
        self.assertIn("each vacancy has its own rules", " ".join(c.notes).lower())
        self.assertEqual(c.certificate, "Not stated")

    def test_aicte_is_a_discovery_portal_with_unconfirmed_availability(self):
        a = _e("aicte-national-internship-portal")
        self.assertEqual((a.verification, a.application_status, a.region), (data.PARTIAL, data.UNCONFIRMED, "India"))
        self.assertIn("does not itself provide every listed internship", a.description)
        self.assertIn("not every listing is about cybersecurity", a.description)
        self.assertEqual(a.button_label, "Visit Official Portal")
        self.assertIn("reported by third parties", " ".join(a.notes).lower())
        self.assertEqual(a.certificate, "Unverified")

    def test_discovery_platforms_are_not_presented_as_providers(self):
        for pid in PLATFORM_IDS:
            e = _e(pid)
            self.assertEqual((e.category, e.section, e.button_label), ("Discovery platform", "discovery", "Visit Official Platform"), pid)
            self.assertTrue("not an internship provider" in e.description or "not an employer" in e.description, pid)
            self.assertTrue(e.certificate.startswith("Not applicable"), pid)
            self.assertEqual(e.verification, data.PARTIAL, pid)
        self.assertIn("Indeed, Inc.", _e("glassdoor").organizer)
        self.assertIn("separate from internships", " ".join(_e("handshake").notes))
        self.assertIn("do not assume every student can see every listing", _e("handshake").eligibility)

    def test_github_list_is_labelled_community_maintained(self):
        g = _e("awesome-cybersecurity-internships")
        self.assertEqual((g.category, g.button_label), ("Community-curated list", "Open Community Resource"))
        self.assertIn("Community-maintained", g.organizer)
        self.assertIn("not an employer or a government portal", g.description)
        self.assertIn("paralax", g.organizer)
        self.assertEqual(g.official_url, "https://github.com/paralax/awesome-cybersecurity-internships")

    def test_api_intern_group_is_a_paid_programme_not_a_free_internship(self):
        a = _e("api-intern-group")
        self.assertTrue(a.paid_programme)
        self.assertEqual((a.pay_status, a.category), ("Fee-based", "Paid placement service"))
        self.assertIn("This is not a free internship", a.description)
        self.assertEqual(a.official_url.split("/")[2], "theinterngroup.com")
        notes = " ".join(a.notes)
        self.assertIn("could not be verified and is not used", notes)
        self.assertIn("shows the name API Intern Group", notes)
        self.assertIn("This is the organisation's claim, not independently verified", notes)
        self.assertIn("expect an unpaid internship", a.cost_note)
        self.assertIn("This is not a free internship", a.description)
        self.assertEqual([e.id for e in ENTRIES if e.paid_programme], ["api-intern-group"])
        self.assertEqual([e.id for e in ENTRIES if e.pay_status == "Fee-based"], ["api-intern-group"])

    def test_no_unsupported_certificate_pay_or_eligibility_claims(self):
        for e in ENTRIES:
            self.assertRegex(e.certificate, r"^(Unverified|Not stated|Not applicable)", e.id)
            self.assertNotIn(e.pay_status, ("Paid", "Unpaid"), f"{e.id}: pay was not confirmed as a single status")
        blob = " ".join(_text(e) for e in ENTRIES)
        self.assertIsNone(re.search(r"[$\u20b9\u00a3\u20ac]\s?\d", blob), "no invented amounts")
        self.assertNotIn("guaranteed placement", blob)
        self.assertNotIn("you will get", blob)
        for e in ENTRIES:
            if e.id not in ("gpcssi", "cisa-cyber-it-internships"):
                self.assertRegex(e.duration, r"^(Varies|Not stated)", e.id)       # durations only where verified

    def test_verification_labels_are_honest(self):
        self.assertEqual({e.id for e in ENTRIES if e.verification == data.VERIFIED}, {"cisa-cyber-it-internships"})
        self.assertFalse([e for e in ENTRIES if e.verification == data.UNVERIFIED])
        self.assertEqual({e.id for e in ENTRIES if e.application_status == data.CLOSED}, {"gpcssi"})

    def test_indeed_and_linkedin_search_guidance(self):
        self.assertEqual(_e("indeed").search_terms, ("Cybersecurity Intern", "SOC Analyst Intern", "Information Security Intern",
                                                    "GRC Intern", "Security Analyst Intern"))
        li = " ".join(_e("linkedin").notes).lower()
        for needle in ("employment type", "experience level", "internship", "remote or hybrid"):
            self.assertIn(needle, li)
        self.assertIn("could not be reviewed automatically", li)

    def test_tips_and_safety_text(self):
        self.assertEqual(SAFETY_WARNING, "Never pay an unknown recruiter for a guaranteed internship or job. Verify the "
                         "organisation, official domain and application process before sharing personal documents or "
                         "sensitive information.")
        titles = [t for t, _ in TIPS]
        for needle in ("resume", "portfolio", "networking and operating system", "legally", "interviews", "emails", "legitimate"):
            self.assertTrue(any(needle in t.lower() for t in titles), needle)
        blob = " ".join(p for _, pts in TIPS for p in pts).lower() + data.INTRO.lower()
        self.assertNotIn("guarantee a", blob.replace("nothing here promises", ""))
        self.assertIn("nothing here promises a placement, a job or a certificate", data.INTRO)


class FilterTests(unittest.TestCase):
    def ids(self, **kw):
        return [e.id for e in filter_entries(ENTRIES, **kw)]

    def test_defaults_and_search(self):
        self.assertEqual(self.ids(), list(REQUIRED_IDS))
        self.assertEqual(self.ids(query="  "), list(REQUIRED_IDS))
        self.assertEqual(len(filter_entries(ENTRIES, query=None)), 10)
        self.assertEqual(self.ids(query="police"), ["gpcssi"])
        self.assertEqual(self.ids(query="LINKEDIN"), ["linkedin"])
        self.assertEqual(self.ids(query="cisa cyber"), ["cisa-cyber-it-internships"])
        self.assertEqual(self.ids(query="api group"), ["api-intern-group"])

    def test_search_uses_names_only(self):
        self.assertEqual(self.ids(query="visa"), [])            # appears only in a cost note
        self.assertEqual(self.ids(query="zzzz-nothing"), [])

    def test_category_filter(self):
        self.assertEqual(self.ids(category="Government / national portal"), ["aicte-national-internship-portal"])
        self.assertEqual(self.ids(category="Government internship programme"), ["cisa-cyber-it-internships"])
        self.assertEqual(self.ids(category="Training programme"), ["gpcssi"])
        self.assertEqual(len(self.ids(category="Discovery platform")), 5)
        self.assertEqual(self.ids(category="Paid placement service"), ["api-intern-group"])
        self.assertEqual(sum(len(self.ids(category=c)) for c in CATEGORIES), 10)

    def test_location_filter(self):
        self.assertEqual(self.ids(region="India"), ["aicte-national-internship-portal", "gpcssi"])
        self.assertEqual(self.ids(region="United States"), ["cisa-cyber-it-internships", "awesome-cybersecurity-internships"])
        self.assertEqual(self.ids(region="International / multiple"), ["api-intern-group"])
        self.assertEqual(sum(len(self.ids(region=r)) for r in REGIONS), 10)

    def test_format_filter(self):
        self.assertEqual(self.ids(work_format="Remote"), [])
        self.assertEqual(self.ids(work_format="In-person"), [])
        self.assertEqual(self.ids(work_format="Not stated"), ["cisa-cyber-it-internships", "awesome-cybersecurity-internships"])
        self.assertEqual(len(self.ids(work_format="Varies")), 8)
        self.assertEqual(sum(len(self.ids(work_format=f)) for f in FORMATS), 10)

    def test_paid_unpaid_fee_filter(self):
        self.assertEqual(self.ids(pay="Fee-based"), ["api-intern-group"])
        self.assertEqual(self.ids(pay="Paid"), [])
        self.assertEqual(self.ids(pay="Unpaid"), [])
        self.assertEqual(self.ids(pay="Not stated"), ["gpcssi"])
        self.assertEqual(len(self.ids(pay="Varies")), 8)
        self.assertEqual(sum(len(self.ids(pay=p)) for p in PAY), 10)

    def test_application_status_filter(self):
        self.assertEqual(self.ids(app_status="Applications Closed"), ["gpcssi"])
        self.assertEqual(self.ids(app_status="Applications Open"), [])
        self.assertEqual(len(self.ids(app_status="Availability Unconfirmed")), 9)
        self.assertEqual(sum(len(self.ids(app_status=s)) for s in APP_STATUSES), 10)

    def test_verification_filter(self):
        self.assertEqual(self.ids(verification="Verified"), ["cisa-cyber-it-internships"])
        self.assertEqual(len(self.ids(verification="Partially Verified")), 9)
        self.assertEqual(self.ids(verification="Unverified"), [])

    def test_filters_combine_with_and(self):
        self.assertEqual(self.ids(region="India", app_status="Applications Closed"), ["gpcssi"])
        self.assertEqual(self.ids(region="India", verification="Verified"), [])
        self.assertEqual(self.ids(category="Discovery platform", query="intern"), [])          # only the list and the service say "intern"
        self.assertEqual(self.ids(query="intern", region="International / multiple"), ["api-intern-group"])
        self.assertEqual(self.ids(query="intern", pay="Fee-based", verification="Partially Verified"), ["api-intern-group"])

    def test_sections_keep_order_and_omit_empty_ones(self):
        groups = entries_by_section(ENTRIES)
        self.assertEqual([g[0] for g in groups], ["government", "programme", "discovery"])
        self.assertEqual([len(g[3]) for g in groups], [2, 1, 7])
        only = entries_by_section(filter_entries(ENTRIES, region="India"))
        self.assertEqual([g[0] for g in only], ["government", "programme"])
        self.assertEqual(entries_by_section([]), [])


class PageBase(unittest.TestCase):
    def setUp(self):
        self.fake = FakeStreamlit()
        self.st = self.fake.st
        self.values = {}
        self.st.text_input.side_effect = lambda *a, **k: self.values.get("query", "")
        self.st.selectbox.side_effect = lambda label, options, **k: self.values.get(label, ALL)
        self.mods = mock.patch.dict(sys.modules, {"streamlit": self.st})
        self.mods.start()
        self._purge()
        self.page = importlib.import_module("views.internships")

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
    def test_renders_header_notice_sections_cards_tips_and_safety(self):
        self.page.render()
        self.st.title.assert_called_once_with("Internships")
        self.assertIn("No application link is shown unless an official source confirms", self.st.info.call_args_list[0].args[0])
        self.assertEqual([c.args[0] for c in self.st.subheader.call_args_list],
                         ["Government and National Internship Portals", "Cybersecurity-Specific Programmes",
                          "Internship Discovery Websites", "Application Preparation Tips",
                          "Important Safety and Verification Advice"])
        html = self.html()
        self.assertEqual(html.count('class="cs-card"'), 10)
        for e in ENTRIES:
            self.assertIn(e.name.replace("&", "&amp;"), html)
        self.assertEqual(self.st.warning.call_args.args[0], SAFETY_WARNING)
        self.assertIn("Showing 10 of 10 listings.", str(self.st.caption.call_args_list))

    def test_cards_show_every_required_field_and_status_labels(self):
        self.page.render()
        html = self.html()
        for label in ("Organiser:", "Type:", "Eligibility:", "Location:", "Format:", "Pay or fee:", "Duration:",
                      "Certificate:", "Last verified 2026-11-26", "Partially Verified", "Verified",
                      "Availability Unconfirmed", "Applications Closed", "Paid Programme"):
            self.assertIn(label, html)
        self.assertEqual(html.count("Paid Programme"), 1)
        self.assertEqual(html.count("Applications Closed"), 1)
        self.assertNotIn("Applications Open", html)
        self.assertIn(NEXT_CYCLE_NOTE, html)
        for e in ENTRIES:
            self.assertIn(e.source_url, html)
        self.assertEqual(html.count('target="_blank" rel="noopener noreferrer"'), 10)

    def test_official_buttons_use_the_right_labels_and_never_say_apply(self):
        self.page.render()
        calls = self.st.link_button.call_args_list
        self.assertEqual([c.args[1] for c in calls], [e.official_url for e in ENTRIES])
        labels = [c.args[0] for c in calls]
        self.assertEqual(len(labels), len(set(labels)))
        for label, e in zip(labels, ENTRIES):
            self.assertTrue(label.startswith(e.button_label), label)
            self.assertNotIn("Apply", label)
        self.assertEqual(sum(l.startswith("Visit Official Platform") for l in labels), 5)
        self.assertIn("View Announcement Source → Gurugram Police Cyber Security Summer Internship (GPCSSI)", labels)

    def test_application_button_only_for_open_status_with_an_official_url(self):
        base = _e("simplify")
        url = "https://simplify.jobs/internships"
        cases = [(dataclasses.replace(base, application_status=data.OPEN, application_url=url), 2),
                 (dataclasses.replace(base, application_status=data.CLOSED, application_url=url), 1),
                 (dataclasses.replace(base, application_status=data.OPEN, application_url=None), 1),
                 (base, 1)]
        for entry, buttons in cases:
            self.st.reset_mock()
            with mock.patch.object(self.page, "ENTRIES", (entry,)):
                self.page.render()
            self.assertEqual(self.st.link_button.call_count, buttons, entry.application_status)
            if buttons == 2:
                self.assertIn("Apply Now", self.st.link_button.call_args_list[1].args[0])

    def test_expanders_tips_and_details(self):
        self.page.render()
        self.assertEqual(self.st.expander.call_count, 1 + sum(1 for e in ENTRIES if e.notes or e.search_terms) + len(TIPS))
        md = self.md()
        for title, points in TIPS:
            for p in points:
                self.assertIn(p, md)
        self.assertIn("Suggested search terms:", md)
        self.assertIn("`SOC Analyst Intern`", md)

    def test_filter_widgets_use_only_internships_keys_and_a_reset_button(self):
        self.page.render()
        calls = list(self.st.text_input.call_args_list) + list(self.st.selectbox.call_args_list)
        self.assertEqual(len(calls), 7)
        self.assertTrue(all(c.kwargs["key"].startswith("internships_") for c in calls))
        options = {c.args[0]: c.args[1] for c in self.st.selectbox.call_args_list}
        self.assertEqual(set(options), {"Category", "Location", "Remote, in-person or hybrid", "Paid, unpaid or fee-based",
                                        "Application status", "Verification status"})
        self.assertEqual(options["Category"], [ALL, *CATEGORIES])
        self.assertEqual(options["Application status"], [ALL, *APP_STATUSES])
        self.assertEqual(self.st.button.call_args_list[-1].kwargs["key"], "internships_reset")
        self.assertIs(self.st.button.call_args_list[-1].kwargs["on_click"], self.page._reset)

    def test_quick_links_use_go_to_as_the_callback(self):
        self.page.render()
        by_key = {c.kwargs["key"]: c.kwargs for c in self.st.button.call_args_list}
        for key in ("roadmap", "courses"):
            kw = by_key[f"internships_top_{key}"]
            self.assertIs(kw["on_click"], self.page.go_to)
            self.assertEqual(kw["args"], (key,))
        self.assertFalse(self.st.rerun.called)

    def test_search_and_filters_change_the_cards(self):
        self.values["query"] = "police"
        self.page.render()
        self.assertEqual(self.st.link_button.call_count, 1)
        self.assertIn("Showing 1 of 10 listings.", str(self.st.caption.call_args_list))
        self.st.reset_mock()
        self.values.update({"query": "", "Location": "India"})
        self.page.render()
        self.assertEqual(self.st.link_button.call_count, 2)
        self.st.reset_mock()
        self.values.update({"Location": ALL, "Paid, unpaid or fee-based": "Fee-based"})
        self.page.render()
        self.assertEqual([c.args[1] for c in self.st.link_button.call_args_list], [_e("api-intern-group").official_url])

    def test_empty_results_show_a_message_and_still_show_tips_and_safety(self):
        self.values["query"] = "zzzz-nothing"
        self.page.render()
        self.assertFalse(self.st.link_button.called)
        self.assertEqual(self.html().count('class="cs-card"'), 0)
        self.assertIn("No listings match", self.st.info.call_args_list[-1].args[0])
        self.assertIn("Showing 0 of 10 listings.", str(self.st.caption.call_args_list))
        subs = [c.args[0] for c in self.st.subheader.call_args_list]
        self.assertEqual(subs, ["Application Preparation Tips", "Important Safety and Verification Advice"])
        self.assertTrue(self.st.button.called)

    def test_unexpected_widget_values_fall_back_to_no_filter(self):
        self.values.update({"Category": "Hacked", "Location": 5, "query": 3})
        self.page.render()
        self.assertEqual(self.st.link_button.call_count, 10)

    def test_reset_clears_only_the_internships_keys(self):
        self.fake.session.update({"internships_query": "x", "internships_category": "Training programme",
                                  "internships_region": "India", "internships_format": "Varies", "internships_pay": "Fee-based",
                                  "internships_status": "Applications Closed", "internships_verification": "Verified",
                                  "page": "internships", "guide_history": ["keep"]})
        self.page._reset()
        s = self.fake.session
        self.assertEqual(s["internships_query"], "")
        for k in ("category", "region", "format", "pay", "status", "verification"):
            self.assertEqual(s[f"internships_{k}"], ALL)
        self.assertEqual((s["page"], s["guide_history"]), ("internships", ["keep"]))

    def test_dollar_signs_and_html_are_escaped(self):
        hostile = dataclasses.replace(_e("simplify"), name="<script>alert(1)</script>", description="<img src=x onerror=1> & US$5",
                                      notes=("US$5 and US$6",), official_url="https://simplify.jobs/internships",
                                      source_url='https://simplify.jobs/"onmouseover="x')
        with mock.patch.object(self.page, "ENTRIES", (hostile,)):
            self.page.render()
        html = self.html()
        for raw in ("<script>", "<img"):
            self.assertNotIn(raw, html)
        self.assertNotIn('"onmouseover="', html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("US&#36;5", html)
        self.assertIn("US\\$5 and US\\$6", self.md())
        self.page.render()
        for text in (self.md(), self.html()):
            self.assertIsNone(re.search(r"(?<![\\&#])\$", text.replace("&#36;", "")))

    def test_rendering_writes_no_state_and_has_no_network_or_hard_coded_data(self):
        before = dict(self.fake.session)
        self.page.render()
        self.assertEqual(dict(self.fake.session), before)
        src = _read("views/internships.py")
        for banned in ("import requests", "import urllib", "import subprocess", "import os", "from backend", "from config",
                       "Entry(", "https://", "http://"):
            self.assertNotIn(banned, src)


class IntegrationTests(unittest.TestCase):
    def test_registry_entry_order_and_single_learn_group(self):
        m = reg.get_module("internships")
        self.assertEqual((m.key, m.title, m.icon, m.group, m.status), ("internships", "Internships", "💼", "Learn", "implemented"))
        self.assertEqual(len(reg.implemented_keys()), 12)
        groups = nav_state.nav_groups()
        names = [g for g, _ in groups]
        self.assertEqual(names.count("Learn"), 1)
        self.assertEqual(names, ["Platform", "Analysis", "QR Tools", "Protect", "Learn", "System"])
        self.assertEqual([x.key for x in dict(groups)["Learn"]], ["learning_center", "courses", "roadmap", "internships"])
        self.assertEqual([x.title for x in dict(groups)["Learn"]], ["Security Learning Center", "Courses", "Roadmap", "Internships"])
        self.assertEqual(nav_state.NAV_GROUP_ORDER, ("Platform", "Analysis", "QR Tools", "Protect", "Learn", "System"))

    def test_router_wiring_and_sync_assertion_are_intact(self):
        src = _read("streamlit_app.py")
        for entry in ('"internships": internships.render,', '"roadmap": roadmap.render,', '"courses": courses.render,',
                      '"cyber_hygiene": cyber_hygiene.render,', '"learning_center": learning_center.render,'):
            self.assertIn(entry, src)
        self.assertIn("assert set(PAGES) == set(reg.implemented_keys())", src)

    def test_navigate_opens_internships_and_closes_the_drawer(self):
        state = {nav_state.SIDEBAR_KEY: True, "page": "dashboard", "guide_history": ["keep"]}
        self.assertEqual(nav_state.navigate(state, "internships"), "internships")
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

    def test_internships_opens_through_the_shield_highlights_and_closes_the_drawer(self):
        self.fake.session["guide_history"] = [{"role": "user", "content": "keep"}]
        self.toggle()
        self.assertIn("cs_navitem_internships", self.fake.button_keys)
        self.assertIn("💼", self.fake.button_labels["cs_navitem_internships"])
        self.fake.press("cs_navitem_internships")
        self.assertEqual(self.fake.session["page"], "internships")
        self.assertFalse(self.fake.session[nav_state.SIDEBAR_KEY])
        self.fake.run_app()
        self.assertFalse(self.fake.st.error.called)
        self.fake.st.title.assert_called_with("Internships")
        self.assertEqual(self.fake.st.link_button.call_count, 10)
        self.toggle()
        active = [k for k in self.fake.button_keys if k and k.startswith("cs_navitem_active_")]
        self.assertEqual(active, ["cs_navitem_active_internships"])
        self.assertEqual(self.fake.session["guide_history"][0]["content"], "keep")
        keys = [k for k in self.fake.button_keys if k]
        self.assertEqual(len(keys), len(set(keys)), "duplicate widget keys")

    def test_quick_links_open_the_real_roadmap_and_courses_pages(self):
        for key, page, title in (("internships_top_roadmap", "roadmap", "Roadmap"), ("internships_top_courses", "courses", "Courses")):
            self.fake.session["page"] = "internships"
            self.fake.run_app()
            self.assertIn(key, self.fake.button_keys)
            self.fake.press(key)
            self.fake.run_app()
            self.assertEqual(self.fake.session["page"], page)
            self.assertFalse(self.fake.st.error.called, page)
            self.fake.st.title.assert_called_with(title)

    def test_existing_learn_and_protect_pages_still_open_from_the_drawer(self):
        for key in ("learning_center", "courses", "roadmap", "cyber_hygiene"):
            self.toggle()
            self.assertIn(f"cs_navitem_{key}", self.fake.button_keys)
            self.fake.press(f"cs_navitem_{key}")
            self.assertEqual(self.fake.session["page"], key)
            self.fake.run_app()
            self.assertFalse(self.fake.st.error.called, key)

    def test_dashboard_lists_internships_automatically(self):
        # dashboard.py is unchanged: it builds its tool cards from the registry.
        self.assertIn("Open Internships", self.fake.button_labels.values())
        self.assertIn("dash_open_internships", self.fake.button_keys)

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
        return [s for s in load_sections() if s.page == "internships"]

    def test_topics_exist_with_page_key_and_fit_the_engine_limit(self):
        secs = self.sections()
        self.assertEqual(len(secs), 2)
        body = " ".join(s.body for s in secs)
        for needle in ("page key internships", "Learn group", "Open Internships", "Reset filters", "Partially Verified",
                       "Applications Open", "Never pay an unknown recruiter", "AICTE National Internship Portal",
                       "CISA Cyber and IT Internships", "U.S. citizenship is required", "GPCSSI",
                       "Next application cycle not yet officially announced", "not a government portal",
                       "Simplify", "Handshake", "Indeed", "Glassdoor", "LinkedIn", "Awesome Cybersecurity Internships",
                       "API Intern Group", "Paid Programme"):
            self.assertIn(needle, body, needle)
        for s in secs:
            self.assertLessEqual(len(s.body), 1800, "engine truncates sections at 1800 characters")

    def test_knowledge_matches_the_implementation(self):
        body = " ".join(s.body for s in self.sections()).lower()
        for banned in ("cybersecurityjobs", "theinternsgroup", "isc2", "guaranteed placement", "free certificate"):
            self.assertNotIn(banned, body)
        self.assertNotIn("is open now", body)

    def test_question_retrieval(self):
        for q in ("Where can I find cybersecurity internships?", "Is the Gurugram police cyber security summer internship open?",
                  "Can Indian students apply for CISA internships?", "Is API Intern Group a free internship?"):
            top = [s.page for s in retrieve(q, k=3)]
            self.assertIn("internships", top, q)

    def test_documentation_counts_and_navigation_are_consistent(self):
        km = _read("knowledge.md")
        self.assertIn("lists all twelve pages", km)
        self.assertIn("Learn (Security Learning Center, Courses, Roadmap, Internships)", km)
        self.assertNotIn("lists all eleven pages", km)
        nav = next(s for s in load_sections() if s.title == "Navigation sidebar and shield button")
        self.assertIn("Internships", nav.body)
        readme = _read("README.md")
        self.assertIn("all twelve pages", readme)
        self.assertNotIn("all eleven pages", readme)
        self.assertIn("| Internships |", readme)
        self.assertIn("November 26, 2026", readme)
        arch = _read("docs/architecture.md")
        self.assertIn("## Internships", arch)
        self.assertIn("Security Learning Center, Courses, Roadmap, Internships, Settings & API Configuration", arch)
        self.assertIn("Platform, Analysis, QR Tools, Protect, Learn, System", arch)


if __name__ == "__main__":
    unittest.main()
