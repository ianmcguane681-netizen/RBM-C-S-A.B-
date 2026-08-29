"""Which businesses are worth approaching about a website, and what may be said to them.

Two halves, and the second is the one that needs the arguing.

**The first half is evidence.** A prospect is a business plus what was actually measured
about its web presence, and the verdict is a cascade in the shape `lib/candidates.py`
argues for: ordered, first refusal decisive, nothing averaged. `NO_SITE_FOUND`,
`NEEDS_WORK`, `ADEQUATE`, `NOT_ESTABLISHED` — and the last is not a filler. An OSM record
with no website tag and a site that timed out both leave this system knowing nothing, and a
lane that reported those as "no website" would send somebody an approach that opens by
telling a business something false about itself.

**The second half is whether it may be sent at all**, and that is a different kind of gate
from anything else in this repository. Every other lane's constraint is losing money; this
one's is doing something to a person who did not ask. So there is a `Contactability` check
before any draft exists, and it refuses more often than it permits:

    a company address, published by the business, for business purposes   PERMITTED
    an address that looks like a named individual's                        REFUSED
    a suppression-list entry                                               REFUSED
    approached before, inside the cooldown                                 REFUSED
    no evidence at all about the site                                      REFUSED

The individual-address rule is a real legal line and not a courtesy. Under Irish and UK
implementations of the ePrivacy rules, unsolicited electronic marketing to a corporate
subscriber is permitted with an identified sender and a working opt-out; to an individual
subscriber — a sole trader, a partnership, a personal address — it is not, without prior
consent. `firstname@` and a free-mail domain are the signals available here, they are
imperfect, and the direction of the imperfection is chosen deliberately: this refuses cases
it is unsure about. **None of this is legal advice and the file does not pretend to be it**
— it is a conservative reading, and a person who wants to approach a refused prospect can
do so knowing that they, not this, made the call.

**And nothing here sends anything.** `Approach` is a drafted message with an address on it.
There is no SMTP client, no API key path and no send method in this module or anywhere near
it, for the same structural reason `connectors/chain_exec.py` cannot sign: the deliverable
is the draft, and a person presses send. Do not add one.

## What the draft may claim

Only what was measured, and the module enforces it. A draft built from a report where the
site was never reached carries no claim about the site; a draft built from an OSM record
with no website tag says "I could not find a website for you" and never "you have no
website". The difference is the whole credibility of the approach: the recipient knows
whether they have a website, and an opening line that is wrong about it is the end of the
conversation and a fair reason for them to be annoyed.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from lib.candidates import INDETERMINATE, PASSED, REFUSED, Candidate, Stage

# What was established about this business's web presence.
NO_SITE_FOUND = "NO_SITE_FOUND"
NEEDS_WORK = "NEEDS_WORK"
ADEQUATE = "ADEQUATE"
NOT_ESTABLISHED = "NOT_ESTABLISHED"

# Whether an approach may be drafted and sent.
PERMITTED = "PERMITTED"
NOT_PERMITTED = "NOT_PERMITTED"

#: How long before the same business may be approached again. Long on purpose: a second
#: message six weeks after the first is a follow-up, and a second message six months after
#: the first is a stranger who did not remember writing.
COOLDOWN_DAYS = 180

#: Free-mail domains. An address here is almost always a person's rather than a company's,
#: which is the line the ePrivacy rules draw — so these are refused by default rather than
#: approached and apologised for.
PERSONAL_DOMAINS = frozenset({
    "gmail.com", "googlemail.com", "hotmail.com", "hotmail.co.uk", "outlook.com",
    "live.com", "live.ie", "yahoo.com", "yahoo.co.uk", "yahoo.ie", "aol.com",
    "icloud.com", "me.com", "eircom.net", "btinternet.com", "sky.com", "protonmail.com",
})

#: Mailbox names that mean an address belongs to a role rather than a person. The safe
#: side of the corporate/individual line, and the list is short because a name that is not
#: obviously a role is treated as a person's.
ROLE_MAILBOXES = frozenset({
    "info", "hello", "contact", "enquiries", "enquiry", "office", "admin", "sales",
    "bookings", "reception", "mail", "shop", "orders", "support", "accounts", "team",
})

#: Where businesses that have asked not to be contacted are kept. Consulted before every
#: draft and never expires — a suppression that lapsed after a year would be a system that
#: eventually ignores somebody who already said no.
SUPPRESSION = Path("data/outreach-suppression.json")

#: What a person found when they went and looked for a business's website. The bridge
#: between "OSM has no tag" and "this business has no website", which nothing here can
#: cross on its own — see `SearchLog`.
SEARCHES = Path("data/outreach-searches.json")

#: The record of who has been approached and when. Not the seen register: that records what
#: was SURFACED to the operator, and this records what was SENT to a third party. Merging
#: them would let a prospect that was merely looked at count as one that was written to.
APPROACHES = Path("data/outreach-approaches.json")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, AttributeError, TypeError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _stamp(moment: datetime | None = None) -> str:
    return (moment or _now()).isoformat(timespec="seconds").replace("+00:00", "Z")


# --- who may be written to -------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Contactability:
    """Whether this business may be approached, and the reason either way.

    Reason on a PERMITTED as well as a refusal. An approach that goes out has a record of
    why it was allowed to, which is what makes a complaint answerable six months later with
    something better than "the system thought it was fine".
    """

    status: str
    channel: str
    address: str
    reason: str

    @property
    def permitted(self) -> bool:
        return self.status == PERMITTED

    def describe(self) -> str:
        return f"{self.status} via {self.channel or 'no channel'}: {self.reason}"


def looks_like_an_individual(email: str) -> tuple[bool, str]:
    """Whether this address looks like a person's rather than a company's, and why.

    Imperfect, and the imperfection runs one way on purpose. `paul@paulsplumbing.ie` is a
    sole trader's own address on his own domain and this treats it as an individual's; that
    will refuse some approaches that would have been lawful. The opposite error sends
    unsolicited mail to a person who is entitled not to receive it, and the two are not
    symmetrical.
    """

    address = str(email).strip().lower()
    mailbox, _, domain = address.partition("@")
    if not mailbox or not domain:
        return True, "the address could not be read as an address at all"
    if domain in PERSONAL_DOMAINS:
        return True, (f"{domain} is a personal mail provider, so the subscriber is an "
                      f"individual rather than a corporate one")
    if mailbox in ROLE_MAILBOXES:
        return False, f"{mailbox}@ is a role address rather than a named person's"
    if re.fullmatch(r"[a-z]+", mailbox) or re.fullmatch(r"[a-z]+[._-][a-z]+", mailbox):
        return True, (f"{mailbox}@ reads as a person's name rather than a role. Refused "
                      f"because the individual/corporate line is where the rules sit and "
                      f"this cannot tell which side of it a first name is on")
    return False, f"{mailbox}@ does not read as an individual's mailbox"


class SuppressionList:
    """Businesses that have asked not to be contacted. Consulted before every draft.

    An unreadable list REFUSES everything, which is the opposite of how the seen register
    behaves and is right here for the reason the whole file turns on: the cost of a missed
    approach is one email nobody sent, and the cost of a missed suppression is writing again
    to somebody who already said no.
    """

    def __init__(self, path: str | Path, *, readable: bool = True, reason: str = "") -> None:
        self.path = Path(path)
        self.readable = readable
        self.reason = reason
        self.entries: dict[str, dict] = {}

    @classmethod
    def load(cls, path: str | Path) -> "SuppressionList":
        listing = cls(path)
        if not listing.path.is_file():
            return listing
        try:
            rows = json.loads(listing.path.read_text(encoding="utf-8"))
            for row in rows:
                key = str(row["key"]).strip().lower()
                listing.entries[key] = dict(row)
        except (OSError, ValueError, TypeError, KeyError) as error:
            return cls(path, readable=False,
                       reason=f"{type(error).__name__}: {error}"[:140])
        return listing

    def suppressed(self, *keys: str) -> tuple[bool, str]:
        if not self.readable:
            return True, (f"the suppression list could not be read ({self.reason}). "
                          f"Nothing may be sent while it is unknown who has asked not to "
                          f"be — an unreadable list is not an empty one")
        for key in keys:
            entry = self.entries.get(str(key).strip().lower())
            if entry:
                return True, (f"{key} is on the suppression list "
                              f"({entry.get('reason', 'no reason recorded')}, added "
                              f"{entry.get('added_at', 'undated')})")
        return False, ""

    def add(self, key: str, reason: str, *, when: str = "") -> None:
        if not self.readable:
            raise RuntimeError(
                "refusing to write a suppression list that could not be read: saving "
                "would drop everybody who has already asked not to be contacted")
        self.entries[str(key).strip().lower()] = {
            "key": str(key).strip(), "reason": reason, "added_at": when or _stamp()}

    def save(self) -> None:
        if not self.readable:
            raise RuntimeError("refusing to overwrite an unreadable suppression list")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        rows = [self.entries[key] for key in sorted(self.entries)]
        self.path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")


class SearchLog:
    """What a person found when they went and looked for a business online.

    The bridge this lane could not otherwise cross. `connectors/directory` can say
    OpenStreetMap has no website tag, and that is a lead rather than a finding — no free
    search API exists to turn it into one, and a scraped search page would be both against
    the terms and wrong often enough to matter.

    So a person searches, takes thirty seconds, and records one of two things: a URL, which
    the site checker then assesses, or that they looked and found nothing, which IS a
    finding and unlocks a draft. `checked_by` is a named human for the same reason
    `lib.rulebook.Clause` requires one: nothing in this repository can establish it, so an
    entry attributed to a machine would be an entry nobody made.

    A record goes STALE, because a business that had no website in March may have one now
    and an approach opening on a six-month-old search is the embarrassing kind of wrong.
    """

    #: How long a search stands before it must be done again.
    STALE_AFTER_DAYS = 90

    def __init__(self, path: str | Path, *, readable: bool = True, reason: str = "") -> None:
        self.path = Path(path)
        self.readable = readable
        self.reason = reason
        self.entries: dict[str, dict] = {}

    @classmethod
    def load(cls, path: str | Path) -> "SearchLog":
        log = cls(path)
        if not log.path.is_file():
            return log
        try:
            rows = json.loads(log.path.read_text(encoding="utf-8"))
            for row in rows:
                log.entries[str(row["key"]).strip().lower()] = dict(row)
        except (OSError, ValueError, TypeError, KeyError) as error:
            return cls(path, readable=False,
                       reason=f"{type(error).__name__}: {error}"[:140])
        return log

    def find(self, key: str, *, now: datetime | None = None) -> tuple[str, str, str]:
        """`(status, website, detail)` where status is FOUND, NONE_FOUND or UNSEARCHED.

        Three values because they lead three different places: a URL to check, a finding
        that unlocks a draft, and an errand for a person. An unreadable log answers
        UNSEARCHED for everything, which blocks — the safe direction here, since the thing
        being unlocked is a message to a stranger.
        """

        if not self.readable:
            return "UNSEARCHED", "", (
                f"the search log could not be read ({self.reason}), so whether anybody has "
                f"looked for this business online is unknown")
        entry = self.entries.get(str(key).strip().lower())
        if not entry:
            return "UNSEARCHED", "", "nobody has searched for this business online"

        when = _parse(str(entry.get("checked_at", "")))
        if when is None:
            return "UNSEARCHED", "", "a search is recorded with an unreadable date"
        age = ((now or _now()) - when).days
        if age > self.STALE_AFTER_DAYS:
            return "UNSEARCHED", "", (
                f"the last search was {age} days ago, over the "
                f"{self.STALE_AFTER_DAYS}-day limit. A business with no website in March "
                f"may have one now, and an approach resting on that is the embarrassing "
                f"kind of wrong")

        website = str(entry.get("website") or "").strip()
        who = entry.get("checked_by", "somebody")
        if website:
            return "FOUND", website, f"{who} found {website} on {entry.get('checked_at')}"
        return "NONE_FOUND", "", (
            f"{who} searched on {entry.get('checked_at')} and found no website")

    def record(self, key: str, *, website: str, checked_by: str, when: str = "") -> None:
        """Note what a person found. Refuses an automation-attributed search."""

        from lib.thesis import AUTOMATION_PREFIXES

        if not self.readable:
            raise RuntimeError(
                "refusing to write a search log that could not be read: saving would "
                "discard every search somebody has already done")
        who = str(checked_by).strip()
        if not who or any(who.lower().startswith(p) for p in AUTOMATION_PREFIXES):
            raise ValueError(
                f"{checked_by!r} cannot be named as having searched for a business. "
                f"Nothing in this repository can search the web, so this can only be the "
                f"record of a person doing it — and a machine-attributed search would "
                f"unlock a message to a stranger that nobody actually checked")
        self.entries[str(key).strip().lower()] = {
            "key": str(key).strip(), "website": str(website).strip(),
            "checked_by": who, "checked_at": when or _stamp()}

    def save(self) -> None:
        if not self.readable:
            raise RuntimeError("refusing to overwrite an unreadable search log")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        rows = [self.entries[key] for key in sorted(self.entries)]
        self.path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")


class ApproachLog:
    """Who has been written to and when. Separate from the seen register, deliberately.

    `lib/seen.py` records what was SURFACED to the operator. This records what was SENT to
    a third party. They look alike and they answer different questions, and one register
    doing both would let a prospect that was merely looked at count as one that has already
    had a message — or, far worse, the other way round.
    """

    def __init__(self, path: str | Path, *, readable: bool = True, reason: str = "") -> None:
        self.path = Path(path)
        self.readable = readable
        self.reason = reason
        self.entries: dict[str, dict] = {}

    @classmethod
    def load(cls, path: str | Path) -> "ApproachLog":
        log = cls(path)
        if not log.path.is_file():
            return log
        try:
            rows = json.loads(log.path.read_text(encoding="utf-8"))
            for row in rows:
                log.entries[str(row["key"]).strip().lower()] = dict(row)
        except (OSError, ValueError, TypeError, KeyError) as error:
            return cls(path, readable=False,
                       reason=f"{type(error).__name__}: {error}"[:140])
        return log

    def recently_approached(self, key: str, *, cooldown_days: int = COOLDOWN_DAYS,
                            now: datetime | None = None) -> tuple[bool, str]:
        if not self.readable:
            return True, (f"the approach log could not be read ({self.reason}), so whether "
                          f"this business has already been written to is unknown. An "
                          f"unknown is not a no")
        entry = self.entries.get(str(key).strip().lower())
        if not entry:
            return False, ""
        when = _parse(str(entry.get("approached_at", "")))
        if when is None:
            return True, "a previous approach is recorded with an unreadable date"
        age = ((now or _now()) - when).days
        if age <= cooldown_days:
            return True, (f"approached {age} day(s) ago, inside the {cooldown_days}-day "
                          f"cooldown. A second message six months after the first is a "
                          f"stranger who did not remember writing")
        return False, ""

    def record(self, key: str, subject: str, *, when: str = "") -> None:
        if not self.readable:
            raise RuntimeError(
                "refusing to write an approach log that could not be read: saving would "
                "lose every record of who has already been contacted")
        self.entries[str(key).strip().lower()] = {
            "key": str(key).strip(), "subject": subject,
            "approached_at": when or _stamp()}

    def save(self) -> None:
        if not self.readable:
            raise RuntimeError("refusing to overwrite an unreadable approach log")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        rows = [self.entries[key] for key in sorted(self.entries)]
        self.path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")


def contactability(
    business: Any,
    *,
    suppression: SuppressionList | None = None,
    log: ApproachLog | None = None,
    cooldown_days: int = COOLDOWN_DAYS,
    now: datetime | None = None,
) -> Contactability:
    """Whether a message may be drafted for this business at all, before any is.

    Ordered cheapest and most decisive first. Suppression outranks everything: somebody who
    has said no has said no, and no amount of evidence about their website changes it.
    """

    key = str(getattr(business, "osm_id", "") or getattr(business, "name", ""))
    email = str(getattr(business, "email", "") or "")
    phone = str(getattr(business, "phone", "") or "")

    listing = suppression if suppression is not None else SuppressionList.load(SUPPRESSION)
    blocked, why = listing.suppressed(key, email, str(getattr(business, "name", "")))
    if blocked:
        return Contactability(NOT_PERMITTED, "", email or phone, why)

    history = log if log is not None else ApproachLog.load(APPROACHES)
    approached, why = history.recently_approached(key, cooldown_days=cooldown_days, now=now)
    if approached:
        return Contactability(NOT_PERMITTED, "", email or phone, why)

    if email:
        individual, why = looks_like_an_individual(email)
        if individual:
            return Contactability(NOT_PERMITTED, "email", email, (
                f"{why}. Unsolicited electronic marketing to an individual subscriber "
                f"needs prior consent, where to a corporate one it needs an identified "
                f"sender and a working opt-out. This is a conservative reading and not "
                f"legal advice — approach by another route, or decide for yourself"))
        return Contactability(PERMITTED, "email", email, (
            f"{why}, published by the business for business contact. The draft must "
            f"identify the sender and carry an opt-out"))

    if phone:
        return Contactability(PERMITTED, "phone", phone, (
            "no email is published, and a published business phone number may be rung. A "
            "call is a conversation rather than a broadcast, which is also why the draft "
            "for this channel is notes rather than a script"))

    return Contactability(NOT_PERMITTED, "", "", (
        "no published contact details at all. Turning up in person or finding an address "
        "elsewhere is a decision for a person, not something to automate from a map"))


# --- what was established about the site -----------------------------------------------

@dataclass(frozen=True, slots=True)
class Prospect:
    """One business, what is known about its web presence, and whether it may be written to.

    `verdict` comes from the cascade rather than from a count of failures. A site that could
    not be reached has NOT_ESTABLISHED and never NEEDS_WORK, because the second is a claim
    about somebody's website and the first is a claim about a request.
    """

    business: Any
    site: Any = None
    stages: tuple[Stage, ...] = ()
    contact: Contactability | None = None

    @property
    def name(self) -> str:
        return str(getattr(self.business, "name", "") or "(unnamed)")

    @property
    def key(self) -> str:
        return str(getattr(self.business, "osm_id", "") or self.name)

    @property
    def verdict(self) -> str:
        return Candidate(self.name, self.stages).verdict

    @property
    def finding(self) -> str:
        """What was established, in this module's own vocabulary rather than the cascade's.

        Kept separate because the cascade answers "should this be surfaced" and this
        answers "what is true", and they are not the same question: an ADEQUATE site is a
        real finding and a perfectly good reason not to write to anybody.
        """

        if not self.stages:
            return NOT_ESTABLISHED
        decided = Candidate(self.name, self.stages).decided_by
        if decided is not None and decided.verdict == INDETERMINATE:
            return NOT_ESTABLISHED
        if decided is not None and decided.verdict == REFUSED:
            return ADEQUATE
        if self.site is None or not getattr(self.site, "assessed", False):
            return NO_SITE_FOUND
        return NEEDS_WORK

    @property
    def material_failures(self) -> tuple[Any, ...]:
        return tuple(getattr(self.site, "material_failures", ()) or ())

    def describe(self) -> str:
        lines = [f"{self.finding}  {self.name}"]
        lines += [f"  {line}" for line in
                  str(getattr(self.business, "describe", lambda: "")()).splitlines()]
        lines += [f"  {line}" for stage in self.stages
                  for line in stage.describe().splitlines()]
        if self.contact is not None:
            lines.append(f"  CONTACT: {self.contact.describe()}")
        return "\n".join(lines)


def assess(
    business: Any,
    site: Any = None,
    *,
    suppression: SuppressionList | None = None,
    log: ApproachLog | None = None,
    searches: SearchLog | None = None,
    cooldown_days: int = COOLDOWN_DAYS,
    now: datetime | None = None,
) -> Prospect:
    """A business and its site report into a prospect, with every absence kept as one.

    `site=None` means nobody fetched a page, which is the ordinary case for a business
    whose OSM record carries no website tag. What decides the finding then is the SEARCH
    log: OSM's silence is a lead, and only a person who went and looked turns it into
    `NO_SITE_FOUND`.
    """

    stages: list[Stage] = []
    from connectors.directory import SITE_TAGGED

    tagged = getattr(business, "website_status", "") == SITE_TAGGED
    key = str(getattr(business, "osm_id", "") or getattr(business, "name", ""))
    searched, found_url, search_detail = (
        (searches or SearchLog.load(SEARCHES)).find(key, now=now))

    if site is None and not tagged and searched == "NONE_FOUND":
        # The one path by which an absent OSM tag becomes a finding: a named person looked.
        stages.append(Stage(
            "is there a website", PASSED, disqualifying=True,
            detail=(f"{search_detail}. OpenStreetMap's silence was a lead; this is the "
                    f"record of somebody converting it into a finding."),
        ))
    elif site is None and not tagged and searched == "FOUND":
        stages.append(Stage(
            "is there a website", INDETERMINATE, disqualifying=True,
            detail=(f"{search_detail}, and that site has not been checked. Point the site "
                    f"checker at {found_url} before saying anything about it."),
        ))
    elif site is None and not tagged:
        stages.append(Stage(
            "is there a website", INDETERMINATE, disqualifying=True,
            detail=("OpenStreetMap records no website for this business, and " +
                    search_detail + ". OSM's coverage of attributes is far worse than its "
                    "coverage of premises, so this is a lead worth thirty seconds of a "
                    "search engine — not a finding that no website exists. Record what "
                    "you find with `python outreach.py --searched`."),
        ))
    elif site is None:
        stages.append(Stage(
            "is there a website", INDETERMINATE, disqualifying=True,
            detail=(f"a website is recorded ({getattr(business, 'website', '')}) and it "
                    f"was not checked. Nothing about it has been established."),
        ))
    elif not getattr(site, "assessed", False):
        stages.append(Stage(
            "is there a website", INDETERMINATE, disqualifying=True,
            detail=(f"the recorded address was not reached: "
                    f"{getattr(site, 'reason', 'no reason recorded')}. That is an "
                    f"unanswered request, not a bad website, and a business must never be "
                    f"told otherwise."),
        ))
    else:
        stages.append(Stage("is there a website", PASSED, disqualifying=True,
                            detail=f"{getattr(site, 'url', '')} answered and was assessed"))

        failures = tuple(getattr(site, "material_failures", ()) or ())
        if not failures:
            unassessed = tuple(getattr(site, "unassessed", ()) or ())
            stages.append(Stage(
                "does it need work", REFUSED, disqualifying=True,
                detail=("every material criterion passed"
                        + (f", and {len(unassessed)} could not be assessed"
                           if unassessed else "")
                        + ". There is nothing to tell this business that they do not "
                          "already know, and an approach without one is a nuisance."),
            ))
        else:
            stages.append(Stage(
                "does it need work", PASSED, disqualifying=True,
                detail=("; ".join(f.name for f in failures)
                        + f" — {len(failures)} measured failure(s), each with a remedy"),
            ))

    contact = contactability(business, suppression=suppression, log=log,
                             cooldown_days=cooldown_days, now=now)
    if not contact.permitted:
        stages.append(Stage("may they be contacted", REFUSED, disqualifying=True,
                            detail=contact.reason))
    else:
        stages.append(Stage("may they be contacted", PASSED, disqualifying=True,
                            detail=contact.reason))

    return Prospect(business, site, tuple(stages), contact)


# --- the draft ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Approach:
    """A message somebody may send, and the evidence every sentence of it rests on.

    NOT SENT. There is no SMTP client in this repository and no key path for one, the same
    way `connectors/chain_exec.py` has no signing library — the deliverable is the draft,
    and a person presses send. Do not add one.
    """

    key: str
    business: str
    channel: str
    address: str
    subject: str
    body: str
    claims: tuple[str, ...] = ()
    drafted_at: str = field(default_factory=_stamp)

    def describe(self) -> str:
        return "\n".join([
            f"DRAFT — NOT SENT.  {self.business}  via {self.channel} to {self.address}",
            f"  subject: {self.subject}",
            "",
            *(f"  {line}" for line in self.body.splitlines()),
            "",
            "  Every claim above rests on:",
            *(f"    - {claim}" for claim in self.claims),
            "",
            "  Nothing has been sent. Read it, change it to sound like you, and send it "
            "yourself.",
        ])


def draft(
    prospect: Prospect,
    *,
    sender: str,
    sender_detail: str,
    opt_out: str = "",
) -> Approach | str:
    """A message, or a string saying why there is not one. Never a message on thin evidence.

    `sender` and `sender_detail` are mandatory: an unsolicited business message must
    identify who is sending it, and a draft that left that to be filled in later is a draft
    that goes out with a placeholder in it.

    The returned string on refusal is deliberate rather than an exception — a lane drafting
    forty approaches must be able to report the ones it would not write, and why.
    """

    if not sender.strip() or not sender_detail.strip():
        return ("no sender is named. An unsolicited business message must identify who is "
                "sending it, and this will not draft one that cannot")
    if prospect.contact is None or not prospect.contact.permitted:
        return (prospect.contact.reason if prospect.contact is not None
                else "contactability was never established")
    if prospect.finding == NOT_ESTABLISHED:
        return ("nothing was established about this business's website, so there is no "
                "claim that could honestly be made. Check by hand first")
    if prospect.finding == ADEQUATE:
        return ("the site was assessed and every material criterion passed. There is "
                "nothing to say")

    name = prospect.name
    channel = prospect.contact.channel
    opt_out = opt_out.strip() or (
        "If you would rather I did not write again, reply with the word STOP and I will "
        "put you on a list I check before contacting anyone.")

    if prospect.finding == NO_SITE_FOUND:
        # The claim is somebody's search, not OpenStreetMap's silence. The wording is
        # hedged for the same reason: a search can miss a site, the recipient knows
        # whether they have one, and an opening line that is wrong about it ends the
        # conversation and earns the annoyance.
        established = next(
            (stage.detail for stage in prospect.stages
             if stage.name == "is there a website"), "")
        claims = (f"a person searched and recorded the result: {established}",)
        subject = f"A website for {name}"
        body = (
            f"Hello,\n\n"
            f"I am {sender} — {sender_detail}. I went looking for {name} online and could "
            f"not find a website, though I may simply have missed it. If that is right, I "
            f"would be glad to talk about what one would need to do for you; if it is "
            f"wrong, I apologise for the noise and would be grateful for the link so I "
            f"can stop guessing.\n\n"
            f"{opt_out}\n\n"
            f"{sender}"
        )
        return Approach(prospect.key, name, channel, prospect.contact.address,
                        subject, body, claims)

    failures = prospect.material_failures
    findings = "\n".join(
        f"  - {f.detail}" + (f" ({f.remedy})" if getattr(f, "remedy", "") else "")
        for f in failures)
    claims = tuple(f"{f.name}: {f.detail}" for f in failures)
    site_url = getattr(prospect.site, "url", "your website")
    subject = f"Two things I noticed about {name}'s website"
    body = (
        f"Hello,\n\n"
        f"I am {sender} — {sender_detail}. I had a look at {site_url} and noticed a "
        f"couple of specific things, which I thought were worth passing on whether or not "
        f"you ever want anything from me:\n\n"
        f"{findings}\n\n"
        f"None of that is a judgement about how the site looks — it is what I could "
        f"measure from one page. If you would like it fixed I would be glad to quote, and "
        f"if you would rather hand the list to whoever built it, that is a perfectly good "
        f"outcome too.\n\n"
        f"{opt_out}\n\n"
        f"{sender}"
    )
    return Approach(prospect.key, name, channel, prospect.contact.address,
                    subject, body, claims)


def summarise(prospects: Sequence[Prospect]) -> str:
    """The counts, with what was NOT established kept beside what was."""

    counts: dict[str, int] = {}
    for prospect in prospects:
        counts[prospect.finding] = counts.get(prospect.finding, 0) + 1

    lines = [f"{len(prospects)} business(es) assessed:"]
    for finding in (NEEDS_WORK, NO_SITE_FOUND, ADEQUATE, NOT_ESTABLISHED):
        lines.append(f"  {finding:<18} {counts.get(finding, 0)}")
    lines.append(
        "  NOT_ESTABLISHED is neither a prospect nor a rejection: those are businesses "
        "this looked at and learned nothing about.")
    blocked = [p for p in prospects if p.contact is not None and not p.contact.permitted]
    if blocked:
        lines.append(f"  {len(blocked)} may not be contacted, and the reason is on each.")
    return "\n".join(lines)
