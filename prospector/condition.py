"""Fetching the site they already have, and handing it to the standard.

This file used to hold the checks as well. They live in `standard.py` now, because "what
is wrong with this site" turned out to be the question the whole tool rests on, and a list
of ad-hoc regexes buried in a fetcher is not a thing anybody can agree to or argue with.
What is left here is the part that is genuinely about fetching: how many attempts before a
failure is a fact, what a 403 to an automated request means, and how to tell whether the
same site answers over HTTPS.

## What a single failed fetch means

Nothing, on its own. A site that times out once has not been shown to be down, and "your
website is offline" is the most embarrassing sentence in an outreach note when it is wrong.
Unreachability requires the same failure twice, with a gap; anything less is not a finding.

## A 403 grades the checker, not the site

Cloudflare and its relatives answer an unknown user agent with a challenge. A page that
refuses to talk to this fetcher may be perfectly good for a person with a browser, so it is
`UNDETERMINED` and does not surface. The alternative is a tool that preferentially
approaches businesses whose sites are well defended, which is exactly backwards.
"""
from __future__ import annotations

import re
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Sequence

from prospector import standard

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
    #: Every criterion in the standard, met or failed or not assessed. The findings above
    #: are the failures; this is the whole picture, and it is what the dossier records so
    #: a person can see what was checked rather than only what was wrong.
    report: Any = None

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
    """Fetch the site, run the standard over it, and report what it fails."""

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
            report = standard.assess("", url=url, reached=False, status=None,
                                     https_available=None, byte_size=0)
            detail = ("the domain does not resolve at all, on two attempts — the "
                      "registration may have lapsed") if unresolved else (
                      f"two attempts, both failed: {second.error}")
            code = "DOMAIN_DOES_NOT_RESOLVE" if unresolved else "UNREACHABLE"
            return Condition(DEFICIENT, url=url, report=report,
                             findings=(Finding(code, DEFECT, detail),))
        first = second

    status = first.status or 0
    if status in (403, 429):
        return Condition(UNDETERMINED, url=url, http_status=status,
                         reason=f"the site answered HTTP {status} to an automated request; "
                                f"a person opening it in a browser may see a working site")

    report = standard.assess(first.body or "", url=url, status=status, reached=True,
                             https_available=_https_available(url, fetcher),
                             byte_size=len(first.body or ""))
    findings = tuple(
        Finding(assessment.code,
                DEFECT if assessment.tier in standard.APPROACHABLE_TIERS else OBSERVATION,
                f"{assessment.criterion.title} — {assessment.detail}")
        for assessment in report.failures())
    if report.blocked and not report.approachable_failures:
        # Something that decides the verdict could not be evaluated, and nothing that could
        # be evaluated failed. That is not a site in good order; it is a site nobody looked
        # at properly.
        unknown = ", ".join(a.code for a in report.by_state(standard.NOT_ASSESSED)
                            if a.tier in standard.APPROACHABLE_TIERS)
        return Condition(UNDETERMINED, url=url, http_status=status, report=report,
                         findings=findings, final_url=first.final_url,
                         reason=f"these criteria could not be evaluated: {unknown}")
    verdict = DEFICIENT if report.approachable_failures else SERVICEABLE
    return Condition(verdict, url=url, findings=findings, http_status=status,
                     final_url=first.final_url, report=report)
