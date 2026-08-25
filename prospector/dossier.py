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

    index.html   the sample site
    NOTE.md      the draft approach, with the opening sentence the evidence supports
    EVIDENCE.md  every fact, where it came from, and what was checked and found
    evidence.json the same, for a machine

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

from prospector.business import Business, Fact
from prospector.cascade import Decision
from prospector.condition import Condition
from prospector.presence import Presence
from prospector.site import render


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
                   operator: str, site_url: str = "") -> str:
    name = business.name.value
    where = site_url or "the attached file"
    contact = business.get("email")
    to = contact.value if isinstance(contact, Fact) else "no email listed — this one is a "\
        "phone call or a walk-in"
    return f"""# Draft note — {name}

**To:** {to}
**Nothing has been sent. This file is a draft for you to read, edit and send yourself.**

---

Hello,

{decision.opening_claim}

It is at {where}. It is a sample rather than a finished site: the details on it are the
ones listed publicly, there are no photographs because those are yours, and the parts that
need your words are marked as gaps rather than filled in with guesses.

If it is useful, I will finish it properly with you. If it is not, delete this and I will
not follow up.

{operator}

---

## Before you send this

- Read the opening sentence again. It is the strongest claim the evidence supports and it
  was written from what was actually checked. Do not strengthen it.
- Check the opening hours and the address on the sample against reality. They came from a
  volunteer-maintained map and they are sometimes years old.
- If you are sending more than a handful of these in a day, you are running a bulk mailing
  and the rules for one apply to you.
"""


def write(business: Business, presence: Presence, condition: Condition | None,
          decision: Decision, *, out_dir: Path, operator: str,
          site_url: str = "") -> Path:
    """Write the folder for one business and return its path."""

    folder = Path(out_dir) / f"{slug(business.name.value)}--{slug(business.identity)}"
    folder.mkdir(parents=True, exist_ok=True)
    sources = sorted({fact.source for fact in business.known().values()})
    (folder / "index.html").write_text(
        render(business, operator=operator, sources=sources), encoding="utf-8")
    (folder / "NOTE.md").write_text(
        _note_markdown(business, presence, decision, operator, site_url), encoding="utf-8")
    (folder / "EVIDENCE.md").write_text(
        _evidence_markdown(business, presence, condition, decision), encoding="utf-8")
    (folder / "evidence.json").write_text(json.dumps({
        "business": _serialise(business),
        "presence": _serialise(presence),
        "condition": _serialise(condition),
        "decision": _serialise(decision),
    }, indent=1, default=str), encoding="utf-8")
    return folder
