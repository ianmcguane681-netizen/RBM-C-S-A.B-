"""What lands in your hands: a folder per business, with the sample site, the evidence
behind every word of it, and a draft note that is never sent by this program.

The deliverable is deliberately a folder on your disk rather than an outbound email, and
that is a design decision rather than an unfinished feature. Sending is the one irreversible
step in the whole pipeline — a page can be deleted, a wrong reading can be corrected, an
email that has arrived at a business cannot be recalled — so the pipeline stops one step
short of it and hands a person the thing they would have sent.

The parent repository's rule is that the deliverable is whatever a person can act from, and
that a slip good enough to act from is harder to produce than an API call. The same applies
here. Four files:

    BRIEF.md      what to design and what not to invent, for whoever builds the real page
    index.html    the reference render: plain, correct, and not the thing you send
    NOTE.md       the draft approach, with the opening sentence the evidence supports
    EVIDENCE.md   every fact, where it came from, and what was checked and found
    evidence.json the same, for a machine — and what `verify.py` checks a page against
    images/       the photographs, theirs and stock, each recorded in evidence.json

`EVIDENCE.md` exists because of the moment a business replies "where did you get my opening
hours". Being able to answer that in one line, from a file written before the email went
out, is the difference between a slightly odd approach and a slightly alarming one.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path

from prospector.brief import write_brief
from prospector.business import Business, Fact
from prospector.cascade import Decision
from prospector.condition import Condition
from prospector.countries import Country
from prospector.countries import UNKNOWN as COUNTRY_UNKNOWN
from prospector.images import SUBJECT_OWN, ImageSet, download
from prospector.locales import CATALOGUE, Locale
from prospector.presence import Presence
from prospector.site import render
from prospector.states import COULD_NOT_LOOK_FOR_IMAGES, IMAGES_FOUND
from prospector.verify import verify


def slug(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return cleaned or "unnamed"


def _serialise(obj):
    if is_dataclass(obj) and not isinstance(obj, type):
        return {k: _serialise(v) for k, v in asdict(obj).items()}
    if isinstance(obj, dict):
        return {k: _serialise(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialise(v) for v in obj]
    return obj


def _evidence_markdown(business: Business, presence: Presence,
                       condition: Condition | None, decision: Decision) -> str:
    lines = [f"# Evidence — {business.name.value}", "",
             f"Prepared {datetime.now(timezone.utc).isoformat(timespec='seconds')}.", "",
             "## Every fact on the page, and where it came from", ""]
    for key, fact in business.known().items():
        lines.append(f"- **{key}**: {fact.value}  \n  source: `{fact.source}`, "
                     f"retrieved {fact.retrieved_at}")
    lines += ["", "## Web presence", "", "```", presence.describe(), "```", ""]
    if not presence.may_claim_no_website and presence.status == "NO_SITE_LISTED":
        lines += ["> **Do not write that this business has no website.** What was "
                  "established is that the public listing does not carry one. No search "
                  "was run, because no search backend is configured.", ""]
    if condition is not None:
        lines += ["## The site they have", "", "```", condition.describe(), "```", ""]
    lines += ["## Decision", "", "```", decision.describe(), "```", ""]
    return "\n".join(lines)


def _note_markdown(business: Business, presence: Presence, decision: Decision,
                   operator: str, site_url: str = "", locale: Locale | None = None,
                   country: Country = COUNTRY_UNKNOWN) -> str:
    locale = locale or CATALOGUE["en"]
    name = business.name_in(locale.code).value
    where = (locale.text("where_url", url=site_url) if site_url
             else locale.text("where_attached"))
    contact = business.get("email")
    to = contact.value if isinstance(contact, Fact) else "no email listed — this one is a "\
        "phone call or a walk-in"
    claim = (locale.text(decision.claim_key) if decision.claim_key
             else decision.opening_claim)
    body = locale.text("note_body", where=where)
    caveat = ""
    if not locale.reviewed:
        caveat = (f"\n> **This note is in {locale.name} and nobody has checked it.** "
                  f"{locale.caveat}\n")
    english = ""
    if locale.code != "en":
        # The operator has to be able to read what they are about to send over their own
        # name. A translated note nobody in the room understands is a note nobody can
        # judge, and the point of stopping before sending is the judgement.
        english = (f"\n---\n\n## What it says, in English\n\n"
                   f"> {decision.opening_claim}\n")
    return f"""# Draft note — {name}

**To:** {to}
**Language:** {locale.name} (`{locale.code}`)
**Nothing has been sent. This file is a draft for you to read, edit and send yourself.**
{caveat}
---

{locale.text("note_greeting")}

{claim}

{body}

{operator}
{english}
---

## Before you send this

- Read the opening sentence again. It is the strongest claim the evidence supports and it
  was written from what was actually checked. Do not strengthen it.
- Check the opening hours and the address on the sample against reality. They came from a
  volunteer-maintained map and they are sometimes years old.
- **Where this is going:** {country.describe().splitlines()[0]}
- **The rule about sending it there**, which is a prompt to check rather than legal
  advice: {country.outreach_rule}
- If you are sending more than a handful of these in a day, you are running a bulk mailing
  and the rules for one apply to you.
"""


def write(business: Business, presence: Presence, condition: Condition | None,
          decision: Decision, *, out_dir: Path, operator: str,
          site_url: str = "", images: ImageSet | None = None,
          fetch_images: bool = True, max_images: int = 2,
          locale: Locale | str = "en", country: Country = COUNTRY_UNKNOWN) -> Path:
    """Write the folder for one business and return its path."""

    if isinstance(locale, str):
        locale = CATALOGUE[locale]
    folder = Path(out_dir) / f"{slug(business.name.value)}--{slug(business.identity)}"
    folder.mkdir(parents=True, exist_ok=True)
    sources = sorted({fact.source for fact in business.known().values()})

    found = images or ImageSet(status="NO_IMAGE_FOUND", reason="no image search was run")
    #: What the page may show: only images actually on disk beside it. `considered` keeps
    #: every candidate, downloaded or not, because the reason attached to a downgraded set
    #: says the records are in evidence.json and that sentence has to be true.
    on_disk: list = []
    considered: list = []
    if found.status == IMAGES_FOUND:
        for index, image in enumerate(found.images, start=1):
            if len(on_disk) >= max_images:
                considered.append(image)
                continue
            hint = ("theirs" if image.provenance == SUBJECT_OWN else "stock") + f"-{index}"
            fetched = (download(image, folder / "images", name_hint=hint)
                       if fetch_images else image)
            # A download that failed keeps its record and drops the picture. The page is
            # then short a photograph, which is visible, rather than carrying a broken
            # <img> that the recipient is the first to see.
            if fetched.local_path:
                relative = _with_relative_path(fetched)
                on_disk.append(relative)
                considered.append(relative)
            else:
                considered.append(image)
        if on_disk:
            images = ImageSet(IMAGES_FOUND, tuple(on_disk), found.reason, found.at)
        else:
            # Found and not fetched is not found. A set reporting IMAGES_FOUND with nothing
            # in it would put "photographs: 2" in the brief beside an empty folder, which
            # is the same defect as an empty book reporting a price.
            images = ImageSet(
                COULD_NOT_LOOK_FOR_IMAGES, (),
                reason=f"{len(found.images)} image(s) were found and none could be "
                       f"downloaded (the host refused an automated fetch); every candidate "
                       f"is still recorded in evidence.json", at=found.at)
    else:
        images = found
    image_dir = folder / "images"
    if image_dir.is_dir() and not any(image_dir.iterdir()):
        # An empty folder called `images` reads as "the photographs are missing" to whoever
        # opens the dossier. The absence belongs in VERIFY.md and the brief, in words.
        image_dir.rmdir()

    (folder / "index.html").write_text(
        render(business, operator=operator, sources=sources, images=images.images,
               locale=locale),
        encoding="utf-8")
    (folder / "BRIEF.md").write_text(
        write_brief(business, presence, decision, images, operator=operator,
                    locale=locale, country=country),
        encoding="utf-8")
    (folder / "NOTE.md").write_text(
        _note_markdown(business, presence, decision, operator, site_url, locale, country),
        encoding="utf-8")
    (folder / "EVIDENCE.md").write_text(
        _evidence_markdown(business, presence, condition, decision), encoding="utf-8")
    evidence = {
        "operator": operator,
        "language": locale.code,
        "language_reviewed": locale.reviewed,
        "country": _serialise(country),
        "business": _serialise(business),
        "presence": _serialise(presence),
        "condition": _serialise(condition),
        "decision": _serialise(decision),
        "images": [_serialise(image) for image in (considered or images.images)],
        "images_status": images.status,
        "images_reason": images.reason,
    }
    (folder / "evidence.json").write_text(json.dumps(evidence, indent=1, default=str),
                                          encoding="utf-8")
    # The reference render is checked by the same verifier that will check whatever gets
    # designed to replace it. A generator that exempts its own output is a generator whose
    # guarantee stops holding the moment somebody edits the file by hand.
    verdict = verify((folder / "index.html").read_text(encoding="utf-8"), evidence,
                     operator=operator, locale=locale)
    (folder / "VERIFY.md").write_text(
        f"# Verification\n\nOf `index.html`, against `evidence.json`, at "
        f"{datetime.now(timezone.utc).isoformat(timespec='seconds')}.\n\n"
        f"```\n{verdict.describe()}\n```\n\nRe-run after any edit, and after a "
        f"designed page replaces the reference render:\n\n"
        f"```bash\npython -m prospector.verify {folder}\n```\n", encoding="utf-8")
    return folder


def _with_relative_path(image):
    """The page and the file sit in the same folder, so `images/<name>` is the src."""

    from prospector.images import Image, _as_dict

    return Image(**{**_as_dict(image), "local_path": f"images/{image.local_path}"})
