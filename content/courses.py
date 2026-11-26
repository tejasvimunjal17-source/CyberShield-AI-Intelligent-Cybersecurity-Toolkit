"""Static course directory data and local search/filter logic for the Courses page.

No Streamlit import and no network access. Every fact here comes from the Phase 2 research
(PHASE2_PROGRESS.md, research date 2026-11-26). Rules for editing this file:

* Add a course only after reading the provider's own page. Never guess a URL, duration,
  price, certificate or badge. Use "Unverified" or "Not stated" instead.
* `official_url` is where the learner enrolls. If no direct course URL is verified it is the
  provider's official catalogue page and the course is marked "Partially verified".
* `source_url` is the official page the facts were read from (may differ from `official_url`).
* A digital badge, a completion certificate and a paid professional certification exam are
  different things. `certificate_status` is the learner-facing credential for the course
  itself; paid exams go in `exam_note` and are never counted as free.
* Offers change. Providers can alter or withdraw courses, prices and credentials at any time.
"""

from __future__ import annotations

from dataclasses import dataclass

LAST_VERIFIED = "2026-11-26"

ALL = "All"

# Filter vocabularies (shown in the select boxes, in this order).
DIFFICULTIES = ("Beginner", "Intermediate", "Not stated")
COSTS = ("Free", "Paid", "Unverified")
CREDENTIALS = ("Digital badge", "Completion certificate (paid programme)", "None verified", "Unverified")

VERIFIED = "Verified"
PARTIAL = "Partially verified"
VERIFICATION_LEVELS = (VERIFIED, PARTIAL)

# Official provider hosts only. tests/test_courses.py enforces these lists.
OFFICIAL_URL_HOSTS = frozenset({
    "www.netacad.com", "skillsforall.com", "skillsbuild.org", "grow.google", "learn.microsoft.com",
    "training.fortinet.com", "paloaltonetworks.com", "cloud.google.com",
})
SOURCE_URL_HOSTS = OFFICIAL_URL_HOSTS | frozenset({
    "www.cisco.com", "www.fortinet.com", "www.paloaltonetworks.com",
})


@dataclass(frozen=True)
class Provider:
    key: str
    name: str
    icon: str            # emoji, so no remote logo is loaded
    website: str         # official provider website
    note: str            # limits and context shown above the provider's cards
    resource: tuple[str, str] | None = None   # (label, url): provider resource link, not a course


@dataclass(frozen=True)
class Course:
    id: str
    title: str
    provider: str        # Provider.name
    description: str
    difficulty: str      # one of DIFFICULTIES
    cost_status: str     # one of COSTS
    certificate_status: str   # one of CREDENTIALS
    duration: str
    eligibility: str
    official_url: str
    category: str        # subject area
    last_verified: str
    source_url: str      # official page the facts were read from
    verification: str    # VERIFIED or PARTIAL
    details: tuple[str, ...] = ()   # credential / exam / status notes shown in the expander


PROVIDERS: tuple[Provider, ...] = (
    Provider("cisco", "Cisco Networking Academy", "🌐", "https://www.netacad.com/",
             "Cisco's catalogue changes. The self-paced Cybersecurity Essentials course was refreshed as the Junior "
             "Cybersecurity Analyst Career Path, so those are shown as two separate entries. Instructor-led courses "
             "are offered through participating academies."),
    Provider("ibm", "IBM SkillsBuild", "🔷", "https://skillsbuild.org/",
             "Learners register on IBM SkillsBuild. IBM also lists some courses for registered institutions only; "
             "those are not shown here."),
    Provider("google", "Google", "🔎", "https://grow.google/",
             "Google's Cybersecurity Certificate is a paid programme, not a free course. Google Cloud's learning "
             "catalogue is linked as a resource only: no specific free security course was verified.",
             ("Google Cloud learning catalogue (resource, not a verified course)", "https://cloud.google.com/learn")),
    Provider("microsoft", "Microsoft Learn", "🪟", "https://learn.microsoft.com/",
             "These are learning paths on Microsoft Learn. The SC-900 certification exam is a separate paid "
             "professional exam; completing a learning path is not that certification."),
    Provider("fortinet", "Fortinet Training Institute", "🧱", "https://training.fortinet.com/",
             "Only the pathway is listed. Individual course names, durations, levels and exam terms were not "
             "verified, so none are shown."),
    Provider("paloalto", "Palo Alto Networks", "🔥", "https://www.paloaltonetworks.com/",
             "Limited listing. Palo Alto's page describes free fundamentals courses, but course names, durations "
             "and credentials were not verified. Its Cybersecurity Academy curriculum is for academic institutions."),
)

_CISCO_FAQ = "https://www.cisco.com/site/us/en/learn/training-certifications/certifications/support-technician/faq.html"

COURSES: tuple[Course, ...] = (
    # ------------------------------------------------------------------ Cisco
    Course(
        "cisco-intro-cybersecurity", "Introduction to Cybersecurity", "Cisco Networking Academy",
        "An introductory Cisco Networking Academy course on cybersecurity.",
        "Beginner", "Free", "Digital badge",
        "About 15 hours (from a Cisco-hosted copy of the course page; confirm on netacad.com)",
        "No prerequisites listed on that page copy; confirm when you enroll",
        "https://www.netacad.com/", "Cybersecurity fundamentals", LAST_VERIFIED,
        "https://www.netacad.com/", PARTIAL,
        ("Partially verified: level, cost, duration, prerequisites and badge come from a Cisco-hosted copy of the "
         "course page, not the public page. A direct public course URL was not verified, so the button opens "
         "Cisco's official catalogue; search it for the course.",)),
    Course(
        "cisco-networking-essentials", "Networking Essentials", "Cisco Networking Academy",
        "A Cisco Networking Academy networking course. Cisco describes it as instructor-led through participating "
        "academies. Cisco's separate, free self-paced Network Technician Career Path (about 70 hours) is listed "
        "on Skills for All.",
        "Not stated", "Unverified", "Unverified",
        "Unverified", "Unverified; offered through participating academies",
        "https://www.netacad.com/", "Networking", LAST_VERIFIED,
        _CISCO_FAQ, PARTIAL,
        ("Partially verified: only the course's existence and instructor-led delivery are supported by Cisco's page. "
         "Level, cost, duration and credential were not verified. No direct course URL was verified, so the "
         "button opens Cisco's official catalogue.",)),
    Course(
        "cisco-ethical-hacker", "Ethical Hacker", "Cisco Networking Academy",
        "A Cisco Networking Academy course on ethical hacking (offensive security).",
        "Not stated", "Free", "Digital badge",
        "Unverified", "Unverified",
        "https://www.netacad.com/courses/ethical-hacker?courseLang=en-US", "Ethical hacking", LAST_VERIFIED,
        "https://www.cisco.com/site/us/en/learn/training-certifications/certifications/ethical-hacker/program.html",
        VERIFIED,
        ("Credential: the course carries a Cisco digital badge. Cisco's separate certificate also requires "
         "completing a Capture the Flag challenge in Cisco U. The cost of that challenge was not verified.",
         "Level, duration and eligibility were not verified, so they are not shown.")),
    Course(
        "cisco-junior-cybersecurity-analyst", "Junior Cybersecurity Analyst Career Path", "Cisco Networking Academy",
        "Cisco's free self-paced cybersecurity pathway on Skills for All. It replaced the self-paced Cybersecurity "
        "Essentials course and prepares for Cisco's entry-level CCST Cybersecurity exam.",
        "Beginner", "Free", "Digital badge",
        "About 120 hours (Cisco)", "None stated on Cisco's page; offered in several languages",
        "https://skillsforall.com/career-path/cybersecurity", "Cybersecurity career pathway", LAST_VERIFIED,
        _CISCO_FAQ, VERIFIED,
        ("Credential: Cisco digital badge for the free training.",
         "Paid exam: the CCST Cybersecurity exam is a separate professional certification and costs US$125 "
         "(Cisco FAQ, April 2026). Free training does not include a free exam.",
         "Not the same as Cybersecurity Essentials: see the separate entry below.")),
    Course(
        "cisco-cybersecurity-essentials", "Cybersecurity Essentials", "Cisco Networking Academy",
        "Cisco's Cybersecurity Essentials course remains available as an instructor-led course through "
        "participating academies. It is different from the free self-paced Junior Cybersecurity Analyst Career Path.",
        "Not stated", "Unverified", "Unverified",
        "Unverified", "Unverified; offered through participating academies",
        "https://www.netacad.com/", "Cybersecurity fundamentals", LAST_VERIFIED,
        _CISCO_FAQ, PARTIAL,
        ("Partially verified: Cisco states the self-paced version was refreshed as the Junior Cybersecurity Analyst "
         "Career Path and that the instructor-led course continues through academies. Its cost, duration and "
         "credential were not verified. The button opens Cisco's official catalogue.",)),
    # -------------------------------------------------------------------- IBM
    Course(
        "ibm-cybersecurity-fundamentals", "Cybersecurity Fundamentals", "IBM SkillsBuild",
        "A cybersecurity fundamentals course in the IBM SkillsBuild course catalogue.",
        "Not stated", "Free", "Digital badge",
        "About 7.5 hours", "Registered IBM SkillsBuild learners",
        "https://skillsbuild.org/college-students/course-catalog/cybersecurity-fundamentals",
        "Cybersecurity fundamentals", LAST_VERIFIED,
        "https://skillsbuild.org/college-students/course-catalog/cybersecurity-fundamentals", VERIFIED,
        ("Credential: IBM digital badge (shared through Credly). A badge is not a professional certification.",
         "IBM SkillsBuild is described as free; availability can change, so confirm when you register.",
         "The catalogue page did not state a difficulty level.")),
    Course(
        "ibm-cybersecurity-fluency-pathway", "Cybersecurity Fluency Pathway", "IBM SkillsBuild",
        "An IBM SkillsBuild learning pathway on cybersecurity.",
        "Not stated", "Free", "Unverified",
        "About 54 hours", "Unverified",
        "https://skillsbuild.org/college-students/course-catalog/cybersecurity-fluency-pathway",
        "Cybersecurity pathway", LAST_VERIFIED,
        "https://skillsbuild.org/college-students/course-catalog/cybersecurity-fluency-pathway", VERIFIED,
        ("IBM SkillsBuild is described as free; availability can change, so confirm when you register.",
         "Credential, level and eligibility were not verified for this pathway, so none are claimed.")),
    # ----------------------------------------------------------------- Google
    Course(
        "google-cybersecurity-certificate", "Google Cybersecurity Certificate", "Google",
        "A paid Google Career Certificate programme taught on Coursera.",
        "Not stated", "Paid", "Completion certificate (paid programme)",
        "8 courses, about 181 hours (shown on a regional Google page; pace varies)",
        "No prior experience is stated as required",
        "https://grow.google/certificates/en_us/certificates/cybersecurity",
        "Cybersecurity career certificate", LAST_VERIFIED,
        "https://grow.google/certificates/en_us/certificates/cybersecurity", VERIFIED,
        ("Cost: a paid Coursera subscription (about US$49 per month in the US and Canada after a 7-day trial; price "
         "varies by country). Financial aid or scholarships may be available. This is not a free course.",
         "Credential: a certificate for completing the paid programme. It is not a professional certification exam.")),
    # -------------------------------------------------------------- Microsoft
    Course(
        "ms-security-compliance-identity-concepts", "Security, compliance and identity concepts", "Microsoft Learn",
        "Microsoft Learn learning path: Microsoft Security, Compliance, and Identity Fundamentals, describing "
        "the concepts of security, compliance and identity.",
        "Not stated", "Unverified", "None verified",
        "Unverified", "Unverified",
        "https://learn.microsoft.com/en-us/training/paths/describe-concepts-of-security-compliance-identity/",
        "Security fundamentals", LAST_VERIFIED,
        "https://learn.microsoft.com/en-us/training/paths/describe-concepts-of-security-compliance-identity/",
        VERIFIED,
        ("Cost, duration, level and completion credential were not stated on the page reviewed, so none are claimed.",
         "Exam: the SC-900 certification exam is separate and paid. Finishing this path is not that certification.")),
    Course(
        "ms-security-solutions-capabilities", "Capabilities of Microsoft security solutions", "Microsoft Learn",
        "Microsoft Learn learning path: Microsoft Security, Compliance, and Identity Fundamentals, describing "
        "the capabilities of Microsoft security solutions.",
        "Not stated", "Unverified", "None verified",
        "Unverified", "Unverified",
        "https://learn.microsoft.com/en-us/training/paths/describe-capabilities-of-microsoft-security-solutions",
        "Microsoft security", LAST_VERIFIED,
        "https://learn.microsoft.com/en-us/training/paths/describe-capabilities-of-microsoft-security-solutions",
        VERIFIED,
        ("Cost, duration, level and completion credential were not stated on the page reviewed, so none are claimed.",
         "Exam: the SC-900 certification exam is separate and paid. Finishing this path is not that certification.")),
    Course(
        "ms-entra-identity-access", "Capabilities of Microsoft Entra (identity and access)", "Microsoft Learn",
        "Microsoft Learn learning path: Microsoft Security, Compliance, and Identity Fundamentals, describing "
        "the capabilities of Microsoft Entra for identity and access management.",
        "Beginner", "Unverified", "None verified",
        "Unverified", "Unverified",
        "https://learn.microsoft.com/en-us/training/paths/describe-capabilities-of-microsoft-identity-access",
        "Identity and access management", LAST_VERIFIED,
        "https://learn.microsoft.com/en-us/training/paths/describe-capabilities-of-microsoft-identity-access",
        VERIFIED,
        ("Microsoft labels this path Beginner. Cost, duration and completion credential were not stated on the page "
         "reviewed, so none are claimed.",
         "Exam: the SC-900 certification exam is separate and paid. Finishing this path is not that certification.")),
    # --------------------------------------------------------------- Fortinet
    Course(
        "fortinet-fcf-cybersecurity", "Fortinet Certified Fundamentals (FCF) Cybersecurity pathway", "Fortinet Training Institute",
        "Fortinet's pathway of introductory cybersecurity training toward its FCF Cybersecurity credential.",
        "Not stated", "Free", "Digital badge",
        "Unverified", "Unverified",
        "https://training.fortinet.com/course/index.php/Certification:FCF_Cybersecurity",
        "Cybersecurity fundamentals", LAST_VERIFIED,
        "https://www.fortinet.com/training/cybersecurity-professionals.html", PARTIAL,
        ("Partially verified: Fortinet's pages describe free self-paced training with digital badges. Individual "
         "course names and details, whether the offer is current, and the terms and cost of the FCF certification "
         "exam were not verified.",)),
    # ---------------------------------------------------------- Palo Alto Networks
    Course(
        "paloalto-free-fundamentals", "Free cybersecurity fundamentals education", "Palo Alto Networks",
        "Palo Alto Networks says its fundamentals of cybersecurity courses are free and need only a free Beacon "
        "learning account.",
        "Not stated", "Free", "Unverified",
        "Unverified", "A free Beacon account (an email address), per Palo Alto Networks",
        "https://paloaltonetworks.com/cyberpedia/free-cybersecurity-education-courses",
        "Cybersecurity fundamentals", LAST_VERIFIED,
        "https://paloaltonetworks.com/cyberpedia/free-cybersecurity-education-courses", PARTIAL,
        ("Partially verified: course names, durations and any certificate were not verified against Palo Alto "
         "Networks' own pages, so none are listed or claimed.",
         "Palo Alto Networks' Cybersecurity Academy curriculum is for academic institutions, not open enrollment.")),
)

PROVIDER_NAMES = tuple(p.name for p in PROVIDERS)


def provider_for(name: str) -> Provider:
    return next(p for p in PROVIDERS if p.name == name)


def course_by_id(course_id: str) -> Course | None:
    return next((c for c in COURSES if c.id == course_id), None)


def filter_courses(courses=COURSES, query: str = "", provider: str = ALL, difficulty: str = ALL,
                   cost: str = ALL, credential: str = ALL) -> list[Course]:
    """Local search and filters. `query` matches every word against the course title."""
    words = [w for w in (query or "").lower().split() if w]
    result = []
    for c in courses:
        if words and not all(w in c.title.lower() for w in words):
            continue
        if provider != ALL and c.provider != provider:
            continue
        if difficulty != ALL and c.difficulty != difficulty:
            continue
        if cost != ALL and c.cost_status != cost:
            continue
        if credential != ALL and c.certificate_status != credential:
            continue
        result.append(c)
    return result


def group_by_provider(courses) -> list[tuple[Provider, list[Course]]]:
    """Provider sections in catalogue order, omitting providers with no matching course."""
    grouped = [(p, [c for c in courses if c.provider == p.name]) for p in PROVIDERS]
    return [(p, cs) for p, cs in grouped if cs]
