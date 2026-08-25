"""Check a finished page against the evidence behind it, before anyone sees it.

This is the module that makes bespoke pages safe. If every sample came out of one template
there would be nothing to check — the template either invents things or it does not, once,
forever. The moment each business gets a page designed for it, by a person or by a model,
the guarantee has to move from the generator to a check on the output, because the whole
point of a bespoke page is that nobody read it before it was written.

So: take the page, take the `evidence.json` beside it, and refuse to let through anything
fact-shaped that the evidence does not support.

    VERIFIED           every checkable claim on the page traces to the evidence
    UNSOURCED_CLAIMS   something on the page does not, and each one is quoted
    COULD_NOT_VERIFY   the page or the evidence could not be read. NOT a pass

`COULD_NOT_VERIFY` failing rather than passing is the same rule as everywhere else, applied
where it costs least to be strict: the alternative is a page nobody checked going out under
somebody's name.

## What it looks for

**Numbers that assert something.** A phone number on the page that is not the phone number
in the evidence. An email. A founding year. A price. These are the details a model supplies
without noticing, because a page with a plausible phone number reads better than a page
with a gap.

**Phrases that assert something.** "Family-run", "established 1962", "award-winning",
"fully insured", "over 20 years". Every one of them is a claim about a business that nobody
here has spoken to, and none of them can be sourced from a map.

**Photographs.** Every image on the page must be one of the recorded images, and a stock
photograph must carry its label — because an unlabelled stock photograph on a page headed
with a business's name is a picture of premises that are not theirs, presented as theirs.

**The banner.** A sample that does not say it is a sample is a forgery of somebody's web
presence. It is checked here as well as generated, because the page may not have come from
this program at all.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable

from prospector.states import COULD_NOT_VERIFY, LICENSED_STOCK, UNSOURCED_CLAIMS, VERIFIED

#: Phrases that make a claim about a business rather than describing a page. Deliberately
#: written as the way a model writes them, because that is where they come from.
CLAIM_PHRASES = (
    "family-run", "family run", "family-owned", "family owned", "established in",
    "established 1", "established 2", "est.", "since 19", "since 20", "award-winning",
    "award winning", "fully insured", "fully qualified", "years of experience",
    "years experience", "generations", "trusted by", "voted", "no.1", "no. 1",
    "number one", "market leader", "best in", "we pride ourselves", "our team of",
    "founded in", "serving the community", "five-star", "5-star", "guaranteed",
    "free quote", "24/7", "certified", "accredited",
)

_PHONE = re.compile(r"(?:\+?\d[\d\s().-]{7,}\d)")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_YEAR = re.compile(r"\b(?:18|19|20)\d{2}\b")
_MONEY = re.compile(r"(?:[€£$]\s?\d[\d,.]*)")


@dataclass(frozen=True, slots=True)
class Problem:
    code: str
    detail: str


@dataclass(frozen=True, slots=True)
class Verdict:
    status: str
    problems: tuple[Problem, ...] = ()
    reason: str = ""

    def describe(self) -> str:
        if self.status == VERIFIED:
            return ("VERIFIED  every checkable claim on the page traces to the evidence. "
                    "That is not a verdict on the design.")
        if self.status == COULD_NOT_VERIFY:
            return (f"COULD_NOT_VERIFY  {self.reason}\n"
                    f"  The page was not checked, so it has not passed. Do not send it.")
        lines = [f"UNSOURCED_CLAIMS  {len(self.problems)}"]
        for problem in self.problems:
            lines.append(f"  {problem.code}: {problem.detail}")
        return "\n".join(lines)


class _Visible(HTMLParser):
    """Text a reader sees, plus the images and the meta tags that carry obligations."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text_parts: list[str] = []
        self.images: list[str] = []
        self.robots = ""
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag in ("script", "style"):
            self._skip += 1
        elif tag == "img" and values.get("src"):
            self.images.append(values["src"])
            # Alt text is read by a person using a screen reader, so it is page text and
            # an invented claim can hide in it.
            if values.get("alt"):
                self.text_parts.append(values["alt"])
        elif tag == "meta" and (values.get("name") or "").lower() == "robots":
            self.robots = (values.get("content") or "").lower()

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.text_parts.append(data)

    @property
    def text(self) -> str:
        return " ".join(" ".join(self.text_parts).split())


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value)


def _evidence_values(evidence: dict) -> list[str]:
    values: list[str] = []
    business = evidence.get("business") or {}
    for key in ("name", "kind", "website"):
        entry = business.get(key)
        if isinstance(entry, dict) and entry.get("value"):
            values.append(str(entry["value"]))
    for entry in (business.get("fields") or {}).values():
        if isinstance(entry, dict) and entry.get("value"):
            values.append(str(entry["value"]))
    raw = (business.get("raw") or {}).get("tags") or {}
    values += [str(v) for v in raw.values()]
    return values


def verify(page_html: str, evidence: dict, *, operator: str = "") -> Verdict:
    """The page, the evidence beside it, and every claim that does not join up."""

    if not page_html.strip():
        return Verdict(COULD_NOT_VERIFY, reason="the page is empty")
    if not evidence:
        return Verdict(COULD_NOT_VERIFY, reason="no evidence was supplied to check against")

    parser = _Visible()
    try:
        parser.feed(page_html)
    except Exception as exc:  # noqa: BLE001 - an unparseable page is unverified, not fine
        return Verdict(COULD_NOT_VERIFY, reason=f"the page would not parse: {exc!r}")

    text = parser.text
    lowered = text.lower()
    known = _evidence_values(evidence)
    known_text = " ".join(known).lower()
    known_digits = {_digits(v) for v in known if _digits(v)}
    problems: list[Problem] = []

    if "unofficial sample" not in lowered:
        problems.append(Problem("NO_SAMPLE_BANNER",
                                "the page does not say it is an unofficial sample. A page "
                                "carrying a business's name that does not say this is a "
                                "forgery of their web presence"))
    if "not affiliated" not in lowered:
        problems.append(Problem("NO_DISCLAIMER",
                                "the page does not disclaim affiliation with the business"))
    if operator and operator.lower() not in lowered:
        problems.append(Problem("UNSIGNED",
                                f"the page does not name {operator}, so nobody is standing "
                                f"behind it"))
    if "noindex" not in parser.robots:
        problems.append(Problem("INDEXABLE",
                                "the page does not ask search engines to leave it alone, "
                                "so a sample about somebody's business could outrank them"))

    for match in set(_PHONE.findall(text)):
        digits = _digits(match)
        if len(digits) < 8:
            continue
        if not any(digits in k or k in digits for k in known_digits):
            problems.append(Problem("UNSOURCED_NUMBER",
                                    f"the page prints {match.strip()!r}, which is not in "
                                    f"the evidence"))
    for match in {m.rstrip(".,;:") for m in _EMAIL.findall(text)}:
        if match.lower() not in known_text:
            problems.append(Problem("UNSOURCED_EMAIL",
                                    f"the page prints {match!r}, which is not in the evidence"))
    for match in {m.rstrip(".,;:") for m in _MONEY.findall(text)}:
        if match.lower() not in known_text:
            problems.append(Problem("UNSOURCED_PRICE",
                                    f"the page prints a price, {match!r}, and prices are "
                                    f"never in the evidence"))
    for match in set(_YEAR.findall(text)):
        if match not in known_text:
            problems.append(Problem("UNSOURCED_YEAR",
                                    f"the page prints the year {match}, which is not in "
                                    f"the evidence. A founding year is the invented detail "
                                    f"a reader notices first"))
    for phrase in CLAIM_PHRASES:
        if phrase in lowered and phrase not in known_text:
            problems.append(Problem("UNSOURCED_CLAIM",
                                    f"the page says {phrase!r}, which is a claim about the "
                                    f"business that nothing here established"))

    problems += _image_problems(parser.images, evidence, lowered)

    if problems:
        return Verdict(UNSOURCED_CLAIMS, tuple(problems))
    return Verdict(VERIFIED)


def _image_problems(srcs: Iterable[str], evidence: dict, lowered_text: str) -> list[Problem]:
    recorded = evidence.get("images") or []
    by_name = {}
    for entry in recorded:
        for key in ("local_path", "url"):
            value = entry.get(key)
            if value:
                by_name[str(value).rsplit("/", 1)[-1]] = entry
    problems: list[Problem] = []
    for src in srcs:
        if src.startswith("data:"):
            problems.append(Problem("EMBEDDED_IMAGE",
                                    "the page embeds an image whose source is not recorded"))
            continue
        entry = by_name.get(src.rsplit("/", 1)[-1])
        if entry is None:
            problems.append(Problem("UNRECORDED_IMAGE",
                                    f"the page shows {src!r}, which is not one of the "
                                    f"images recorded in the evidence"))
            continue
        if entry.get("provenance") == LICENSED_STOCK:
            label = (entry.get("label") or "").lower().rstrip(".")
            if label and label not in lowered_text:
                problems.append(Problem("UNLABELLED_STOCK",
                                        f"{src!r} is a stock photograph and the page does "
                                        f"not say so, which presents somebody else's "
                                        f"premises as this business's"))
            attribution = (entry.get("attribution") or "")
            creator = (entry.get("creator") or "").lower()
            required = entry.get("attribution_required", True)
            if required and attribution and creator and creator not in lowered_text:
                problems.append(Problem("MISSING_ATTRIBUTION",
                                        f"{src!r} is licensed on condition of attribution "
                                        f"to {entry.get('creator')}, and the page does not "
                                        f"carry it"))
    return problems


def verify_folder(folder: Path, *, operator: str = "") -> Verdict:
    """Check a dossier folder written by `dossier.write`, or any folder shaped like one."""

    folder = Path(folder)
    page = folder / "index.html"
    evidence_path = folder / "evidence.json"
    if not page.exists():
        return Verdict(COULD_NOT_VERIFY, reason=f"no index.html in {folder}")
    if not evidence_path.exists():
        return Verdict(COULD_NOT_VERIFY, reason=f"no evidence.json in {folder}")
    try:
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return Verdict(COULD_NOT_VERIFY, reason=f"evidence.json will not parse: {exc!r}")
    try:
        html = page.read_text(encoding="utf-8")
    except OSError as exc:
        return Verdict(COULD_NOT_VERIFY, reason=f"index.html will not read: {exc!r}")
    return verify(html, evidence, operator=operator or evidence.get("operator", ""))


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print("usage: python -m prospector.verify <dossier folder> [more folders]",
              file=sys.stderr)
        return 2
    worst = 0
    for target in argv:
        verdict = verify_folder(Path(target))
        print(f"{target}\n{verdict.describe()}\n")
        if verdict.status != VERIFIED:
            worst = 1
    return worst


if __name__ == "__main__":
    sys.exit(main())
