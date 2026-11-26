"""Beginner cybersecurity learning roadmap: static content, no Streamlit and no URLs.

The roadmap never stores a link. It refers to things that already exist in the app:
  * `course_ids`    -> ids in content/courses.py (the page shows each course's own verified link, cost and
                       verification label; it never restates them);
  * `lessons`       -> exact titles in content/learning_topics.TOPICS;
  * `pages`         -> keys in app_registry (opened with components.sidebar.go_to).
tests/test_roadmap.py checks every reference, so a renamed course, lesson or page fails the suite.

Durations are "Self-paced": nothing in the research supports a reliable time estimate.
Courses are optional suggestions. Completing one does not guarantee a job or a certification.
"""

from __future__ import annotations

from dataclasses import dataclass

DURATION = "Self-paced"

INTRO = ("This roadmap is a suggested order for learning cybersecurity if you are starting from zero or with little "
         "technical knowledge. Each stage builds on the one before it, but you can move back and forth, and you do not "
         "need to finish everything before you start the next stage.")

DISCLAIMER = ("The roadmap and the courses it mentions are recommendations, not requirements. Completing a course does "
              "not guarantee a job or a certification: a professional certification is a separate exam, usually paid. "
              "Only practise hands-on skills on devices and networks you own, or where you have written permission.")

NO_COURSE_NOTE = ("No verified course for this stage is listed on the Courses page. Use the suggested topics below to "
                  "find learning material you trust.")


@dataclass(frozen=True)
class Stage:
    key: str
    number: int
    title: str
    short: str                           # label in the progress strip
    icon: str
    summary: str
    objectives: tuple[str, ...]          # Learning objectives
    concepts: tuple[tuple[str, str], ...]  # Important concepts: (term, plain-English meaning)
    skills: tuple[str, ...]              # Skills to develop
    topics: tuple[str, ...]              # Recommended topics
    activities: tuple[str, ...]          # Practical activities or exercises
    outcome: str                         # Expected learning outcome
    next_key: str | None                 # Recommended next stage (None for the last)
    lessons: tuple[str, ...] = ()        # Security Learning Center lesson titles
    course_ids: tuple[str, ...] = ()     # content/courses.py ids (recommended, never mandatory)
    pages: tuple[str, ...] = ()          # related in-app pages (registry keys) shown as buttons
    duration: str = DURATION


STAGES: tuple[Stage, ...] = (
    Stage(
        "fundamentals", 1, "Cybersecurity Fundamentals", "Fundamentals", "🧭",
        "Learn what cybersecurity protects, and the everyday habits that keep people safe.",
        ("Explain in simple words what cybersecurity is and why it matters.",
         "Recognize common threats such as phishing and malware.",
         "Build safe habits: strong passwords, multi-factor authentication and software updates."),
        (("Confidentiality, integrity, availability", "Three goals of security: keep data private, keep it correct, and keep it reachable when needed."),
         ("Threat", "Something that could cause harm, such as a scam email."),
         ("Vulnerability", "A weakness a threat can use, such as an app that has not been updated."),
         ("Risk", "The chance that a threat uses a weakness, and how much harm that would cause."),
         ("Phishing", "A trick message that pretends to come from someone you trust."),
         ("Multi-factor authentication (MFA)", "Proving who you are in two or more ways, for example a password plus a code from an app.")),
        ("Spot a suspicious message", "Use a password manager and turn on MFA", "Keep devices and apps updated",
         "Describe a simple risk in plain words"),
        ("Types of cyber threats", "Passwords and MFA", "Phishing and social engineering (tricking people instead of machines)",
         "Privacy basics", "Safe use of public Wi-Fi"),
        ("Turn on MFA for your email account and one other important account.",
         "Follow the Cyber Hygiene guide for your own phone or computer.",
         "Write down five warning signs of phishing, then check a real suspicious message against them (without clicking any link).",
         "Explain confidentiality, integrity and availability to a friend using one example each."),
        "You can explain the core ideas in plain English, and your own accounts and devices are better protected.",
        "computer_os",
        lessons=("Using this toolkit responsibly", "Passwords and multi-factor authentication", "Recognizing phishing"),
        course_ids=("cisco-intro-cybersecurity", "ibm-cybersecurity-fundamentals", "ms-security-compliance-identity-concepts"),
        pages=("learning_center", "courses", "cyber_hygiene")),
    Stage(
        "computer_os", 2, "Computer and Operating System Fundamentals", "Computers & OS", "💻",
        "Understand how a computer and its operating system work, because security protects these things.",
        ("Describe what an operating system does.",
         "Find your way around files, folders, users and settings.",
         "Understand why permissions and updates matter."),
        (("Operating system (OS)", "The main program that runs a computer, such as Windows, macOS, Linux, Android or iOS."),
         ("Process", "A program that is running right now."),
         ("File system", "The way files and folders are organised and stored."),
         ("User account and permissions", "Rules about who may read, change or run what."),
         ("Administrator", "An account that can change almost anything on the computer, so it needs extra care."),
         ("Patch (update)", "A fix from the maker that closes a known weakness.")),
        ("Navigate files and settings confidently", "Manage user accounts and permissions",
         "Install and remove software safely", "Back up and restore files"),
        ("How an operating system works, at a high level", "Files, folders and paths", "Users, groups and permissions",
         "Installing software from trusted sources", "Updates and backups", "What a virtual machine is (a computer simulated inside your computer)"),
        ("Open Task Manager (Windows) or Activity Monitor (macOS) and name five programs that are running.",
         "Create a standard (non-administrator) account and note what it is not allowed to do.",
         "Back up a folder, then restore one file from the backup.",
         "Check the update settings on your device and turn on automatic updates."),
        "You understand the basic parts of a computer and can manage users, permissions, updates and backups.",
        "networking",
        pages=("cyber_hygiene",)),
    Stage(
        "networking", 3, "Networking Fundamentals", "Networking", "🌐",
        "Learn how computers talk to each other, because most attacks travel over networks.",
        ("Explain how data travels from your device to a website.",
         "Understand IP addresses, DNS and ports in simple terms.",
         "Know what a router and a firewall do."),
        (("IP address", "A number that identifies a device on a network, like a postal address."),
         ("DNS", "The internet's phone book: it turns a name such as example.org into an IP address."),
         ("Router", "The device that connects your home network to the internet."),
         ("Port", "A numbered door on a device that a particular service listens on."),
         ("Protocol", "An agreed set of rules for communicating, such as HTTP or HTTPS."),
         ("Firewall", "A filter that allows or blocks network traffic by rules.")),
        ("Read basic network information from your own devices", "Explain common protocols", "Understand a home network layout",
         "Secure a home router"),
        ("How data travels in packets (small pieces)", "IP addressing basics", "DNS", "Common protocols and ports",
         "Home networks, Wi-Fi security and firewalls"),
        ("Find your device's IP address and your router's address.",
         "Draw your home network: the router, each device and how they connect.",
         "On a router you own, change the default admin password and confirm Wi-Fi uses WPA2 or WPA3 encryption.",
         "Look up a domain name with your operating system's lookup tool and explain what the answer means."),
        "You can describe how devices connect and communicate, and you have secured your own router.",
        "linux_cli",
        course_ids=("cisco-networking-essentials",),
        pages=("courses",)),
    Stage(
        "linux_cli", 4, "Linux and Command-Line Basics", "Linux & CLI", "⌨️",
        "Get comfortable with the text-based way of controlling a computer, which many security tools use.",
        ("Explain what Linux is and why security people use it.",
         "Move around and manage files using typed commands.",
         "Understand Linux file permissions."),
        (("Linux", "A free, widely used family of operating systems."),
         ("Terminal and shell", "The window where you type commands, and the program that reads them."),
         ("Command", "A typed instruction, such as listing the files in a folder."),
         ("Permissions (read, write, execute)", "Three kinds of access that can be given to a file's owner, a group or everyone."),
         ("Package manager", "A tool that installs and updates software for you."),
         ("Root / sudo", "The all-powerful account, and the command that borrows its power for one task.")),
        ("Navigate with the command line", "Create, copy, move and search files", "Read and change permissions",
         "Write a very small script (a saved list of commands)"),
        ("Why Linux is used for security work", "Moving around: showing where you are, listing and changing folders",
         "Working with files carefully, since deleted files may not be recoverable", "File permissions",
         "Searching inside text files", "Installing software with a package manager"),
        ("Install a beginner-friendly Linux in a virtual machine, so your main computer is not affected.",
         "Practise ten basic commands until they feel natural.",
         "Create a folder and a file, then change who may read it.",
         "Search a text file for a word, then write a three-line script that does it for you."),
        "You can work in a Linux terminal for everyday tasks and understand how permissions protect files.",
        "web_security"),
    Stage(
        "web_security", 5, "Web Security Fundamentals", "Web Security", "🕸️",
        "Learn how websites work and how they are attacked, since the web is where most people meet threats.",
        ("Explain what happens when you open a website.",
         "Read a web address carefully and spot a suspicious one.",
         "Recognize a few common web weaknesses in simple terms."),
        (("HTTP and HTTPS", "The languages browsers and websites use to talk. HTTPS adds encryption, so others cannot read the traffic."),
         ("Cookie", "A small piece of data a site stores in your browser, often to remember that you are signed in."),
         ("Session", "The period during which a site recognises you after you sign in."),
         ("Input validation", "Checking what a user types before the site trusts it."),
         ("SQL injection", "Typing specially crafted text into a form to trick a site's database."),
         ("Cross-site scripting (XSS)", "Getting a site to show an attacker's code to other visitors."),
         ("OWASP Top 10", "A well-known public list of the most common web security problems.")),
        ("Read and judge a URL", "Explain how a request and a response work", "Describe common web weaknesses",
         "Browse more safely"),
        ("How websites work: requests and responses", "HTTPS and certificates (proof of a site's identity)",
         "Cookies and sessions", "Reading URLs and spotting fake sites", "An overview of the OWASP Top 10",
         "Safe password storage, in outline"),
        ("Take a web address apart piece by piece using the Learning Center lesson.",
         "Paste a suspicious link into the URL Security Scanner, which checks it without visiting it.",
         "Use your browser's built-in developer tools to look at the requests a public page makes (looking only).",
         "Read an overview of the OWASP Top 10 and explain three items in one sentence each."),
        "You can read links critically, explain how web traffic works and name the most common web weaknesses.",
        "tools_practice",
        lessons=("Reading a URL", "Recognizing phishing"),
        pages=("learning_center", "url_scanner")),
    Stage(
        "tools_practice", 6, "Cybersecurity Tools and Practical Skills", "Tools & Practice", "🛠️",
        "Start using real security tools in a safe, legal way.",
        ("Use beginner security tools on systems you own.",
         "Understand why permission and ethics come first.",
         "Build a small practice lab."),
        (("Hash", "A short fingerprint of a file. If the file changes, the fingerprint changes."),
         ("Vulnerability scanner", "A tool that checks a system for known weaknesses."),
         ("Packet capture", "Recording the data moving across a network so it can be examined."),
         ("Lab environment", "A safe, separate setup, often virtual machines, used only for practice."),
         ("Authorization", "Permission to test a system. Without it, testing may be illegal.")),
        ("Check a file's integrity with a hash", "Observe network traffic in your own lab", "Run a basic scan on your own lab systems",
         "Work within legal and ethical limits"),
        ("File hashes and integrity", "Scanning concepts", "Reading captured network traffic, in outline",
         "Building an isolated home lab", "Ethics, law and responsible disclosure (reporting a flaw to its owner)"),
        ("Compare a downloaded file's hash with the one the publisher posts, using the File Hash Analyzer.",
         "Check a QR code with the QR Code Security Analyzer and read what it reports.",
         "Build a small lab of virtual machines that you own, isolated from your main network.",
         "In that lab only, capture some network traffic with a beginner-friendly tool and identify the protocols you see."),
        "You can use beginner tools responsibly, in a lab you control, and explain why permission matters.",
        "security_operations",
        lessons=("Hashes and file integrity", "Interpreting VirusTotal results", "QR code risks ('quishing')"),
        course_ids=("cisco-ethical-hacker",),
        pages=("learning_center", "courses", "file_analyzer", "qr_analyzer")),
    Stage(
        "security_operations", 7, "Security Operations and Threat Analysis", "Security Operations", "🔍",
        "Learn how defenders watch for attacks and respond when something goes wrong.",
        ("Describe what a security operations team does.",
         "Read simple logs and alerts.",
         "Follow the basic steps of responding to an incident."),
        (("Security operations centre (SOC)", "A team that watches systems for signs of attack and responds."),
         ("Log", "A time-stamped record of what happened on a system."),
         ("SIEM", "A tool that gathers logs from many systems so alerts can be spotted in one place."),
         ("Incident", "A security event that causes, or could cause, harm."),
         ("Indicator of compromise (IOC)", "A clue that something bad happened, such as a suspicious file hash or web address."),
         ("Threat intelligence", "Information about attackers and how they work.")),
        ("Read logs and spot unusual activity", "Sort alerts into harmless and needs-attention", "Write a short incident note",
         "Check a suspicious file or link with a reputation service"),
        ("What a SOC does", "Logs and alerts", "The steps of incident response: prepare, detect, contain, recover, learn",
         "Indicators of compromise", "Threat intelligence basics", "How attackers typically work, at an overview level"),
        ("Read a sample log and find repeated failed sign-ins.",
         "Look at five example alerts and decide which are probably harmless and which need follow-up.",
         "Write a short incident note: what happened, when, what was affected and what you would do.",
         "Read a VirusTotal result using the Learning Center lesson and explain the verdict in your own words."),
        "You can read basic logs and alerts, explain how incidents are handled and write a clear incident note.",
        "specialization",
        lessons=("Interpreting VirusTotal results",),
        course_ids=("cisco-junior-cybersecurity-analyst", "ms-security-solutions-capabilities"),
        pages=("learning_center", "courses")),
    Stage(
        "specialization", 8, "Specialization and Career Preparation", "Specialization", "🎯",
        "Choose a direction, show what you can do, and plan your next steps.",
        ("Explore the main areas of cybersecurity work.",
         "Choose one area to go deeper in.",
         "Build evidence of your skills."),
        (("Specialization", "A focus area, such as security analysis, testing or cloud security."),
         ("Certification", "A professional exam that proves knowledge. It is separate from a course and is usually paid."),
         ("Digital badge", "A record that you completed a course. It is not a professional certification."),
         ("Portfolio", "A collection of your own work, such as write-ups of lab exercises."),
         ("Governance, risk and compliance (GRC)", "Work that sets security rules and checks they are followed.")),
        ("Compare career areas", "Write clearly about technical work", "Document your projects", "Plan further study"),
        ("Common areas: security analysis, penetration testing, cloud security, identity and access, GRC, digital forensics",
         "Reading real job descriptions", "Building a portfolio without exposing sensitive data",
         "How certifications differ from courses and badges", "CV and interview basics"),
        ("Pick one area and read two job descriptions in it, noting the skills they ask for.",
         "Write up two of your lab exercises as short, clear articles.",
         "Make a plan for the next three months, including which skill gaps to close.",
         "Practise explaining one of your projects aloud in two minutes."),
        "You have chosen a direction, have a small portfolio and know what to study next.",
        None,
        course_ids=("google-cybersecurity-certificate", "fortinet-fcf-cybersecurity"),
        pages=("courses",)),
)

STAGE_KEYS = tuple(s.key for s in STAGES)


def stage_by_key(key: str) -> Stage | None:
    return next((s for s in STAGES if s.key == key), None)
