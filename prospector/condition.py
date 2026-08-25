"""What is wrong with the site they already have — as named, checkable defects, never a
score.

The temptation here is a number: page weight, mobile, HTTPS, freshness, accessibility,
summed out of a hundred, with a threshold above which a business becomes a prospect. The
parent repository argues at length why that is a category error, and the argument does not
weaken by moving domain. Two of its points land especially hard here.

**A weighted sum treats a disqualifier as a deduction.** A site that does not load at all
is not "scoring poorly on availability"; it is the only finding that matters, and any
scheme that lets four good dimensions carry it past a threshold will eventually send a
polite note about mobile layout to a business whose domain has expired.

**And an unmeasured dimension has no honest score.** A page that timed out has no mobile
verdict, no HTTPS verdict and no content verdict. Scored as zero it manufactures four
defects out of one failure; dropped from the average it *raises* the total, because less
was looked at.

So: named findings, each one independently checkable by the recipient, and a verdict that
is one of three things. `SERVICEABLE` is worded to avoid implying praise — there is no
machine-checkable definition of a good website, and this module does not have a view on
whether a site is good. It has a view on whether a specific, stated defect is present.

## What a single failed fetch means

Nothing, on its own. A site that times out once has not been shown to be down, and
"your website is offline" is the most embarrassing sentence in an outreach note when it is
wrong. A defect of unreachability requires the same failure twice, with a gap; anything
less is `UNDETERMINED`, which does not surface.
"""
from __future__ import annotations

import re
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Sequence

from prospector.states import DEFICIENT, SERVICEABLE, UNDETERMINED

def _this_year() -> int:
    return datetime.now(timezone.utc).year


USER_AGENT = ("Mozilla/5.0 (compatible; prospector/0.1; +site condition check; "
              "contact via the sender of this report)")

#: Read at most this much of a page. A condition check does not need the whole of a
#: 40 MB hero video, and an unbounded read is how a check on one bad site stalls a county.
MAX_BYTES = 512 * 1024
TIMEOUT = 15.0

#: Severity. An observation is true, worth telling a person, and not a reason to pitch.
DEFECT = "DEFECT"
OBSERVATION = "OBSERVATION"

_PARKED_PHRASES = (
    "this domain is for sale", "buy this domain", "domain for sale",
    "parked free, courtesy of", "this site is under construction",
    "under construction", "coming soon", "default web page", "welcome to nginx",
    "apache2 ubuntu default page", "future home of something quite cool",
    "account suspended", "index of /",
)


@dataclass(frozen=True, slots=True)
class Finding:
    """One named, checkable thing about the page."""

    code: str
    severity: str
    detail: str


@dataclass(frozen=True, slots=True)
class Condition:
    """The verdict on one site, and every finding behind it."""

    status: str
    url: str = ""
    findings: tuple[Finding, ...] = ()
    reason: str = ""
    final_url: str = ""
    http_status: int | None = None

    @property
    def defects(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.severity == DEFECT)

    def describe(self) -> str:
        if self.status == UNDETERMINED:
            return (f"UNDETERMINED  {self.url}\n  {self.reason}\n"
                    f"  The page was not assessed. It is not therefore fine, and it is not "
                    f"therefore broken.")
        head = f"{self.status}  {self.url}"
        if not self.findings:
            return head + "\n  no named defect was found. That is not a verdict that the " \
                          "site is good."
        lines = [head]
        for finding in self.findings:
            lines.append(f"  {finding.severity:11} {finding.code}: {finding.detail}")
        return "\n".join(lines)


class _Page(HTMLParser):
    """Just enough of the document to check the things worth checking, from the stdlib.

    A parser dependency would be the fifth thing on a list of dependencies this package is
    trying not to have. `html.parser` handles real-world tag soup adequately for asking
    'is there a viewport meta tag' and 'how much text is on this page'.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.viewport = False
        self.title = ""
        self.text_chars = 0
        self.image_count = 0
        self.link_hosts: set[str] = set()
        self._in_title = False
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "meta" and (values.get("name") or "").lower() == "viewport":
            self.viewport = True
        elif tag == "title":
            self._in_title = True
        elif tag == "img":
            self.image_count += 1
        elif tag in ("script", "style"):
            self._skip += 1
        elif tag == "a":
            href = (values.get("href") or "").lower()
            match = re.match(r"https?://([^/]+)/?", href)
            if match:
                self.link_hosts.add(match.group(1))

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag in ("script", "style") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if self._in_title:
            self.title += data.strip()
        elif not self._skip:
            self.text_chars += len(data.strip())


@dataclass(frozen=True, slots=True)
class Fetch:
    """One attempt at one URL."""

    ok: bool
    body: str = ""
    status: int | None = None
    final_url: str = ""
    error: str = ""
    scheme: str = ""


def fetch(url: str, *, timeout: float = TIMEOUT) -> Fetch:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                                   "Accept": "text/html,*/*"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(MAX_BYTES)
            charset = response.headers.get_content_charset() or "utf-8"
            final = response.geturl()
            return Fetch(True, raw.decode(charset, errors="replace"), response.status,
                         final, scheme=final.split(":", 1)[0])
    except urllib.error.HTTPError as exc:
        # A 4xx or 5xx is an answer, not a failure to look. It is graded below.
        body = ""
        try:
            body = exc.read(MAX_BYTES).decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001 - the body is a nicety; the status is the fact
            pass
        return Fetch(True, body, exc.code, url, scheme=url.split(":", 1)[0])
    except (urllib.error.URLError, ssl.SSLError, TimeoutError, OSError, ValueError) as exc:
        return Fetch(False, error=repr(exc), scheme=url.split(":", 1)[0])


def _https_available(url: str, fetcher) -> bool | None:
    """Whether the same site answers over HTTPS. `None` when that could not be told."""

    if url.lower().startswith("https://"):
        return True
    attempt = fetcher("https://" + url.split("://", 1)[-1])
    if not attempt.ok:
        return None if "timed out" in attempt.error.lower() else False
    return attempt.status is not None and attempt.status < 400


def assess(url: str, *, fetcher=fetch, retry_pause: float = 2.0) -> Condition:
    """Fetch the site and name what is wrong with it, or say it could not be assessed."""

    if not url or "://" not in url:
        return Condition(UNDETERMINED, url=url, reason="not a URL this checker can fetch")

    first = fetcher(url)
    if not first.ok:
        # One failure proves nothing. A second, after a pause, is a finding.
        if retry_pause:
            time.sleep(retry_pause)
        second = fetcher(url)
        if not second.ok:
            # A name that does not resolve is a different fact from a connection that
            # fails, and the difference is the strongest signal this checker produces: a
            # domain listed on the map whose DNS is gone is usually a lapsed registration,
            # which is a business that has lost its website without necessarily knowing.
            unresolved = "gaierror" in second.error or "not known" in second.error
            code = "DOMAIN_DOES_NOT_RESOLVE" if unresolved else "UNREACHABLE"
            detail = ("the domain does not resolve at all, on two attempts — the "
                      "registration may have lapsed") if unresolved else (
                      f"two attempts, both failed: {second.error}")
            return Condition(DEFICIENT, url=url,
                             findings=(Finding(code, DEFECT, detail),))
        first = second

    findings: list[Finding] = []
    status = first.status or 0
    if status >= 500:
        return Condition(DEFICIENT, url=url, http_status=status, final_url=first.final_url,
                         findings=(Finding("SERVER_ERROR", DEFECT,
                                           f"the site answered HTTP {status}"),))
    if status in (403, 429):
        # Being refused by a bot defence says nothing about the site's quality, and a
        # cascade that graded it would be grading its own user agent.
        return Condition(UNDETERMINED, url=url, http_status=status,
                         reason=f"the site answered HTTP {status} to an automated request; "
                                f"a person opening it in a browser may see a working site")
    if status >= 400:
        findings.append(Finding("NOT_FOUND", DEFECT,
                                f"the listed address answered HTTP {status}"))

    body = first.body or ""
    lowered = body.lower()
    if not body.strip():
        findings.append(Finding("EMPTY_PAGE", DEFECT, "the page returned no content"))
    for phrase in _PARKED_PHRASES:
        if phrase in lowered:
            findings.append(Finding("PLACEHOLDER", DEFECT,
                                    f"the page reads as a placeholder: {phrase!r}"))
            break

    page = _Page()
    try:
        page.feed(body)
    except Exception as exc:  # noqa: BLE001 - malformed markup is a finding, not a crash
        findings.append(Finding("MALFORMED", OBSERVATION, f"the markup would not parse: {exc!r}"))

    if body and not page.viewport:
        findings.append(Finding("NO_MOBILE_VIEWPORT", DEFECT,
                                "no viewport meta tag, so the page is served to phones at "
                                "desktop width"))
    https = _https_available(url, fetcher)
    if https is False:
        findings.append(Finding("NO_HTTPS", DEFECT,
                                "the site does not answer over HTTPS, so browsers mark it "
                                "'Not secure'"))
    elif https is None:
        findings.append(Finding("HTTPS_UNKNOWN", OBSERVATION,
                                "whether the site supports HTTPS could not be established"))
    # Guarded on there being nothing else, because a 404 page and a placeholder page are
    # also short, and reporting three findings for one fault reads as three faults.
    if body and page.text_chars < 200 and not findings:
        findings.append(Finding("ALMOST_NO_CONTENT", DEFECT,
                                f"only {page.text_chars} characters of text on the page"))
    # The LATEST year in any copyright notice, not the first. A footer reading
    # "© 2001-2026" starts with a year that means nothing; taking it as the site's age
    # would flag every well-maintained site on the internet, which is the sort of finding
    # that trains a reader to stop reading findings.
    years: list[int] = []
    for notice in re.finditer(r"(?:©|&copy;|copyright)", lowered):
        window = lowered[notice.start():notice.start() + 60]
        years += [int(y) for y in re.findall(r"(?:19|20)\d{2}", window)]
    if years:
        latest = max(years)
        if latest < _this_year() - 1:
            findings.append(Finding("DATED_NOTICE", OBSERVATION,
                                    f"the newest copyright year on the page is {latest}"))
    if not page.title.strip() and body:
        findings.append(Finding("NO_TITLE", DEFECT,
                                "the page has no <title>, so it appears in search results "
                                "and browser tabs with no name"))

    verdict = DEFICIENT if any(f.severity == DEFECT for f in findings) else SERVICEABLE
    return Condition(verdict, url=url, findings=tuple(findings), http_status=status,
                     final_url=first.final_url)
