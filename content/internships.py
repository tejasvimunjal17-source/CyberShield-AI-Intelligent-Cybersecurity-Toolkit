"""Internship directory data and local search/filter logic. No Streamlit import and no network access.

Built from the Phase 4 research (PHASE4_PROGRESS.md, verified 2026-11-26). Rules for editing this file:

* Add an entry only after reading the organisation's own page. Never guess a URL, date, fee, stipend,
  eligibility rule, certificate or application link. Use "Not stated" or "Unverified" instead.
* `official_url` is the button target. For GPCSSI no government page was found, so it is an ANNOUNCEMENT source
  (`official_kind == "announcement"`) and the card says so.
* `application_url` stays None unless an official source confirms an ACTIVE application window; then
  `application_status` must be "Applications Open". Old registration forms must never be linked.
* Distinctions the page must keep: a discovery platform is not an internship provider; a training programme is
  not an employment internship; a completion certificate is not a professional certification; free
  participation is not a paid stipend; a past application window or a past edition does not mean a current or
  next one; a fee-based placement service is not a free internship.
"""

from __future__ import annotations

from dataclasses import dataclass

LAST_VERIFIED = "2026-11-26"
ALL = "All"

# Status labels (see the specification).
VERIFIED, PARTIAL, UNVERIFIED = "Verified", "Partially Verified", "Unverified"
OPEN, CLOSED, UNCONFIRMED = "Applications Open", "Applications Closed", "Availability Unconfirmed"
PAID_PROGRAMME = "Paid Programme"

VERIFICATIONS = (VERIFIED, PARTIAL, UNVERIFIED)
APP_STATUSES = (OPEN, CLOSED, UNCONFIRMED)
CATEGORIES = ("Government / national portal", "Government internship programme", "Training programme",
              "Discovery platform", "Community-curated list", "Paid placement service")
REGIONS = ("India", "United States", "International / multiple", "Not stated")
FORMATS = ("In-person", "Remote", "Hybrid", "Varies", "Not stated")
PAY = ("Paid", "Unpaid", "Varies", "Fee-based", "Not stated")

# Official hosts only (https). tests/test_internships.py also checks every URL against an explicit list.
OFFICIAL_HOSTS = frozenset({
    "internship.aicte-india.org", "www.cisa.gov", "x.com", "simplify.jobs", "github.com", "joinhandshake.com",
    "www.indeed.com", "www.glassdoor.com", "www.linkedin.com", "theinterngroup.com",
})
SOURCE_HOSTS = OFFICIAL_HOSTS | frozenset({"aicte.gov.in", "niccs.cisa.gov", "theprint.in"})

NEXT_CYCLE_NOTE = "Next application cycle not yet officially announced. Check official announcements for updates."
SAFETY_WARNING = ("Never pay an unknown recruiter for a guaranteed internship or job. Verify the organisation, "
                  "official domain and application process before sharing personal documents or sensitive information.")

INTRO = ("A cybersecurity internship is a short period of supervised work or training that lets you practise skills "
         "and learn how security teams operate. This directory lists places to look, with honest labels about what was "
         "confirmed. It is not a list of open positions, and nothing here promises a placement, a job or a certificate.")

DISTINCTIONS = (
    "**Discovery platform is not an internship provider.** Platforms such as LinkedIn or Indeed show listings posted by employers.",
    "**Training programme is not an employment internship.** Some programmes teach skills and do not employ you.",
    "**Completion certificate is not a professional certification.** A certificate of participation is not an industry exam.",
    "**Free participation is not a stipend.** A programme can be free and still pay nothing.",
    "**A past window is not an open window, and a past edition is not the next edition.** Always check the official announcement.",
    "**Fee-based placement services are different from free internships.** They charge programme fees.",
)


@dataclass(frozen=True)
class Entry:
    id: str
    name: str
    organizer: str
    section: str                 # "government" | "programme" | "discovery"
    category: str                # one of CATEGORIES
    description: str
    eligibility: str
    location: str
    region: str                  # one of REGIONS
    work_format: str             # one of FORMATS
    pay_status: str              # one of PAY
    cost_note: str               # fee / cost to the user, as far as verified
    duration: str
    certificate: str
    application_status: str      # one of APP_STATUSES
    application_url: str | None  # only for Applications Open + official active URL; otherwise None
    official_url: str
    official_kind: str           # "official" | "announcement"
    button_label: str
    source_url: str
    last_verified: str
    verification: str            # one of VERIFICATIONS
    paid_programme: bool = False
    status_note: str = ""        # shown on the card, outside the expander
    notes: tuple[str, ...] = ()  # confirmed context and what was NOT verified
    search_terms: tuple[str, ...] = ()
    extra_sources: tuple[str, ...] = ()


SECTIONS = (
    ("government", "Government and National Internship Portals",
     "Official or government-linked routes. Check each eligibility rule: some are limited by country or citizenship."),
    ("programme", "Cybersecurity-Specific Programmes",
     "Programmes focused on cybersecurity. Historical details are kept separate from current application information."),
    ("discovery", "Internship Discovery Websites",
     "These help you find listings posted by others. They are not internship providers."),
)

ENTRIES: tuple[Entry, ...] = (
    # ---------------------------------------------------------------- Government and national
    Entry(
        "aicte-national-internship-portal", "AICTE National Internship Portal", "AICTE (All India Council for Technical Education)",
        "government", "Government / national portal",
        "A national internship discovery portal run by AICTE, a statutory body under India's Ministry of Education. "
        "Organisations post internships and students browse them. AICTE does not itself provide every listed internship, "
        "and not every listing is about cybersecurity.",
        "Aimed at students. Requirements are set by each listing and were not verified from AICTE's own pages.",
        "India-based portal; individual listings vary", "India", "Varies", "Varies",
        "Reported by universities and blogs as free for students; not confirmed on AICTE's own pages.",
        "Varies by listing", "Unverified", UNCONFIRMED, None,
        "https://internship.aicte-india.org", "official", "Visit Official Portal",
        "https://aicte.gov.in/sites/default/files/AICTE%20Advertisement%20for%20intern.pdf", LAST_VERIFIED, PARTIAL,
        status_note="No cybersecurity listing was confirmed as open during this research. Check the portal for current listings.",
        notes=("Confirmed: an AICTE document on aicte.gov.in names this portal and its address.",
               "Reported by third parties, not confirmed by AICTE: both paid and unpaid listings, a mix of remote, hybrid and "
               "in-person formats, and completion certificates.",
               "Current availability is unconfirmed unless the portal's current listings show otherwise."),
        search_terms=("cyber", "security", "information security")),
    Entry(
        "cisa-cyber-it-internships", "CISA Cyber and IT Internships", "Cybersecurity and Infrastructure Security Agency (CISA), United States",
        "government", "Government internship programme",
        "CISA is a US federal agency. It offers student internships, including Cyber and IT interns. NICCS (a CISA site) "
        "describes a paid 10 to 12 week programme for high school, undergraduate and graduate students.",
        "U.S. citizenship is required: CISA says it can only employ U.S. citizens for its internships. Minimum age 16. You "
        "must be an enrolled student when you apply and when the internship starts, and stay at least part-time. CISA's "
        "volunteer student internships also ask for a transcript and a 2.5 minimum GPA. This programme is not open to "
        "international students, including students from India.",
        "United States (federal agency)", "United States", "Not stated", "Varies",
        "No application fee was stated. The Cyber and IT Interns programme is described as paid; CISA's separate volunteer student internships are unpaid.",
        "10 to 12 weeks (NICCS description of the Cyber and IT Interns programme)", "Not stated", UNCONFIRMED, None,
        "https://www.cisa.gov/pathways-interns", "official", "Visit Official Programme Page",
        "https://niccs.cisa.gov/resources/internships-apprenticeships", LAST_VERIFIED, VERIFIED,
        status_note="Applications run through individual USAJOBS vacancies. No current application window was confirmed, so no application link is shown.",
        notes=("General programme information is not the same as eligibility for a particular vacancy. Each vacancy has its own rules, so read it fully.",
               "Several CISA student vacancies found during research were already closed.",
               "Work format and any certificate were not stated on the pages reviewed."),
        extra_sources=("https://www.cisa.gov/pathways-interns",)),
    # ------------------------------------------------------------ Cybersecurity-specific programmes
    Entry(
        "gpcssi", "Gurugram Police Cyber Security Summer Internship (GPCSSI)", "Gurugram Police (Gurugram Cyber Police), India",
        "programme", "Training programme",
        "A yearly cybersecurity training and awareness programme for students and professionals, organised with Gurugram "
        "Police. It is a training programme, not an employment internship.",
        "Two tracks were announced for the 13th edition: Cyber Warriors (undergraduate, graduate and postgraduate or master's "
        "students, and working professionals) and Cyber Ambassadors (school students in Grades 9 to 12).",
        "Gurugram, Haryana, India", "India", "Varies", "Not stated",
        "Third-party sites report no fee and no stipend. This is not confirmed by an official source.",
        "About one month in the 12th edition (2 June to 2 July 2025, per PTI)",
        "Unverified (third-party sites report a completion certificate)", CLOSED, None,
        "https://x.com/tandonrakshit/status/2050208882602201333", "announcement", "View Announcement Source",
        "https://theprint.in/india/gurugram-gpcssi-2025-launched-to-promote-cybersecurity-awareness/2645253", LAST_VERIFIED, PARTIAL,
        status_note=NEXT_CYCLE_NOTE + " The 13th edition's Cyber Warriors forms were announced as open until 6 May 2026.",
        notes=("The button opens an announcement by the programme's mentor, Dr. Rakshit Tandon, on X. It is an announcement source, not an official government portal. No official Gurugram Police page or registration address was found, and old registration forms are deliberately not linked.",
               "Confirmed through news reports quoting police: Gurugram Police organises the programme. The 12th edition (2025) selected about 1,100 interns and included hands-on training in cybersecurity, cyber hygiene, investigations and tool development, with guest lectures.",
               "Format varies by edition: reports describe the 2024 edition as partly virtual. Do not assume it is in person.",
               "Fee, stipend, venue, certificate and the wider curriculum for the 13th edition appear only on third-party sites and are not shown as facts."),
        extra_sources=("https://x.com/tandonrakshit/status/2050208882602201333",)),
    # ------------------------------------------------------------------ Discovery websites
    Entry(
        "simplify", "Simplify", "Simplify Jobs, Inc.", "discovery", "Discovery platform",
        "A job-search platform that indexes openings from company career pages. It has an Internships section, a "
        "job tracker, resume tools and browser autofill. It helps you find and track applications; it is not an employer.",
        "An account is used for matches and tracking. No eligibility rules were stated on the page reviewed.",
        "Not stated", "Not stated", "Varies", "Varies",
        "Per Simplify: job search, matches, Copilot autofill and the tracker are free; Simplify+ and Autopilot credits are paid.",
        "Varies by listing", "Not applicable (discovery platform)", UNCONFIRMED, None,
        "https://simplify.jobs/internships", "official", "Visit Official Platform",
        "https://simplify.jobs/", LAST_VERIFIED, PARTIAL,
        notes=("Confirmed on Simplify's site: the free and paid features above, and an Internships section.",
               "Not verified: a cybersecurity category, location and remote filters, and country coverage."),
        search_terms=("Cybersecurity Intern", "Security Analyst Intern")),
    Entry(
        "awesome-cybersecurity-internships", "Awesome Cybersecurity Internships (GitHub)", "Community-maintained by the GitHub user paralax",
        "discovery", "Community-curated list",
        "A community-maintained list of cybersecurity internships on GitHub. Entries link to employer pages. It is not an "
        "employer or a government portal, and its own README says it is informational and not an endorsement.",
        "Set by each linked employer.", "Mostly United States at the time of review", "United States", "Not stated", "Varies",
        "Free to read on GitHub. Not confirmed whether the linked internships are paid.",
        "Varies by listing", "Not applicable (list)", UNCONFIRMED, None,
        "https://github.com/paralax/awesome-cybersecurity-internships", "official", "Open Community Resource",
        "https://github.com/paralax/awesome-cybersecurity-internships", LAST_VERIFIED, PARTIAL,
        notes=("Confirmed on the repository page: owned by a personal account, about 588 stars and 73 forks, contributions by pull request, yearly README files including one for 2026, and a Summer 2027 role listed. The date of the last update was not shown.",
               "Few specific cybersecurity listings were visible at the time of review. Always confirm a listing on the employer's own site."),
        search_terms=()),
    Entry(
        "handshake", "Handshake", "Handshake", "discovery", "Discovery platform",
        "A career network that connects students and employers, with full-time, remote and internship categories and "
        "partnerships with university career centres. It is a discovery platform, not an internship provider.",
        "An account is needed. What you can see may depend on your school and country, which were not verified, so do not "
        "assume every student can see every listing.",
        "Not stated", "Not stated", "Varies", "Varies",
        "Cost to students was not stated on the page reviewed.",
        "Varies by listing", "Not applicable (discovery platform)", UNCONFIRMED, None,
        "https://joinhandshake.com/", "official", "Visit Official Platform",
        "https://joinhandshake.com/", LAST_VERIFIED, PARTIAL,
        notes=("Handshake also runs Handshake AI, which offers paid AI project work. That is separate from internships.",
               "Not verified: geographic availability, student access rules and the number of cybersecurity listings."),
        search_terms=("Cybersecurity Intern",)),
    Entry(
        "indeed", "Indeed", "Indeed, Inc.", "discovery", "Discovery platform",
        "A job search engine with keyword and location search, company reviews and salary pages. Employers post the "
        "listings, so it is a discovery platform, not an internship provider.",
        "Each listing sets its own requirements. Account rules were not verified.",
        "Not stated (the US site was reviewed)", "Not stated", "Varies", "Varies",
        "Cost to job seekers was not stated on the page reviewed.",
        "Varies by listing", "Not applicable (discovery platform)", UNCONFIRMED, None,
        "https://www.indeed.com/", "official", "Visit Official Platform",
        "https://www.indeed.com/", LAST_VERIFIED, PARTIAL,
        notes=("Search tip: try the terms below, then add a location. Treat results as leads and confirm each one on the employer's site.",
               "Not verified: country coverage and how many results are cybersecurity internships."),
        search_terms=("Cybersecurity Intern", "SOC Analyst Intern", "Information Security Intern", "GRC Intern", "Security Analyst Intern")),
    Entry(
        "glassdoor", "Glassdoor", "Glassdoor (a trademark of Indeed, Inc.)", "discovery", "Discovery platform",
        "A company-research platform with employer ratings and reviews, plus job listings. Use it to learn about a company's "
        "culture and interview process before you apply. It is a discovery and research site, not an internship provider.",
        "Each listing sets its own requirements. Account rules were not verified.",
        "Not stated", "Not stated", "Varies", "Varies",
        "Glassdoor describes its Recruiter (Beta) matching tool as free. Other costs were not stated.",
        "Varies by listing", "Not applicable (discovery platform)", UNCONFIRMED, None,
        "https://www.glassdoor.com/", "official", "Visit Official Platform",
        "https://www.glassdoor.com/", LAST_VERIFIED, PARTIAL,
        notes=("Reviews are opinions from individuals. Compare several sources.",
               "Not verified: country coverage and how many results are cybersecurity internships."),
        search_terms=("Cybersecurity Intern", "SOC Analyst Intern")),
    Entry(
        "linkedin", "LinkedIn", "LinkedIn", "discovery", "Discovery platform",
        "A professional networking site with job search. LinkedIn's help pages describe filters for experience level, "
        "employment type (including internship), company and Easy Apply, and location types such as remote, hybrid and "
        "on-site. It is a discovery platform, not an internship provider.",
        "Each listing sets its own requirements. Account rules and country coverage were not verified.",
        "Not stated", "Not stated", "Varies", "Varies",
        "Cost to users was not verified.",
        "Varies by listing", "Not applicable (discovery platform)", UNCONFIRMED, None,
        "https://www.linkedin.com/", "official", "Visit Official Platform",
        "https://www.linkedin.com/help/linkedin/answer/154", LAST_VERIFIED, PARTIAL,
        notes=("How to search: enter a term such as Cybersecurity Intern, then use the filters for employment type or experience level set to Internship, plus a location type if you want remote or hybrid.",
               "LinkedIn's home page could not be reviewed automatically, so the filter details come from its help page."),
        search_terms=("Cybersecurity Intern", "SOC Analyst Intern", "Information Security Intern"),
        extra_sources=("https://www.linkedin.com/help/linkedin/answer/154",)),
    Entry(
        "api-intern-group", "API Intern Group (The Intern Group)", "The Intern Group (TIG)", "discovery", "Paid placement service",
        "A fee-based service (the organisation shows the name API Intern Group and also calls itself The Intern Group) that places "
        "students and graduates into internships abroad or remotely, including a cybersecurity career field. You pay programme fees. "
        "This is not a free internship.",
        "Per the organisation: applicants from any country are considered, subject to the visa rules of the destination; minimum age 18 "
        "for in-person and 16 for remote programmes; admission includes an interview. Not specifically verified for Indian applicants.",
        "International destinations (for example London, Madrid, Dublin, Melbourne)", "International / multiple", "Varies", "Fee-based",
        "Programme fees apply and vary by destination and duration; they include housing and extras such as coaching. Applying has a small application fee (refunded if unsuccessful, deducted if accepted) and an enrolment deposit. Visa, flights, insurance and food are extra. Its FAQ tells applicants to expect an unpaid internship.",
        "Varies by programme (in-person usually 35 to 40 hours a week; remote 10 to 40 hours a week)", "Not stated", UNCONFIRMED, None,
        "https://theinterngroup.com/career-fields/cyber-security-internships", "official", "View Programme Page (Paid Service)",
        "https://theinterngroup.com/resources/faq", LAST_VERIFIED, PARTIAL, paid_programme=True,
        status_note="Fee-based placement service. Compare it with free options and check the fees before you share any documents.",
        notes=("Identity: the organisation's own FAQ page shows the name API Intern Group and the Intern Group, and the address theinterngroup.com. The different address theinternsgroup.com could not be verified and is not used.",
               "The organisation states its own placement guarantee with a refund if no internship offer is made in your chosen field, subject to its terms. This is the organisation's claim, not independently verified, so read the terms before paying.",
               "Never pay an unknown recruiter for a guaranteed internship. Check the organisation, domain and fees yourself."),
        search_terms=()),
)

ENTRY_IDS = tuple(e.id for e in ENTRIES)

TIPS = (
    ("Build a cybersecurity resume",
     ("Keep it to one page and put skills, projects and coursework first.",
      "Describe what you did and learned, not just tool names. Be honest about your level.",
      "Ask a teacher or mentor to read it before you send it.")),
    ("Create a small practical portfolio",
     ("Write short, clear write-ups of lab exercises, such as how you secured a home router or analysed a sample log.",
      "Share only your own work. Remove personal data, passwords and anything from a real organisation.",
      "Publish write-ups where a reviewer can read them easily, and keep them accurate.")),
    ("Learn networking and operating system basics",
     ("Understand IP addresses, DNS, ports, users, permissions and the command line. The Roadmap page shows an order for these.",
      "Strong basics help you more than a long list of tools.")),
    ("Practise cybersecurity fundamentals legally",
     ("Practise only on devices and networks you own, or where you have written permission.",
      "Use your own lab of virtual machines. Never test other people's websites or accounts.",
      "Learn about responsible disclosure: report flaws to the owner instead of exploiting them.")),
    ("Prepare for interviews",
     ("Be ready to explain basics in simple words, such as phishing, passwords and multi-factor authentication.",
      "Prepare to talk through one project in two minutes: the problem, what you did, and what you learned.",
      "Research the organisation first. Glassdoor-style reviews can help, but treat them as opinions.")),
    ("Write professional application emails",
     ("Use a clear subject line, address a named person if you can, and keep it short.",
      "Say who you are, which role you want, and one reason you are a good fit. Attach only what was requested.",
      "Use a professional email address and proofread before sending.")),
    ("Check that an internship is legitimate",
     ("Find the organisation's official website yourself and match the domain and contact details.",
      "Be careful if you are asked for money, urgency, or personal documents before any interview.",
      "Confirm the role through an official channel before you share an ID, bank details or passwords.")),
)

SAFETY_CHECKS = (
    "Open the organisation's official website yourself, rather than a link from a message, and check the domain carefully.",
    "A real internship does not need a payment to be considered. Fee-based placement services are a different thing, so compare their fees openly.",
    "Do not share ID numbers, bank details or passwords during early recruitment steps.",
    "Be suspicious of pressure, guaranteed outcomes, free email addresses for company recruiters and requests to move to private chat apps.",
    "Use the URL Security Scanner in this app to check an unfamiliar link without visiting it.",
)


def entry_by_id(entry_id: str) -> Entry | None:
    return next((e for e in ENTRIES if e.id == entry_id), None)


def filter_entries(entries=ENTRIES, query: str = "", category: str = ALL, region: str = ALL, work_format: str = ALL,
                   pay: str = ALL, app_status: str = ALL, verification: str = ALL) -> list[Entry]:
    """Local search and filters. `query` matches every typed word against the entry name."""
    words = [w for w in (query or "").lower().split() if w]
    out = []
    for e in entries:
        if words and not all(w in e.name.lower() for w in words):
            continue
        if category != ALL and e.category != category:
            continue
        if region != ALL and e.region != region:
            continue
        if work_format != ALL and e.work_format != work_format:
            continue
        if pay != ALL and e.pay_status != pay:
            continue
        if app_status != ALL and e.application_status != app_status:
            continue
        if verification != ALL and e.verification != verification:
            continue
        out.append(e)
    return out


def entries_by_section(entries) -> list[tuple[str, str, str, list[Entry]]]:
    """(key, title, note, entries) for each section in order, omitting empty sections."""
    grouped = [(k, t, n, [e for e in entries if e.section == k]) for k, t, n in SECTIONS]
    return [g for g in grouped if g[3]]
