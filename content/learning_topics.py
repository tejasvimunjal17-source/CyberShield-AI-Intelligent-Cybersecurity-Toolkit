"""Static educational content for the Learning Center. Plain text only."""

TOPICS = (
    ("Recognizing phishing", [
        "Phishing messages try to rush you into clicking, logging in, paying, or sharing a code.",
        "Warning signs: urgency or threats, unexpected attachments, sender addresses that nearly match a real one, links whose real destination differs from the text, and requests for passwords or one-time codes.",
        "Safer habit: do not use the link in the message. Open the organization's app or type its address yourself, then check for the same notice.",
        "No legitimate service asks for your password or a one-time code by chat, email, or phone.",
    ]),
    ("Reading a URL", [
        "The part that decides the destination is the hostname, between '://' and the next '/'. In https://login.example.com.attacker.net/x the real domain is attacker.net.",
        "An '@' in a URL hides the real host: everything before it is ignored when choosing the destination.",
        "Punycode ('xn--') shows that a hostname contains non-English characters, which can imitate familiar names.",
        "Shorteners such as bit.ly hide where a link goes. Expand them with a trusted tool before opening.",
        "HTTPS means the connection is encrypted. It does not mean the site is trustworthy: attackers use HTTPS too.",
    ]),
    ("Hashes and file integrity", [
        "A hash is a fixed-length fingerprint of a file's bytes. Change one byte and the hash changes completely.",
        "Compare the SHA-256 of a download with the hash the publisher posted, ideally from a different channel than the download itself. A match means the file is identical to what they hashed.",
        "Hashes do not say whether a file is harmful. A malicious file has a hash too.",
        "MD5 and SHA-1 are weak against deliberate collisions. Prefer SHA-256.",
    ]),
    ("QR code risks ('quishing')", [
        "A QR code is just a URL or text in a machine-readable form. You cannot see where it leads by looking at it.",
        "Attackers stick fake codes over real ones on parking meters, posters, and menus, or email codes that bypass link filters.",
        "Preview the decoded address before opening it. If a code asks you to log in or pay, go to the official app or website instead.",
        "Be cautious with Wi-Fi codes from unknown sources: joining an unknown network exposes your traffic.",
    ]),
    ("Interpreting VirusTotal results", [
        "VirusTotal combines the verdicts of many security engines. Look at how many agree, not just whether one flagged.",
        "Malicious and suspicious are detections. Undetected is not a clean bill of health.",
        "Zero detections on a brand-new file or URL mean little: engines may not know it yet.",
        "A single odd detection on a popular, signed file is often a false positive. Check the report date and the engines involved.",
    ]),
    ("Passwords and multi-factor authentication", [
        "Use a unique long password for every account, stored in a password manager.",
        "Turn on multi-factor authentication, preferring authenticator apps or hardware keys over SMS codes.",
        "If you entered a password on a suspicious page, change it immediately on the real site and anywhere you reused it.",
    ]),
    ("Using this toolkit responsibly", [
        "Analyze only URLs and files you are allowed to examine. The app never opens links or runs files.",
        "Heuristic findings are hints, VirusTotal reports are third-party data, and AI text is an explanation. Treat them differently.",
        "No tool gives a guarantee of safety. When in doubt, do not open it and ask a trusted person or your IT/security team.",
    ]),
)
