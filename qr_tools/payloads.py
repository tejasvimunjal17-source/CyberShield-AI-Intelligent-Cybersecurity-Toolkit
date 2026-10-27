"""QR content types: validation and standards-based payload builders.

Every builder validates its fields and returns ``(payload, notes)`` where notes are
non-fatal advice for the user. Nothing here touches the network: URLs are only
checked syntactically and are never fetched or opened.

Existing builders in qr_tools.generator (URL, text, Wi-Fi, email) are reused, not
duplicated. All user text that is embedded in a structured format (vCard,
iCalendar, Wi-Fi, URLs) is escaped for that format.

A QR code stores text. It cannot hold a PDF/DOCX/etc.; the file-link types encode a
URL to a copy that is already hosted somewhere. This application does not host files.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Callable
from urllib.parse import quote, urlsplit

from qr_tools import generator as gen
from qr_tools.generator import QRError

Values = dict
Built = tuple[str, list[str]]

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# --------------------------------------------------------------------------
# Small validators
# --------------------------------------------------------------------------
def _clean(value, field: str, *, required: bool = False, max_len: int = 200, multiline: bool = False) -> str:
    text = ("" if value is None else str(value)).strip()
    if _CONTROL.search(text) or (not multiline and re.search(r"[\r\n]", text)):
        raise QRError(f"{field} contains characters that cannot be used.")
    if required and not text:
        raise QRError(f"Enter {field.lower()}.")
    if len(text) > max_len:
        raise QRError(f"{field} is longer than {max_len} characters.")
    return text


def normalize_phone(raw, field: str = "Phone number", *, min_digits: int = 3, max_digits: int = 15) -> str:
    """Return +digits or digits. Accepts spaces, dashes, dots and brackets; rejects letters."""
    text = _clean(raw, field, required=True, max_len=40)
    if re.search(r"[A-Za-z]", text) or not re.fullmatch(r"\+?[\d\s().\-]+", text):
        raise QRError(f"{field} may only contain digits, spaces, dashes, brackets and a leading +.")
    digits = re.sub(r"\D", "", text)
    if not (min_digits <= len(digits) <= max_digits):
        raise QRError(f"{field} must have {min_digits} to {max_digits} digits (including country code).")
    return ("+" if text.startswith("+") else "") + digits


def _email(value, field: str = "Email address", required: bool = True) -> str:
    text = _clean(value, field, required=required, max_len=254)
    if text and not _EMAIL.match(text):
        raise QRError("Enter a valid email address.")
    return text


def _http_url(value, field: str, *, required: bool = True, https_only: bool = False) -> tuple[str, list[str]]:
    text = _clean(value, field, required=required, max_len=1500)
    if not text:
        return "", []
    parts = urlsplit(text)
    if parts.scheme.lower() not in ("http", "https") or not parts.netloc:
        raise QRError(f"{field} must be a full URL starting with http:// or https://")
    if parts.username is not None or "@" in parts.netloc:
        raise QRError(f"{field} must not contain a username or password before the host name.")
    notes: list[str] = []
    if parts.scheme.lower() == "http":
        if https_only:
            raise QRError(f"{field} must use https://")
        notes.append("This link uses http://, which is not encrypted. Prefer https:// when the site supports it.")
    return text, notes


# --------------------------------------------------------------------------
# Basic and communication types
# --------------------------------------------------------------------------
def _url(v: Values) -> Built:
    text, notes = _http_url(v.get("url"), "URL")
    return gen.build_url_payload(text), notes


def _text(v: Values) -> Built:
    text = _clean(v.get("text"), "Text", required=True, max_len=gen.MAX_QR_TEXT_CHARS, multiline=True)
    return gen.build_text_payload(text), []


def _email_type(v: Values) -> Built:
    address = _email(v.get("address"))
    subject = _clean(v.get("subject"), "Subject", max_len=200)
    body = _clean(v.get("body"), "Message", max_len=500, multiline=True)
    params = []
    if subject:
        params.append("subject=" + quote(subject, safe=""))
    if body:
        params.append("body=" + quote(body, safe=""))
    payload = "mailto:" + address + ("?" + "&".join(params) if params else "")
    return gen.build_text_payload(payload), []


def _phone(v: Values) -> Built:
    return gen.build_text_payload("tel:" + normalize_phone(v.get("phone"))), []


def _sms(v: Values) -> Built:
    number = normalize_phone(v.get("phone"))
    message = _clean(v.get("message"), "Message", max_len=500, multiline=True)
    payload = f"SMSTO:{number}:{message}" if message else f"SMSTO:{number}"
    notes = ["SMS codes use the SMSTO format, read by most Android scanners and recent iPhones."]
    return gen.build_text_payload(payload), notes


def _wifi(v: Values) -> Built:
    security = v.get("security", "WPA")
    security = {"No password": "nopass"}.get(security, security)
    ssid = _clean(v.get("ssid"), "Network name", required=True, max_len=32)
    password = _clean(v.get("password"), "Password", max_len=63) if security != "nopass" else ""
    notes = ["Anyone who scans this code can join the network. Treat it like the password itself."]
    return gen.build_wifi_payload(ssid, password, security, bool(v.get("hidden"))), notes


def _whatsapp(v: Values) -> Built:
    number = normalize_phone(v.get("phone"), "WhatsApp number", min_digits=7)
    digits = number.lstrip("+")
    message = _clean(v.get("message"), "Message", max_len=500, multiline=True)
    payload = f"https://wa.me/{digits}" + (f"?text={quote(message, safe='')}" if message else "")
    notes = [] if number.startswith("+") else ["Use the full international number (country code first) or the chat will not open."]
    return gen.build_text_payload(payload), notes


# --------------------------------------------------------------------------
# vCard (contact and business)
# --------------------------------------------------------------------------
def _vc(value: str) -> str:
    """Escape a vCard TEXT value (backslash, semicolon, comma, newline)."""
    return (value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
            .replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\\n"))


def _vcard(v: Values, *, business: bool) -> Built:
    first = _clean(v.get("first"), "First name", max_len=60)
    last = _clean(v.get("last"), "Last name", max_len=60)
    org = _clean(v.get("org"), "Company name", required=business, max_len=100)
    if not business and not (first or last):
        raise QRError("Enter at least a first or last name.")
    if business and not org:
        raise QRError("Enter the company name.")
    title = _clean(v.get("title"), "Job title", max_len=100)
    phone = normalize_phone(v.get("phone"), "Phone") if _clean(v.get("phone"), "Phone", max_len=40) else ""
    mobile = normalize_phone(v.get("mobile"), "Mobile") if _clean(v.get("mobile"), "Mobile", max_len=40) else ""
    email = _email(v.get("email"), "Email", required=False)
    website, _ = _http_url(v.get("website"), "Website", required=False)
    street, city = _clean(v.get("street"), "Street", max_len=100), _clean(v.get("city"), "City", max_len=60)
    region, postcode = _clean(v.get("region"), "State or region", max_len=60), _clean(v.get("postcode"), "Postcode", max_len=20)
    country = _clean(v.get("country"), "Country", max_len=60)
    note = _clean(v.get("note"), "Note", max_len=300, multiline=True)

    full = " ".join(p for p in (first, last) if p) or org
    lines = ["BEGIN:VCARD", "VERSION:3.0", f"N:{_vc(last)};{_vc(first)};;;", f"FN:{_vc(full)}"]
    if org:
        lines.append(f"ORG:{_vc(org)}")
    if title:
        lines.append(f"TITLE:{_vc(title)}")
    if phone:
        lines.append(f"TEL;TYPE=WORK,VOICE:{phone}")
    if mobile:
        lines.append(f"TEL;TYPE=CELL:{mobile}")
    if email:
        lines.append(f"EMAIL;TYPE=INTERNET:{_vc(email)}")
    if website:
        lines.append(f"URL:{_vc(website)}")
    if any((street, city, region, postcode, country)):
        lines.append("ADR;TYPE=WORK:;;" + ";".join(_vc(p) for p in (street, city, region, postcode, country)))
    if note:
        lines.append(f"NOTE:{_vc(note)}")
    lines.append("END:VCARD")
    notes = ["Contact details in a QR code are readable by anyone who scans it. Share only what you intend to make public."]
    return gen.build_text_payload("\r\n".join(lines)), notes


def _contact(v: Values) -> Built:
    return _vcard(v, business=False)


def _business(v: Values) -> Built:
    return _vcard(v, business=True)


# --------------------------------------------------------------------------
# Social profiles
# --------------------------------------------------------------------------
def _host_ok(host: str, domains: tuple[str, ...]) -> bool:
    host = (host or "").lower().rstrip(".")
    return any(host == d or host.endswith("." + d) for d in domains)


def _profile(value, field: str, domains: tuple[str, ...], handle_re: str, build: Callable[[str], str],
             *, extra: Callable[[str], str | None] | None = None) -> Built:
    text = _clean(value, field, required=True, max_len=500)
    lower = text.lower()
    # A bare handle may contain dots (user.name); it is a link only if it has a scheme, a slash or starts with a known domain.
    looks_like_url = "://" in text or "/" in text or any(lower.startswith(d) or lower.startswith("www." + d) for d in domains)
    if looks_like_url:
        candidate = text if "://" in text else "https://" + text
        url, notes = _http_url(candidate, field, https_only=True)
        host = urlsplit(url).hostname or ""
        if not _host_ok(host, domains):
            raise QRError(f"{field} must be a link on {' / '.join(domains[:2])}. Other sites are not accepted here.")
        return gen.build_text_payload(url), notes
    handle = text.lstrip("@")
    if extra:
        built = extra(handle)
        if built:
            return gen.build_text_payload(built), []
    if not re.fullmatch(handle_re, handle):
        raise QRError(f"That does not look like a valid {field.lower()} name.")
    return gen.build_text_payload(build(handle)), []


def _instagram(v: Values) -> Built:
    return _profile(v.get("handle"), "Instagram profile", ("instagram.com", "instagr.am"),
                    r"[A-Za-z0-9._]{1,30}", lambda h: f"https://www.instagram.com/{h}/")


def _facebook(v: Values) -> Built:
    return _profile(v.get("handle"), "Facebook profile", ("facebook.com", "fb.com", "fb.me"),
                    r"[A-Za-z0-9.]{5,50}", lambda h: f"https://www.facebook.com/{h}")


def _youtube(v: Values) -> Built:
    def channel_id(h: str) -> str | None:
        return f"https://www.youtube.com/channel/{h}" if re.fullmatch(r"UC[A-Za-z0-9_-]{22}", h) else None
    return _profile(v.get("handle"), "YouTube channel", ("youtube.com", "youtu.be"),
                    r"[A-Za-z0-9._-]{3,30}", lambda h: f"https://www.youtube.com/@{h}", extra=channel_id)


def _linkedin(v: Values) -> Built:
    return _profile(v.get("handle"), "LinkedIn profile", ("linkedin.com", "lnkd.in"),
                    r"[A-Za-z0-9_%\-]{3,100}", lambda h: f"https://www.linkedin.com/in/{h}")


def _social_other(v: Values) -> Built:
    text, notes = _http_url(v.get("url"), "Profile URL")
    return gen.build_text_payload(text), notes + ["The destination site is not checked. Confirm the link is the profile you mean."]


# --------------------------------------------------------------------------
# Links to hosted files
# --------------------------------------------------------------------------
FILE_KINDS: dict[str, tuple[str, ...]] = {
    "PDF document": (".pdf",),
    "Word document": (".doc", ".docx"),
    "Excel spreadsheet": (".xls", ".xlsx"),
    "PowerPoint presentation": (".ppt", ".pptx"),
    "Text file": (".txt",),
    "CSV file": (".csv",),
    "ZIP archive": (".zip",),
    "Python source file": (".py",),
    "Other document (json, xml, md, rtf, odt, ods, odp, epub)": (".json", ".xml", ".md", ".rtf", ".odt", ".ods", ".odp", ".epub"),
}
BLOCKED_EXTENSIONS = (".exe", ".msi", ".bat", ".cmd", ".com", ".scr", ".pif", ".lnk", ".vbs", ".vbe", ".jar", ".apk",
                      ".dmg", ".pkg", ".ps1", ".hta", ".cpl", ".reg", ".dll", ".sh", ".js", ".jse", ".wsf", ".iso")
DRIVE_HOSTS = ("drive.google.com", "docs.google.com")
DRIVE_PATHS = ("/file/d/", "/document/d/", "/spreadsheets/d/", "/presentation/d/", "/drive/folders/", "/folders/", "/open", "/uc")


def _extension(path: str) -> str:
    last = path.rstrip("/").rsplit("/", 1)[-1]
    return "." + last.rsplit(".", 1)[-1].lower() if "." in last and 1 <= len(last.rsplit(".", 1)[-1]) <= 6 else ""


def _file_link(v: Values) -> Built:
    kind = v.get("kind") or next(iter(FILE_KINDS))
    if kind not in FILE_KINDS:
        raise QRError("Choose a file type from the list.")
    text, notes = _http_url(v.get("url"), "File link")
    ext = _extension(urlsplit(text).path)
    if ext in BLOCKED_EXTENSIONS:
        raise QRError(f"Links to {ext} files are not accepted. Programs and scripts that run on a device are blocked.")
    if ext and ext not in FILE_KINDS[kind]:
        raise QRError(f"The link ends in {ext}, which does not match '{kind}'. Pick the matching file type.")
    if not ext:
        notes.append("The link has no file extension (normal for cloud share links). Open it yourself first to check it "
                     "shows the right file and that sharing is set to 'anyone with the link'.")
    notes.append("The QR code contains this link only. The file itself must already be hosted at it.")
    return gen.build_text_payload(text), notes


def _drive_link(v: Values) -> Built:
    text, notes = _http_url(v.get("url"), "Google Drive link", https_only=True)
    parts = urlsplit(text)
    if (parts.hostname or "").lower() not in DRIVE_HOSTS:
        raise QRError("Use a link copied from Google Drive (drive.google.com or docs.google.com).")
    if not any(parts.path.startswith(p) or p in parts.path for p in DRIVE_PATHS):
        raise QRError("That Google link does not look like a file or folder share link. Use Share > Copy link.")
    notes.append("In Google Drive set General access to 'Anyone with the link', otherwise scanners will hit a sign-in page.")
    return gen.build_text_payload(text), notes


# --------------------------------------------------------------------------
# Calendar event (iCalendar)
# --------------------------------------------------------------------------
def _ics(value: str) -> str:
    return (value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
            .replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\\n"))


def _fold(line: str) -> str:
    """RFC 5545 line folding: at most 75 octets per physical line; continuation lines start with a space."""
    chunks: list[bytes] = []
    cur = b""
    for ch in line:
        enc = ch.encode("utf-8")
        limit = 75 if not chunks else 74           # a continuation line spends one octet on its leading space
        if len(cur) + len(enc) > limit:
            chunks.append(cur)
            cur = b""
        cur += enc
    chunks.append(cur)
    return "\r\n ".join(c.decode("utf-8") for c in chunks)


def _combine(d, t, field: str) -> datetime:
    if not isinstance(d, date) or isinstance(d, datetime):
        raise QRError(f"Choose the {field} date.")
    if not isinstance(t, time):
        raise QRError(f"Choose the {field} time.")
    return datetime.combine(d, t.replace(second=0, microsecond=0, tzinfo=None))


def _calendar(v: Values) -> Built:
    title = _clean(v.get("title"), "Event title", required=True, max_len=120)
    location = _clean(v.get("location"), "Location", max_len=200)
    description = _clean(v.get("description"), "Description", max_len=400, multiline=True)
    all_day, utc = bool(v.get("all_day")), bool(v.get("utc"))
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//CyberShield AI//QR Generator//EN", "CALSCALE:GREGORIAN"]
    if all_day:
        sd, ed = v.get("start_date"), v.get("end_date") or v.get("start_date")
        if not isinstance(sd, date) or not isinstance(ed, date):
            raise QRError("Choose the start and end dates.")
        if ed < sd:
            raise QRError("The event cannot end before it starts.")
        start_txt, end_txt = sd.strftime("%Y%m%d"), (ed + timedelta(days=1)).strftime("%Y%m%d")  # DTEND is exclusive
        dt_lines = [f"DTSTART;VALUE=DATE:{start_txt}", f"DTEND;VALUE=DATE:{end_txt}"]
        stamp = start_txt + "T000000Z"
    else:
        start, end = _combine(v.get("start_date"), v.get("start_time"), "start"), _combine(v.get("end_date"), v.get("end_time"), "end")
        if end <= start:
            raise QRError("The event must end after it starts.")
        z = "Z" if utc else ""
        start_txt, end_txt = start.strftime("%Y%m%dT%H%M%S") + z, end.strftime("%Y%m%dT%H%M%S") + z
        dt_lines = [f"DTSTART:{start_txt}", f"DTEND:{end_txt}"]
        stamp = start.strftime("%Y%m%dT%H%M%S") + "Z"
    # Deterministic UID and DTSTAMP: the same inputs always give the same QR code (no timestamp drift on reruns).
    uid = hashlib.sha256("|".join([title, location, description, *dt_lines]).encode("utf-8")).hexdigest()[:24]
    lines += ["BEGIN:VEVENT", f"UID:{uid}@cybershield-ai", f"DTSTAMP:{stamp}", f"SUMMARY:{_ics(title)}", *dt_lines]
    if location:
        lines.append(f"LOCATION:{_ics(location)}")
    if description:
        lines.append(f"DESCRIPTION:{_ics(description)}")
    lines += ["END:VEVENT", "END:VCALENDAR"]
    notes = ["Times are '" + ("UTC" if utc and not all_day else "floating" if not all_day else "all-day") + "'. "
             + ("" if utc or all_day else "A floating time is shown as the same clock time in the scanner's own time zone.")]
    return gen.build_text_payload("\r\n".join(_fold(line) for line in lines)), notes


# --------------------------------------------------------------------------
# Registry used by the UI and the tests
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Field:
    key: str
    label: str
    kind: str = "text"           # text | area | password | select | check | date | time
    required: bool = False
    help: str = ""
    placeholder: str = ""
    max_chars: int = 200
    options: tuple = ()
    default: object = None


@dataclass(frozen=True)
class ContentType:
    id: str
    label: str
    category: str
    fields: tuple[Field, ...]
    builder: Callable[[Values], Built]
    note: str = ""


CATEGORIES = ("Basic", "Contact & communication", "Social & business", "Files & documents", "Calendar")

CONTENT_TYPES: tuple[ContentType, ...] = (
    ContentType("url", "URL", "Basic", (Field("url", "URL", required=True, placeholder="https://example.com", max_chars=1500),), _url),
    ContentType("text", "Text", "Basic", (Field("text", "Text", "area", True, max_chars=gen.MAX_QR_TEXT_CHARS),), _text),
    ContentType("email", "Email", "Basic", (
        Field("address", "Email address", required=True, max_chars=254, placeholder="name@example.com"),
        Field("subject", "Subject (optional)", max_chars=200),
        Field("body", "Message (optional)", "area", max_chars=500)), _email_type),
    ContentType("phone", "Phone call", "Basic", (
        Field("phone", "Phone number", required=True, max_chars=40, placeholder="+1 555 010 0100",
              help="Include the country code, for example +44 20 7946 0958."),), _phone),
    ContentType("sms", "SMS message", "Basic", (
        Field("phone", "Phone number", required=True, max_chars=40, placeholder="+1 555 010 0100"),
        Field("message", "Message (optional)", "area", max_chars=500)), _sms),
    ContentType("wifi", "Wi-Fi", "Contact & communication", (
        Field("ssid", "Network name (SSID)", required=True, max_chars=32),
        Field("security", "Security", "select", options=("WPA", "WEP", "No password"), default="WPA"),
        Field("password", "Password", "password", max_chars=63),
        Field("hidden", "Hidden network", "check")), _wifi),
    ContentType("whatsapp", "WhatsApp chat link", "Contact & communication", (
        Field("phone", "WhatsApp number", required=True, max_chars=40, placeholder="+44 7700 900123",
              help="International format, country code first."),
        Field("message", "Pre-filled message (optional)", "area", max_chars=500)), _whatsapp),
    ContentType("vcard", "Contact card (vCard)", "Contact & communication", (
        Field("first", "First name", max_chars=60), Field("last", "Last name", max_chars=60),
        Field("org", "Company (optional)", max_chars=100), Field("title", "Job title (optional)", max_chars=100),
        Field("phone", "Phone (optional)", max_chars=40), Field("mobile", "Mobile (optional)", max_chars=40),
        Field("email", "Email (optional)", max_chars=254), Field("website", "Website (optional)", max_chars=300),
        Field("street", "Street (optional)", max_chars=100), Field("city", "City (optional)", max_chars=60),
        Field("region", "State or region (optional)", max_chars=60), Field("postcode", "Postcode (optional)", max_chars=20),
        Field("country", "Country (optional)", max_chars=60), Field("note", "Note (optional)", "area", max_chars=300)), _contact),
    ContentType("instagram", "Instagram profile", "Social & business", (
        Field("handle", "Username or profile link", required=True, max_chars=500, placeholder="@yourname"),), _instagram),
    ContentType("facebook", "Facebook profile or page", "Social & business", (
        Field("handle", "Username or profile link", required=True, max_chars=500, placeholder="yourpage"),), _facebook),
    ContentType("youtube", "YouTube channel", "Social & business", (
        Field("handle", "@handle, channel ID or link", required=True, max_chars=500, placeholder="@yourchannel"),), _youtube),
    ContentType("linkedin", "LinkedIn profile", "Social & business", (
        Field("handle", "Profile name or link", required=True, max_chars=500, placeholder="your-name"),), _linkedin),
    ContentType("social_other", "Other social profile (URL)", "Social & business", (
        Field("url", "Profile URL", required=True, max_chars=1500, placeholder="https://example.com/you"),), _social_other),
    ContentType("business", "Business contact (vCard)", "Social & business", (
        Field("org", "Company", required=True, max_chars=100), Field("first", "Contact first name (optional)", max_chars=60),
        Field("last", "Contact last name (optional)", max_chars=60), Field("title", "Job title (optional)", max_chars=100),
        Field("phone", "Business phone (optional)", max_chars=40), Field("mobile", "Mobile (optional)", max_chars=40),
        Field("email", "Business email (optional)", max_chars=254), Field("website", "Website (optional)", max_chars=300),
        Field("street", "Street (optional)", max_chars=100), Field("city", "City (optional)", max_chars=60),
        Field("region", "State or region (optional)", max_chars=60), Field("postcode", "Postcode (optional)", max_chars=20),
        Field("country", "Country (optional)", max_chars=60), Field("note", "Note (optional)", "area", max_chars=300)), _business),
    ContentType("file_link", "Link to a hosted file", "Files & documents", (
        Field("kind", "File type", "select", options=tuple(FILE_KINDS), default="PDF document"),
        Field("url", "Link to the hosted file", required=True, max_chars=1500, placeholder="https://example.com/menu.pdf")),
        _file_link,
        note="A QR code cannot contain a document. Upload the file to a hosting service you control (your website, "
             "Google Drive, Dropbox, OneDrive...) and paste its share link. CyberShield AI does not host files."),
    ContentType("drive", "Google Drive share link", "Files & documents", (
        Field("url", "Google Drive link", required=True, max_chars=1500, placeholder="https://drive.google.com/file/d/..."),),
        _drive_link,
        note="Create the link in Google Drive with Share > Copy link, and set access to 'Anyone with the link'. "
             "CyberShield AI does not upload to or host files on Drive."),
    ContentType("calendar", "Calendar event", "Calendar", (
        Field("title", "Event title", required=True, max_chars=120), Field("location", "Location (optional)", max_chars=200),
        Field("all_day", "All-day event", "check"),
        Field("start_date", "Start date", "date"), Field("start_time", "Start time", "time"),
        Field("end_date", "End date", "date"), Field("end_time", "End time", "time"),
        Field("utc", "Times are UTC", "check", help="Leave off to use the scanner's own local time."),
        Field("description", "Description (optional)", "area", max_chars=400)), _calendar),
)
TYPES_BY_ID = {t.id: t for t in CONTENT_TYPES}


def build(type_id: str, values: Values) -> Built:
    """Validate ``values`` for a content type and return (payload, notes). Raises QRError."""
    if type_id not in TYPES_BY_ID:
        raise QRError("Unknown content type.")
    return TYPES_BY_ID[type_id].builder(dict(values or {}))


def readable_preview(payload: str, limit: int = 400) -> str:
    """Payload text for display. Wi-Fi passwords are masked so shoulder-surfers do not read them."""
    shown = re.sub(r"(?<=;P:)(?:\\.|[^;\\])*", "••••••", payload) if payload.upper().startswith("WIFI:") else payload
    shown = shown.replace("\r\n", "\n")
    return shown if len(shown) <= limit else shown[:limit] + f"... ({len(payload)} characters in total)"
