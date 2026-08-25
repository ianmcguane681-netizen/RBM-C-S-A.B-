"""What a good small-business website has to do, written down, so that "this one does not"
is a claim with a definition behind it.

Everything else in this package refuses to guess. This file is where the guessing would
otherwise happen, because "their website is bad" is a matter of taste until somebody writes
the criteria down — and a tool that approaches strangers on the strength of an aesthetic
judgement has no answer when one of them asks what exactly is wrong with it.

So: named criteria, each one checkable, each one with a reason a business owner would
accept, arranged in tiers by what failing it costs THEM. Not weighted, not summed. The
argument against a score is the same one as everywhere else and it bites hardest here,
because a score would let a site that does not work on a phone pass on the strength of its
meta description.

## The tiers, and the rule that comes out of them

    BLOCKING     the site does not work at all. Nobody sees anything
    MOBILE       it does not work on a phone, which is where most local search happens
    CONVERSION   a visitor cannot act: no tappable number, no address, no hours
    CRAFT        title, description, structured data, a favicon. Real, and not urgent

**A business is only approached over a failure in the first three tiers.** Craft failures
are recorded, and are worth mentioning once a conversation exists, but a cold email to a
stranger saying their meta description is missing is the kind of message that gets this
whole activity a reputation. Tiers one to three are things that cost the owner customers;
tier four is a thing that would make a web developer wince. Only one of those is their
problem.

## Mobile is a tier of its own, above conversion, on purpose

Most people looking for a local business are on a phone, standing somewhere, deciding
whether to walk in or call. A site that renders at desktop width on a phone has not
degraded gracefully; it has failed, and it fails for the majority of the people who reach
it. A missing viewport tag is a one-line fix that nobody has made — which is exactly the
kind of thing worth telling somebody about.

## What this cannot see, stated so nobody mistakes the list for the whole picture

No rendering happens here. There is no browser, so there is no measurement of what actually
paints, no Core Web Vitals, no screenshot, no view of a layout that collapses at 360px for
reasons invisible in the markup. What is checked is what can be read from the document and
the response: tags, structure, sizes, links, and the presence or absence of the things a
person needs in order to act. A criterion that cannot be evaluated returns `NOT_ASSESSED`
and blocks rather than passing, which is the same rule the rest of the package uses.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Sequence

MEETS = "MEETS"
FAILS = "FAILS"
NOT_ASSESSED = "NOT_ASSESSED"

BLOCKING = "BLOCKING"
MOBILE = "MOBILE"
CONVERSION = "CONVERSION"
CRAFT = "CRAFT"

#: Tier order, worst first. Used to pick which failure a note opens with, because a site
#: that does not load and a site with no favicon are both "failures" and only one of them
#: is worth a stranger's first sentence.
TIERS = (BLOCKING, MOBILE, CONVERSION, CRAFT)

#: A failure in these tiers is a reason to approach a business. A failure in CRAFT is not.
APPROACHABLE_TIERS = (BLOCKING, MOBILE, CONVERSION)


@dataclass(frozen=True, slots=True)
class Criterion:
    """One named quality, why it matters to the owner, and how it is established."""

    code: str
    tier: str
    title: str
    why: str
    how: str


CRITERIA: tuple[Criterion, ...] = (
    Criterion("LOADS", BLOCKING, "The site loads",
              "A site that does not answer is worse than no site: it is a dead address "
              "printed on a van, a card and a directory listing.",
              "Two fetches, spaced, both failing."),
    Criterion("NOT_AN_ERROR", BLOCKING, "The address is the site, not an error page",
              "A listed address that returns 404 or 500 sends every visitor who followed "
              "it away.",
              "HTTP status of the final response after redirects."),
    Criterion("NOT_A_PLACEHOLDER", BLOCKING, "It is a site, not a parking page",
              "A domain-for-sale or default server page tells a customer the business is "
              "gone, whatever the truth is.",
              "Known placeholder phrases in the body text."),
    Criterion("HTTPS", BLOCKING, "It is served over HTTPS",
              "Browsers label plain HTTP 'Not secure' in the address bar, and that label "
              "is the first thing a visitor reads about the business.",
              "The site answers on https:// with a non-error status."),

    Criterion("VIEWPORT", MOBILE, "It is built for a phone screen",
              "Without a viewport tag a phone renders the page at desktop width and "
              "shrinks it, so everything is unreadable until the visitor pinches. Most "
              "local searches are on a phone.",
              "A meta viewport tag with width=device-width."),
    Criterion("ZOOM_ALLOWED", MOBILE, "A visitor can zoom in",
              "Blocking zoom breaks the page for anyone who needs larger text, and it is "
              "usually copied in from a template by accident.",
              "The viewport tag does not set user-scalable=no or maximum-scale=1."),
    Criterion("NO_FIXED_WIDTH", MOBILE, "The layout is not pinned to a desktop width",
              "A layout hard-coded to 960 or 1024 pixels forces sideways scrolling on "
              "every phone, which is where most of the traffic is.",
              "No fixed pixel width of 700px or more on a top-level container, and no "
              "table layout with a wide width attribute."),
    Criterion("NO_LEGACY_MARKUP", MOBILE, "It is not built on markup that predates phones",
              "Framesets, table layouts, <font> tags and Flash objects do not adapt to a "
              "small screen and cannot be made to.",
              "Presence of frameset, Flash objects, font/center tags, or nested layout "
              "tables."),
    Criterion("NOT_HEAVY", MOBILE, "The page is not enormous over mobile data",
              "A very large document with a queue of render-blocking scripts is a blank "
              "screen for several seconds on a phone signal, and people leave.",
              "HTML document size, and the number of render-blocking scripts and "
              "stylesheets in the head."),

    Criterion("PHONE_TAPPABLE", CONVERSION, "The phone number can be tapped to call",
              "On a phone, a number that is not a tel: link has to be memorised, "
              "retyped, or copied — and most people just leave.",
              "A tel: link, or no phone number anywhere on the page."),
    Criterion("ADDRESS_PRESENT", CONVERSION, "Somebody can find where you are",
              "A visitor standing in the street deciding whether to walk in needs the "
              "address on the page, not on a third-party listing.",
              "A postal address in the text or in structured data, or a map link."),
    Criterion("HOURS_PRESENT", CONVERSION, "Opening hours are on the page",
              "'Are they open now' is the single most common question a local site is "
              "asked, and answering it elsewhere sends people to Google's answer instead "
              "of yours.",
              "Opening hours in the text or in structured data."),
    Criterion("CONTACT_PATH", CONVERSION, "There is a way to get in touch that is not the phone",
              "Not everyone can call: people message outside hours, from work, or because "
              "they would rather write it down.",
              "A mailto: link, a contact form, or a link to a contact page."),

    Criterion("TITLE", CRAFT, "The page has a title",
              "The title is the line in the search result and the name on the browser "
              "tab.",
              "A non-empty <title>."),
    Criterion("META_DESCRIPTION", CRAFT, "There is a description for search results",
              "Without one, the search engine picks a sentence, and it is usually the "
              "cookie banner.",
              "A meta description with some text in it."),
    Criterion("HEADING", CRAFT, "The page has a real heading",
              "An <h1> is what tells a search engine and a screen reader what this page "
              "is.",
              "Exactly one non-empty <h1>."),
    Criterion("STRUCTURED_DATA", CRAFT, "The business is described in structured data",
              "LocalBusiness JSON-LD is how the hours, address and phone reach the map "
              "card and the answer box.",
              "A JSON-LD script mentioning a LocalBusiness type."),
    Criterion("SOCIAL_PREVIEW", CRAFT, "It looks like something when shared",
              "Without og: tags, a link pasted into a message is a bare grey URL.",
              "og:title and og:image."),
    Criterion("FAVICON", CRAFT, "It has an icon in the tab",
              "A default icon among twenty tabs is a business that looks unfinished.",
              "A link rel=icon or apple-touch-icon."),
    Criterion("LANG", CRAFT, "The page declares its language",
              "Screen readers and translation tools both need it, and it costs one "
              "attribute.",
              "A lang attribute on <html>."),
)

BY_CODE = {criterion.code: criterion for criterion in CRITERIA}


@dataclass(frozen=True, slots=True)
class Assessment:
    """One criterion, checked."""

    code: str
    state: str
    detail: str = ""

    @property
    def criterion(self) -> Criterion:
        return BY_CODE[self.code]

    @property
    def tier(self) -> str:
        return self.criterion.tier


@dataclass(frozen=True, slots=True)
class Report:
    """Every criterion, checked or not, and what follows from that."""

    assessments: tuple[Assessment, ...]
    url: str = ""
    reason: str = ""

    def by_state(self, state: str) -> tuple[Assessment, ...]:
        return tuple(a for a in self.assessments if a.state == state)

    def failures(self, tiers: Sequence[str] = TIERS) -> tuple[Assessment, ...]:
        """Failing criteria, worst tier first, in the order the criteria are declared."""

        order = {tier: i for i, tier in enumerate(TIERS)}
        failed = [a for a in self.assessments if a.state == FAILS and a.tier in tiers]
        return tuple(sorted(failed, key=lambda a: order[a.tier]))

    @property
    def approachable_failures(self) -> tuple[Assessment, ...]:
        """The failures that are a reason to write to somebody. Never the craft ones."""

        return self.failures(APPROACHABLE_TIERS)

    @property
    def lead(self) -> Assessment | None:
        """The one failure a first sentence should be about."""

        failures = self.approachable_failures
        return failures[0] if failures else None

    @property
    def blocked(self) -> bool:
        """Whether a criterion that decides the verdict could not be evaluated."""

        return any(a.state == NOT_ASSESSED and a.tier in APPROACHABLE_TIERS
                   for a in self.assessments)

    def describe(self) -> str:
        lines = []
        for tier in TIERS:
            in_tier = [a for a in self.assessments if a.tier == tier]
            if not in_tier:
                continue
            fails = sum(1 for a in in_tier if a.state == FAILS)
            unknown = sum(1 for a in in_tier if a.state == NOT_ASSESSED)
            head = f"{tier:11} {len(in_tier) - fails - unknown}/{len(in_tier)} met"
            if fails:
                head += f", {fails} failed"
            if unknown:
                head += f", {unknown} not assessed"
            lines.append(head)
            for assessment in in_tier:
                if assessment.state == MEETS:
                    continue
                mark = "FAIL" if assessment.state == FAILS else "----"
                lines.append(f"  {mark}  {assessment.criterion.title}: {assessment.detail}")
        if not self.approachable_failures:
            lines.append("No failure in BLOCKING, MOBILE or CONVERSION. Craft findings are "
                         "not a reason to approach anybody.")
        return "\n".join(lines)


class _Document(HTMLParser):
    """Everything the criteria need, read once, from the standard library."""

    _BLOCK_TAGS = ("script", "style")

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.lang = ""
        self.viewport = ""
        self.description = ""
        self.og: dict[str, str] = {}
        self.h1: list[str] = []
        self.links: list[tuple[str, str]] = []
        self.icons = 0
        self.forms = 0
        self.styles: list[str] = []
        self.jsonld: list[str] = []
        self.head_scripts_blocking = 0
        self.head_stylesheets = 0
        self.legacy: set[str] = set()
        self.img_widths: list[int] = []
        self.table_widths: list[int] = []
        self.inline_widths: list[int] = []
        self.text_parts: list[str] = []
        self._in_head = True
        self._in = ""
        self._skip = 0
        self._link_text: list[str] = []

    # -- helpers ------------------------------------------------------------------
    @staticmethod
    def _px(value: str) -> int | None:
        match = re.search(r"(\d{2,5})\s*px", value or "", re.I) or re.fullmatch(
            r"\s*(\d{2,5})\s*", value or "")
        return int(match.group(1)) if match else None

    def handle_starttag(self, tag, attrs):
        values = {k.lower(): (v or "") for k, v in attrs}
        if tag in self._BLOCK_TAGS:
            self._skip += 1
        if tag == "html":
            self.lang = values.get("lang", "")
        elif tag == "title":
            self._in = "title"
        elif tag == "meta":
            name = (values.get("name") or values.get("property") or "").lower()
            content = values.get("content", "")
            if name == "viewport":
                self.viewport = content.lower()
            elif name == "description":
                self.description = content.strip()
            elif name.startswith("og:"):
                self.og[name] = content.strip()
        elif tag == "link":
            rel = values.get("rel", "").lower()
            if "icon" in rel:
                self.icons += 1
            if "stylesheet" in rel and self._in_head:
                self.head_stylesheets += 1
        elif tag == "script":
            kind = values.get("type", "").lower()
            if kind == "application/ld+json":
                self._in = "jsonld"
            elif self._in_head and values.get("src") and not (
                    "async" in values or "defer" in values or kind == "module"):
                self.head_scripts_blocking += 1
        elif tag == "style":
            self._in = "style"
        elif tag == "h1":
            self._in = "h1"
            self.h1.append("")
        elif tag == "a":
            self.links.append((values.get("href", ""), ""))
            self._in = "a"
        elif tag == "form":
            self.forms += 1
        elif tag == "img":
            width = self._px(values.get("width", "")) or self._px(values.get("style", ""))
            if width:
                self.img_widths.append(width)
        elif tag == "table":
            width = self._px(values.get("width", "")) or self._px(values.get("style", ""))
            if width:
                self.table_widths.append(width)
        elif tag in ("body", "div", "section", "main", "td"):
            width = self._px(values.get("style", ""))
            if width:
                self.inline_widths.append(width)
        elif tag in ("frameset", "frame", "font", "center", "marquee", "blink"):
            self.legacy.add(tag)
        elif tag == "object" and "shockwave-flash" in values.get("type", "").lower():
            self.legacy.add("flash")
        elif tag == "embed" and "flash" in values.get("type", "").lower():
            self.legacy.add("flash")

    def handle_endtag(self, tag):
        if tag in self._BLOCK_TAGS and self._skip:
            self._skip -= 1
        if tag == "head":
            self._in_head = False
        if tag in ("title", "h1", "a", "style", "script"):
            self._in = ""

    def handle_data(self, data):
        if self._in == "title":
            self.title += data
        elif self._in == "jsonld":
            self.jsonld.append(data)
        elif self._in == "style":
            self.styles.append(data)
        elif self._skip:
            return
        else:
            self.text_parts.append(data)
            if self._in == "h1" and self.h1:
                self.h1[-1] += data
            elif self._in == "a" and self.links:
                href, text = self.links[-1]
                self.links[-1] = (href, text + data)

    @property
    def text(self) -> str:
        return " ".join(" ".join(self.text_parts).split())


_PLACEHOLDER_PHRASES = (
    "this domain is for sale", "buy this domain", "domain for sale",
    "parked free, courtesy of", "site under construction", "under construction",
    "coming soon", "default web page", "welcome to nginx",
    "apache2 ubuntu default page", "future home of something quite cool",
    "account suspended", "index of /",
)
_PHONE = re.compile(r"(?:\+?\d[\d\s().-]{7,}\d)")
_HOURS_WORDS = ("opening hours", "hours", "open ", "mon", "tue", "wed", "thu", "fri",
                "sat", "sun", "horario", "horário", "öffnungszeiten", "horaires", "orari",
                "openingstijden", "uaireanta")
_TIME = re.compile(r"\b\d{1,2}[:.]\d{2}\s*(?:am|pm)?|\b\d{1,2}\s*(?:am|pm)\b", re.I)
_ADDRESS_WORDS = ("street", "st.", "road", "rd.", "avenue", "ave", "lane", "drive",
                  "suite", "rua", "avenida", "calle", "straße", "strasse", "rue",
                  "via ", "sráid", "bóthar", "address", "morada", "dirección", "adresse",
                  "indirizzo", "adres")
_POSTCODE = re.compile(r"\b(?:[A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2}"       # UK
                       r"|[A-Z]\d{2}\s?[A-Z0-9]{4}"                        # IE eircode
                       r"|\d{5}(?:-\d{4})?"                                # US / DE / ES
                       r"|\d{4}-\d{3})\b")                                 # PT
_MAP_HOSTS = ("google.com/maps", "goo.gl/maps", "maps.app.goo.gl", "openstreetmap.org",
              "waze.com", "apple.com/maps", "maps.apple.com")
_CONTACT_WORDS = ("contact", "kontakt", "contacto", "contatti", "contact-us", "enquiry",
                  "enquiries", "teagmh")

#: A document larger than this is a slow first paint on a phone signal whatever else is
#: true of it. Generous on purpose: the criterion is meant to catch pages nobody could
#: defend, not pages a developer would argue about.
HEAVY_HTML_BYTES = 600 * 1024
#: Scripts in the head with neither async nor defer. Each one stops the page from painting.
HEAVY_BLOCKING_SCRIPTS = 8
#: A container this wide, in fixed pixels, does not fit any phone.
DESKTOP_WIDTH_PX = 700


def _fixed_widths(document: _Document) -> list[int]:
    widths = [w for w in document.inline_widths + document.table_widths
              if w >= DESKTOP_WIDTH_PX]
    for block in document.styles:
        for match in re.finditer(r"(?:^|[{;\s])width\s*:\s*(\d{3,5})px", block, re.I):
            value = int(match.group(1))
            if value >= DESKTOP_WIDTH_PX:
                widths.append(value)
        # A min-width on the body is the same failure wearing a different property, and is
        # what template-era sites actually carry.
        for match in re.finditer(r"min-width\s*:\s*(\d{3,5})px", block, re.I):
            value = int(match.group(1))
            if value >= DESKTOP_WIDTH_PX:
                widths.append(value)
    return widths


def assess(html: str, *, url: str = "", status: int | None = None,
           https_available: bool | None = None, reached: bool | None = None,
           byte_size: int | None = None) -> Report:
    """Every criterion against one fetched page.

    `reached`, `status` and `https_available` come from the fetcher rather than the
    document, because whether a site answered is not a fact about its markup. `None` for
    any of them means the fetcher could not tell, and produces `NOT_ASSESSED` rather than
    a pass — the criteria that decide whether somebody gets an email are the ones where
    guessing is least affordable.
    """

    results: list[Assessment] = []

    def record(code: str, state: str, detail: str = "") -> None:
        results.append(Assessment(code, state, detail))

    # --- BLOCKING ----------------------------------------------------------------
    if reached is None:
        record("LOADS", NOT_ASSESSED, "the fetcher did not say whether the site answered")
    elif reached:
        record("LOADS", MEETS, "the site answered")
    else:
        record("LOADS", FAILS, "two attempts, spaced, and neither got a response")

    if status is None:
        record("NOT_AN_ERROR", NOT_ASSESSED, "no HTTP status was recorded")
    elif status >= 400:
        record("NOT_AN_ERROR", FAILS, f"the address answered HTTP {status}")
    else:
        record("NOT_AN_ERROR", MEETS, f"HTTP {status}")

    lowered = (html or "").lower()
    document = _Document()
    parsed = True
    try:
        document.feed(html or "")
    except Exception as exc:  # noqa: BLE001 - tag soup is a fact about the page, not a crash
        parsed = False
        record("NOT_A_PLACEHOLDER", NOT_ASSESSED, f"the markup would not parse: {exc!r}")

    if parsed:
        hit = next((phrase for phrase in _PLACEHOLDER_PHRASES if phrase in lowered), "")
        if hit:
            record("NOT_A_PLACEHOLDER", FAILS, f"the page reads as a placeholder: {hit!r}")
        elif not document.text.strip():
            record("NOT_A_PLACEHOLDER", FAILS, "the page has no text on it at all")
        else:
            record("NOT_A_PLACEHOLDER", MEETS, "real content, not a parking page")

    if https_available is None:
        record("HTTPS", NOT_ASSESSED, "whether the site answers over HTTPS could not be told")
    elif https_available:
        record("HTTPS", MEETS, "answers over HTTPS")
    else:
        record("HTTPS", FAILS, "no HTTPS, so browsers show visitors 'Not secure'")

    if not parsed:
        for code in ("VIEWPORT", "ZOOM_ALLOWED", "NO_FIXED_WIDTH", "NO_LEGACY_MARKUP",
                     "NOT_HEAVY", "PHONE_TAPPABLE", "ADDRESS_PRESENT", "HOURS_PRESENT",
                     "CONTACT_PATH", "TITLE", "META_DESCRIPTION", "HEADING",
                     "STRUCTURED_DATA", "SOCIAL_PREVIEW", "FAVICON", "LANG"):
            record(code, NOT_ASSESSED, "the document could not be parsed")
        return Report(tuple(results), url=url)

    # --- MOBILE ------------------------------------------------------------------
    initial_scale_one = re.search(r"initial-scale\s*=\s*1(?:\.0)?\b", document.viewport)
    if "width=device-width" in document.viewport.replace(" ", ""):
        record("VIEWPORT", MEETS, "meta viewport is set to the device width")
    elif initial_scale_one:
        # The older form. `initial-scale=1` alone gets browsers to the same place in
        # practice, and calling it a failure would put a wrong sentence in an email — which
        # costs more than the criterion is worth being strict about.
        record("VIEWPORT", MEETS,
               f"the older form, {document.viewport!r}, which browsers treat the same way")
    elif document.viewport:
        record("VIEWPORT", FAILS,
               f"the viewport tag does not set the width: {document.viewport!r}")
    else:
        record("VIEWPORT", FAILS,
               "no viewport tag, so phones render the page at desktop width and shrink it")

    if not document.viewport:
        record("ZOOM_ALLOWED", NOT_ASSESSED, "there is no viewport tag to read")
    elif "user-scalable=no" in document.viewport or "maximum-scale=1" in document.viewport:
        record("ZOOM_ALLOWED", FAILS, "the viewport tag blocks pinch-zoom")
    else:
        record("ZOOM_ALLOWED", MEETS, "zoom is not blocked")

    widths = _fixed_widths(document)
    if widths:
        record("NO_FIXED_WIDTH", FAILS,
               f"a fixed width of {max(widths)}px, which forces sideways scrolling on a phone")
    else:
        record("NO_FIXED_WIDTH", MEETS, "no desktop-width container found")

    # `<font>` and `<center>` on their own are untidy rather than broken — plenty of
    # perfectly usable pages carry one. What cannot be made to work on a phone is a
    # frameset, a Flash object, or a page laid out in fixed-width tables, so the criterion
    # fails on those and on the combination that means "laid out in 1998".
    hard = document.legacy & {"frameset", "frame", "flash", "marquee", "blink"}
    dated = document.legacy & {"font", "center"}
    wide_tables = [w for w in document.table_widths if w >= DESKTOP_WIDTH_PX]
    if hard:
        record("NO_LEGACY_MARKUP", FAILS,
               f"markup that predates phones and cannot adapt: {', '.join(sorted(hard))}")
    elif dated and wide_tables:
        record("NO_LEGACY_MARKUP", FAILS,
               f"a fixed-width table layout with {', '.join(sorted(dated))} tags — a "
               f"desktop-era page that a phone cannot reflow")
    else:
        record("NO_LEGACY_MARKUP", MEETS,
               "no framesets, Flash or fixed-width table layout")

    if byte_size is None:
        record("NOT_HEAVY", NOT_ASSESSED, "the document size was not recorded")
    elif byte_size > HEAVY_HTML_BYTES:
        record("NOT_HEAVY", FAILS,
               f"{byte_size // 1024} KB of HTML before a single image or script")
    elif document.head_scripts_blocking > HEAVY_BLOCKING_SCRIPTS:
        record("NOT_HEAVY", FAILS,
               f"{document.head_scripts_blocking} render-blocking scripts in the head")
    else:
        record("NOT_HEAVY", MEETS,
               f"{byte_size // 1024} KB, {document.head_scripts_blocking} blocking scripts")

    # --- CONVERSION --------------------------------------------------------------
    tel_links = [href for href, _ in document.links if href.lower().startswith("tel:")]
    phone_in_text = bool(_PHONE.search(document.text))
    if tel_links:
        record("PHONE_TAPPABLE", MEETS, f"{len(tel_links)} tel: link(s)")
    elif phone_in_text:
        record("PHONE_TAPPABLE", FAILS,
               "the phone number is text, not a tel: link, so it cannot be tapped to call")
    else:
        record("PHONE_TAPPABLE", FAILS, "no phone number anywhere on the page")

    structured = " ".join(document.jsonld).lower()
    has_map = any(host in href.lower() for href, _ in document.links for host in _MAP_HOSTS)
    address_words = any(word in document.text.lower() for word in _ADDRESS_WORDS)
    if has_map or ("address" in structured) or (address_words and _POSTCODE.search(document.text)):
        record("ADDRESS_PRESENT", MEETS, "an address or a map link is on the page")
    elif address_words:
        record("ADDRESS_PRESENT", FAILS,
               "something address-shaped is on the page but no postcode and no map link, "
               "so a visitor cannot navigate to it")
    else:
        record("ADDRESS_PRESENT", FAILS, "no address and no map link")

    hours_words = any(word in document.text.lower() for word in _HOURS_WORDS)
    if "openinghours" in structured.replace(" ", ""):
        record("HOURS_PRESENT", MEETS, "opening hours are in the structured data")
    elif hours_words and _TIME.search(document.text):
        record("HOURS_PRESENT", MEETS, "opening hours are on the page")
    else:
        record("HOURS_PRESENT", FAILS,
               "no opening hours, which is the question a local site is asked most")

    mailto = [href for href, _ in document.links if href.lower().startswith("mailto:")]
    contact_link = any(word in (href + text).lower()
                       for href, text in document.links for word in _CONTACT_WORDS)
    if mailto or document.forms or contact_link:
        record("CONTACT_PATH", MEETS, "an email address, a form or a contact page")
    else:
        record("CONTACT_PATH", FAILS, "no email, no form and no contact page — only a phone")

    # --- CRAFT -------------------------------------------------------------------
    record("TITLE", MEETS if document.title.strip() else FAILS,
           document.title.strip()[:80] or "no <title>")
    record("META_DESCRIPTION", MEETS if document.description else FAILS,
           document.description[:80] or "no meta description")
    headings = [h for h in document.h1 if h.strip()]
    if len(headings) == 1:
        record("HEADING", MEETS, headings[0].strip()[:60])
    elif not headings:
        record("HEADING", FAILS, "no <h1> on the page")
    else:
        record("HEADING", FAILS, f"{len(headings)} <h1> headings, so none of them is THE one")
    record("STRUCTURED_DATA", MEETS if "localbusiness" in structured.replace(" ", "")
           else FAILS,
           "LocalBusiness JSON-LD" if "localbusiness" in structured.replace(" ", "")
           else "no LocalBusiness structured data, so the map card is built from guesses")
    if document.og.get("og:title") and document.og.get("og:image"):
        record("SOCIAL_PREVIEW", MEETS, "og:title and og:image")
    else:
        record("SOCIAL_PREVIEW", FAILS,
               "a link to this page pastes into a message as a bare URL")
    record("FAVICON", MEETS if document.icons else FAILS,
           f"{document.icons} icon link(s)" if document.icons else "no favicon")
    record("LANG", MEETS if document.lang else FAILS,
           document.lang or "no lang attribute on <html>")

    return Report(tuple(results), url=url)
