"""Look at a business's website and record what is measurably true about it.

The outreach lane's whole claim is "your site needs work". That claim has to be evidence
rather than opinion, or the approach is a stranger telling somebody their website is bad —
which is both rude and unanswerable. So this measures, and only measures things that can be
read off one HTTP response:

    the site answers at all, and over HTTPS with a valid certificate
    it declares a viewport, so a phone renders it at a readable size
    it has a title, and the title is not a template placeholder
    it carries a way to contact the business
    it is not a parked domain, a holding page or a builder's default
    how big the first response is, and how long it took

Everything a person might otherwise say — that it looks dated, that the copy is weak, that
the photography is poor — is deliberately absent. Those are real and this cannot establish
them, and a criterion that cannot be established is one that gets asserted anyway.

## Three states on every criterion, and the middle one is why this file is long

`PASS`, `FAIL`, `NOT_ASSESSED`. The last is not padding. A site that timed out has not
failed a mobile check; nothing was checked. A page whose HTML could not be decoded has not
failed a title check. Merging those into FAIL produces an approach that tells somebody
their site has a problem it may not have, and the one thing worse than not sending an
approach is sending a wrong one.

## What this deliberately does not do

No JavaScript is executed, so a single-page application that renders its content client-side
will look emptier than it is. That limitation is REPORTED — `RENDERED_BY_SCRIPT` — rather
than scored, because the honest reading of "the HTML is a shell and a bundle" is "this was
built with a framework", which is evidence AGAINST the site needing rebuilding rather than
for it.

Nothing is crawled. One request to one URL, following redirects, and that is the whole
budget: a stranger's site is not owed a crawl, and a lead list is not worth a load.
"""
from __future__ import annotations

import re
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Sequence

PASS = "PASS"
FAIL = "FAIL"
NOT_ASSESSED = "NOT_ASSESSED"

# What happened when the site was asked for.
REACHED = "REACHED"
UNREACHABLE = "UNREACHABLE"
ERRORED = "ERRORED"
NO_URL = "NO_URL"

#: Bytes of HTML read. Enough for the head and the top of the body, which is where every
#: criterion here lives, and small enough that a lead check never becomes a download.
READ_LIMIT = 200_000

#: Seconds. Generous, because a slow site is a finding rather than a failure to look, and
#: a small business on cheap shared hosting is exactly the prospect this lane wants.
TIMEOUT = 20

#: Above this, a first response is slow enough that a visitor on a phone notices. Not a
#: precise threshold and it is not treated as one — it is a FAIL that says the number.
SLOW_SECONDS = 4.0

#: Phrases that mean a domain is registered and not in use. Matched case-insensitively
#: against the title and the first part of the body.
PARKED_MARKERS = (
    "this domain is for sale", "buy this domain", "domain for sale",
    "under construction", "coming soon", "website coming soon",
    "index of /", "apache2 ubuntu default page", "welcome to nginx",
    "your new website is almost ready", "site not published",
)

#: Default titles that mean a site was made from a template and never finished.
PLACEHOLDER_TITLES = (
    "home", "untitled", "new page", "my website", "my site", "website",
    "just another wordpress site", "index",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class Criterion:
    """One thing that was checked, what it found, and what a person can do about it.

    `remedy` is what makes this an approach rather than a complaint. "No viewport" is a
    fact; "the page is not told to fit a phone screen, which is one line in the head" is
    something a business owner can hear without being insulted, and is the difference
    between a message that gets a reply and one that gets deleted.
    """

    name: str
    status: str
    detail: str
    remedy: str = ""
    #: True where a failure alone justifies an approach. The others are supporting.
    material: bool = True

    def describe(self) -> str:
        mark = {PASS: "  ok  ", FAIL: " FAIL ", NOT_ASSESSED: "  ??  "}[self.status]
        return f"[{mark}] {self.name}\n         {self.detail}"


@dataclass(frozen=True, slots=True)
class SiteReport:
    """Everything measured about one site, with the unmeasured kept unmeasured."""

    status: str
    url: str
    final_url: str = ""
    http_status: int = 0
    criteria: tuple[Criterion, ...] = ()
    elapsed_seconds: float = 0.0
    bytes_read: int = 0
    checked_at: str = ""
    reason: str = ""

    @property
    def failures(self) -> tuple[Criterion, ...]:
        return tuple(c for c in self.criteria if c.status == FAIL)

    @property
    def material_failures(self) -> tuple[Criterion, ...]:
        return tuple(c for c in self.failures if c.material)

    @property
    def unassessed(self) -> tuple[Criterion, ...]:
        return tuple(c for c in self.criteria if c.status == NOT_ASSESSED)

    @property
    def assessed(self) -> bool:
        """Whether anything was actually established. An unreachable site has not failed.

        The distinction the whole module turns on: `lib/outreach.py` may not draft an
        approach from a report where this is False, because there is nothing to say.
        """

        return self.status in {REACHED, ERRORED}

    def describe(self) -> str:
        if self.status == NO_URL:
            return (f"NO_URL: {self.reason}\n"
                    f"  Nothing was checked. This is not a finding about any website.")
        if self.status == UNREACHABLE:
            return (f"UNREACHABLE  {self.url}: {self.reason}\n"
                    f"  The site was not reached, so NOTHING about it has been "
                    f"established. It is not a bad site; it is an unanswered request, and "
                    f"a business must never be told otherwise.")
        head = (f"{self.status}  {self.url}"
                + (f" -> {self.final_url}" if self.final_url != self.url else "")
                + f"  HTTP {self.http_status}  {self.elapsed_seconds:.2f}s  "
                  f"{self.bytes_read:,} bytes")
        lines = [head] + [c.describe() for c in self.criteria]
        if self.unassessed:
            lines.append(
                f"  {len(self.unassessed)} criterion/criteria could NOT be assessed. Those "
                f"are not passes and they are not failures.")
        return "\n".join(lines)


def _text_of(pattern: str, html: str) -> str:
    found = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
    return found.group(1).strip() if found else ""


def _https(url: str, final_url: str, tls_error: str) -> Criterion:
    if tls_error:
        return Criterion(
            "https", FAIL,
            f"the certificate did not validate: {tls_error}. A browser shows a full-page "
            f"warning before anybody sees the site.",
            remedy="a free Let's Encrypt certificate, usually one switch at the host")
    target = final_url or url
    if target.lower().startswith("https://"):
        return Criterion("https", PASS, "served over HTTPS with a valid certificate")
    return Criterion(
        "https", FAIL,
        "served over plain HTTP. Chrome and Safari mark this Not Secure in the address "
        "bar, and search engines have ranked it down since 2018.",
        remedy="a free Let's Encrypt certificate and a redirect from http")


def _viewport(html: str) -> Criterion:
    if not html:
        return Criterion("mobile viewport", NOT_ASSESSED,
                         "no HTML was read, so nothing was checked")
    if re.search(r'<meta[^>]+name=["\']?viewport', html, re.IGNORECASE):
        return Criterion("mobile viewport", PASS,
                         "the page declares a viewport, so a phone renders it at a "
                         "readable size")
    return Criterion(
        "mobile viewport", FAIL,
        "no viewport meta tag. A phone renders the desktop layout scaled down, so the text "
        "is unreadable without pinching — and most local searches happen on a phone.",
        remedy="one line in the head, or a rebuild if the layout is fixed-width")


def _title(html: str) -> Criterion:
    if not html:
        return Criterion("page title", NOT_ASSESSED, "no HTML was read")
    title = _text_of(r"<title[^>]*>(.*?)</title>", html)
    if not title:
        return Criterion(
            "page title", FAIL,
            "the page has no title, so a search result and a browser tab both show the URL",
            remedy="a title naming the business and the town")
    if title.strip().lower() in PLACEHOLDER_TITLES:
        return Criterion(
            "page title", FAIL,
            f"the title is {title!r} — a template default. It is what shows in every "
            f"search result for this business.",
            remedy="a title naming the business and the town")
    return Criterion("page title", PASS, f"titled {title[:70]!r}")


def _contact(html: str) -> Criterion:
    """Whether a visitor can reach the business without leaving the page.

    Not material on its own. A shop whose phone number is on a contact page rather than the
    home page is normal, and this reads one page — so a FAIL here supports an approach and
    never justifies one by itself.
    """

    if not html:
        return Criterion("contact details", NOT_ASSESSED, "no HTML was read", material=False)
    has_tel = bool(re.search(r'href=["\']tel:', html, re.IGNORECASE))
    has_mail = bool(re.search(r'href=["\']mailto:', html, re.IGNORECASE))
    has_number = bool(re.search(r"\b0\d[\d \-()]{7,}\b", html))
    if has_tel or has_mail or has_number:
        return Criterion("contact details", PASS,
                         "a phone number or email is on the first page", material=False)
    return Criterion(
        "contact details", FAIL,
        "no phone, email or tel: link on the first page. A visitor on a phone has to hunt "
        "for a way to get in touch.",
        remedy="a tappable phone number in the header", material=False)


def _parked(html: str, title: str) -> Criterion:
    if not html:
        return Criterion("real content", NOT_ASSESSED, "no HTML was read")
    haystack = (title + " " + html[:4000]).lower()
    hit = next((marker for marker in PARKED_MARKERS if marker in haystack), "")
    if hit:
        return Criterion(
            "real content", FAIL,
            f"the page reads as a placeholder ({hit!r}) rather than a website. The domain "
            f"is registered and there is nothing behind it.",
            remedy="the site itself — this is the strongest case in the list")
    return Criterion("real content", PASS, "the page is not a parked or holding page")


def _speed(elapsed: float, size: int) -> Criterion:
    if elapsed <= 0:
        return Criterion("first response", NOT_ASSESSED, "the response was not timed",
                         material=False)
    if elapsed > SLOW_SECONDS:
        return Criterion(
            "first response", FAIL,
            f"the first response took {elapsed:.1f}s for {size:,} bytes. Above about four "
            f"seconds a visitor on a phone leaves before anything appears.",
            remedy="usually the host rather than the site", material=False)
    return Criterion("first response", PASS, f"{elapsed:.1f}s for {size:,} bytes",
                     material=False)


def _rendered_by_script(html: str) -> Criterion:
    """Whether the page's content arrives from JavaScript this does not run.

    Reported and never counted as a failure — in fact it is evidence AGAINST an approach.
    An HTML shell plus a bundle means somebody built this with a modern framework, and
    telling them their site needs rebuilding would be the message that ends the
    conversation.
    """

    if not html:
        return Criterion("server-rendered", NOT_ASSESSED, "no HTML was read", material=False)
    body = _text_of(r"<body[^>]*>(.*?)</body>", html) or html
    words = len(re.sub(r"<[^>]+>", " ", body).split())
    scripts = len(re.findall(r"<script", body, re.IGNORECASE))
    if words < 40 and scripts:
        return Criterion(
            "server-rendered", NOT_ASSESSED,
            f"only {words} words of HTML with {scripts} script tag(s): the content is "
            f"rendered by JavaScript, which this does not run. Nothing about the page's "
            f"content was established — and a framework build is a reason NOT to approach.",
            material=False)
    return Criterion("server-rendered", PASS, f"{words} words in the HTML", material=False)


def check(
    url: str,
    *,
    opener: Callable[..., Any] | None = None,
    timeout: int = TIMEOUT,
    clock: Callable[[], float] = time.monotonic,
) -> SiteReport:
    """One request to one URL. Never raises, and never crawls.

    An HTTP error status is `ERRORED` and IS assessed — a 404 or a 500 on a business's own
    domain is a real, checkable finding and one of the strongest reasons to get in touch. A
    connection that never completed is `UNREACHABLE` and is assessed as nothing at all.
    """

    if not str(url).strip():
        return SiteReport(NO_URL, "", reason="no website address was supplied",
                          checked_at=_now())

    target = str(url).strip()
    if not target.lower().startswith(("http://", "https://")):
        target = f"https://{target}"

    request = urllib.request.Request(target, headers={
        "User-Agent": "Mozilla/5.0 (compatible; provena-outreach/1.0)",
        "Accept": "text/html,application/xhtml+xml",
    })
    started = clock()
    tls_error, http_status, final_url, raw = "", 0, target, b""

    try:
        with (opener or urllib.request.urlopen)(request, timeout=timeout) as response:
            http_status = int(getattr(response, "status", 0) or 200)
            final_url = str(getattr(response, "url", target) or target)
            raw = response.read(READ_LIMIT)
    except urllib.error.HTTPError as error:
        # A real answer from the site, and a useful one. 404 and 500 on somebody's own
        # domain is a finding, not a failure to look.
        http_status = int(error.code)
        final_url = str(getattr(error, "url", target) or target)
        try:
            raw = error.read(READ_LIMIT)
        except Exception:  # noqa: BLE001 - a body we cannot read is simply absent
            raw = b""
    except ssl.SSLError as error:
        tls_error = str(error)[:120]
    except Exception as error:  # noqa: BLE001
        return SiteReport(UNREACHABLE, target,
                          reason=f"{type(error).__name__}: {error}"[:160],
                          elapsed_seconds=clock() - started, checked_at=_now())

    elapsed = clock() - started

    if tls_error:
        # Reached far enough to learn something real about it, and no page to assess.
        return SiteReport(
            ERRORED, target, final_url=target, http_status=0,
            criteria=(_https(target, "", tls_error),
                      Criterion("mobile viewport", NOT_ASSESSED,
                                "the certificate stopped the page being fetched"),
                      Criterion("page title", NOT_ASSESSED,
                                "the certificate stopped the page being fetched")),
            elapsed_seconds=elapsed, checked_at=_now(),
            reason=f"TLS: {tls_error}")

    html = raw.decode("utf-8", errors="replace") if raw else ""
    title = _text_of(r"<title[^>]*>(.*?)</title>", html)

    criteria = [
        _https(target, final_url, ""),
        _parked(html, title),
        _viewport(html),
        _title(html),
        _contact(html),
        _speed(elapsed, len(raw)),
        _rendered_by_script(html),
    ]

    if http_status >= 400:
        criteria.insert(0, Criterion(
            "the site answers", FAIL,
            f"the address returns HTTP {http_status}. Anyone following a link, a listing "
            f"or a search result lands on an error page.",
            remedy="find out whether the site or the hosting has lapsed"))
        status = ERRORED
    else:
        criteria.insert(0, Criterion("the site answers", PASS,
                                     f"HTTP {http_status}"))
        status = REACHED

    return SiteReport(status, target, final_url, http_status, tuple(criteria),
                      elapsed, len(raw), _now())


def describe_checks(reports: Sequence[SiteReport]) -> str:
    """How many sites were actually looked at, kept apart from what was found."""

    assessed = [r for r in reports if r.assessed]
    unreached = [r for r in reports if r.status == UNREACHABLE]
    line = f"{len(assessed)} of {len(reports)} site(s) were actually assessed"
    if unreached:
        line += (f"; {len(unreached)} could not be reached and NOTHING is established "
                 f"about them")
    return line
