"""What one site costs to make, put up, secure and watch — and the refusal to total it
until somebody has said.

This is bookkeeping, not a business case. There is no revenue in this file, no projection
of what a retainer is worth next quarter and no break-even. The parent repository refuses
demand forecasts across every lane it has, and a costing that quietly grew a revenue column
would be the same error wearing a green eyeshade.

What it does hold is every line it takes to put one small business online, each of which is
`PRICED`, `UNPRICED` or `VARIES`:

    PRICED     somebody stated a number, or it is a published price with no conditions
    UNPRICED   nobody has said. NOT zero, and not left out of the total quietly
    VARIES     genuinely depends on something not yet known — the TLD, the traffic

## The one that matters

**A total that silently omits the unpriced lines is the flattering reading.** It is the
same defect as an empty portfolio reporting `0.0`, and here it produces a number that makes
every site look cheap: leave out the labour, which is the largest line by a distance, and
a site costs about twelve euro. So the totals are stated as a floor with the gaps named —
"at least €X, plus 3 lines nobody has priced: labour, domain, hosting" — and a costing with
an unpriced line refuses to call itself complete.

**Labour is the line that gets left out.** Not by accident: it is the one with no invoice
attached, so it does not feel like money. An hour of a person's time is the most expensive
thing in this whole pipeline and pretending otherwise is how a business ends up working for
four euro an hour and calling it margin.

## Configuration

`data/costs.json`, gitignored, because it holds a rate. `costs.example.json` beside this
file is the shape. Nothing is defaulted from thin air: an absent key is `UNPRICED`, which
is what makes the first run say what it does not know.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Sequence

PRICED = "PRICED"
UNPRICED = "UNPRICED"
VARIES = "VARIES"

ONCE = "ONCE"
PER_MONTH = "PER_MONTH"
PER_YEAR = "PER_YEAR"

CONFIG = Path("data/costs.json")
DEFAULT_CURRENCY = "EUR"


@dataclass(frozen=True, slots=True)
class Line:
    """One cost, its cadence, and whether anybody has actually priced it."""

    key: str
    label: str
    cadence: str
    state: str
    amount: float | None = None
    note: str = ""

    def per_year(self) -> float | None:
        if self.amount is None:
            return None
        if self.cadence == PER_MONTH:
            return self.amount * 12
        return self.amount

    def describe(self, currency: str) -> str:
        if self.state == PRICED:
            shown = f"{currency} {self.amount:,.2f}"
            cadence = {ONCE: "once", PER_MONTH: "/month", PER_YEAR: "/year"}[self.cadence]
            return f"  {self.label:34} {shown:>12} {cadence:<7} {self.note}"
        if self.state == VARIES:
            return f"  {self.label:34} {'VARIES':>12}         {self.note}"
        return f"  {self.label:34} {'UNPRICED':>12}         {self.note}"


@dataclass(frozen=True, slots=True)
class Costing:
    """Every line for one site, and what can honestly be said about the total."""

    lines: tuple[Line, ...]
    currency: str = DEFAULT_CURRENCY

    @property
    def unpriced(self) -> tuple[Line, ...]:
        return tuple(line for line in self.lines if line.state in (UNPRICED, VARIES))

    @property
    def complete(self) -> bool:
        """Whether a total may be stated as the cost rather than as a floor."""

        return not self.unpriced

    @property
    def first_year_at_least(self) -> float:
        """Every priced line for the first twelve months. A floor, never 'the cost'."""

        return sum(line.per_year() or 0.0 for line in self.lines
                   if line.state == PRICED and line.cadence in (ONCE, PER_YEAR, PER_MONTH))

    @property
    def recurring_monthly_at_least(self) -> float:
        return sum(line.amount or 0.0 for line in self.lines
                   if line.state == PRICED and line.cadence == PER_MONTH)

    def describe(self) -> str:
        lines = [f"COST OF ONE SITE ({self.currency})"]
        lines += [line.describe(self.currency) for line in self.lines]
        if self.complete:
            lines.append(f"  {'FIRST YEAR':34} "
                         f"{self.currency + f' {self.first_year_at_least:,.2f}':>12}")
            lines.append(f"  {'RECURRING':34} "
                         f"{self.currency + f' {self.recurring_monthly_at_least:,.2f}':>12} "
                         f"/month")
        else:
            missing = ", ".join(line.key for line in self.unpriced)
            lines.append(f"  AT LEAST {self.currency} {self.first_year_at_least:,.2f} in "
                         f"the first year, plus {len(self.unpriced)} line(s) nobody has "
                         f"priced: {missing}")
            lines.append("  This is a floor, not a cost. The largest line here is usually "
                         "labour, and a total without it is how a person ends up working "
                         "for four euro an hour and calling it margin.")
        return "\n".join(lines)


#: The lines it takes to put one small business online. Every one of them is a real thing
#: somebody pays for, including the two that are usually free and are stated anyway,
#: because "free" with conditions attached is a price and a person should see it.
SHAPE: tuple[tuple[str, str, str, str], ...] = (
    ("build_hours", "Building the site (hours)", ONCE,
     "the hours it takes to go from the sample to something they have signed off"),
    ("hourly_rate", "Your rate per hour", ONCE, "what an hour of your time is worth"),
    ("revision_hours", "Revisions after the first reply", ONCE,
     "their photos, their words, the two rounds nobody plans for"),
    ("domain_per_year", "Domain registration", PER_YEAR,
     "varies by TLD and registrar — a .ie is not a .com. Set it for the one you use"),
    ("hosting_per_month", "Hosting", PER_MONTH,
     "a static page fits every free tier there is, and a free tier is a price with "
     "conditions. Put the real number in, even if it is zero"),
    ("tls_per_year", "TLS certificate", PER_YEAR,
     "Let's Encrypt is free and automated; what costs is a renewal that fails quietly"),
    ("email_per_month", "Email or forwarding on their domain", PER_MONTH,
     "usually the first thing they ask for after the site"),
    ("monitoring_per_month", "Monitoring", PER_MONTH,
     "what it costs you to keep the promise that somebody is watching"),
    ("acquisition_per_prospect", "Finding and preparing one prospect", ONCE,
     "OpenStreetMap and Openverse are free; a paid search backend or a places API would "
     "put a real number here"),
)


def load(path: Path | str = CONFIG) -> tuple[Mapping[str, float], str, str]:
    """Rates from disk. Returns (values, currency, note about how it went).

    An unreadable file gives no values rather than defaults, so a costing built from it
    says UNPRICED everywhere instead of quietly inventing a cheap site.
    """

    path = Path(path)
    if not path.exists():
        return {}, DEFAULT_CURRENCY, f"{path} does not exist, so nothing is priced yet"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {}, DEFAULT_CURRENCY, f"{path} could not be read ({exc!r}), so nothing is priced"
    if not isinstance(data, dict):
        return {}, DEFAULT_CURRENCY, f"{path} is not an object, so nothing is priced"
    values = {k: float(v) for k, v in data.items()
              if isinstance(v, (int, float)) and k != "currency"}
    return values, str(data.get("currency", DEFAULT_CURRENCY)), ""


def cost_of_one_site(values: Mapping[str, float] | None = None, *,
                     currency: str = DEFAULT_CURRENCY) -> Costing:
    """The costing for one site from whatever has been priced."""

    values = dict(values or {})
    lines: list[Line] = []

    hours = values.get("build_hours")
    rate = values.get("hourly_rate")
    revisions = values.get("revision_hours")
    if hours is not None and rate is not None:
        total_hours = hours + (revisions or 0.0)
        note = (f"{hours:g}h build" + (f" + {revisions:g}h revisions" if revisions else "")
                + f" at {currency} {rate:,.2f}/h")
        lines.append(Line("labour", "Your time, build and revisions", ONCE, PRICED,
                          total_hours * rate, note))
    else:
        missing = " and ".join(name for name, value in
                               (("build_hours", hours), ("hourly_rate", rate))
                               if value is None)
        lines.append(Line("labour", "Your time, build and revisions", ONCE, UNPRICED,
                          None, f"set {missing} — this is the largest line there is"))

    for key, label, cadence, note in SHAPE:
        if key in ("build_hours", "hourly_rate", "revision_hours"):
            continue
        amount = values.get(key)
        if amount is None:
            state = VARIES if key == "domain_per_year" else UNPRICED
            lines.append(Line(key, label, cadence, state, None, note))
        else:
            lines.append(Line(key, label, cadence, PRICED, float(amount), note))
    return Costing(tuple(lines), currency)


def cost_of_a_run(costing: Costing, *, prepared: int, live: int = 0) -> str:
    """What a whole run cost, as far as anybody has priced it.

    Two numbers rather than one, because they are different questions: preparing a hundred
    samples costs whatever preparing costs, and only the ones that say yes ever reach the
    build. Conflating them is how the cost per site comes out a hundred times too high.
    """

    per_prospect = next((line for line in costing.lines
                         if line.key == "acquisition_per_prospect"), None)
    build = next((line for line in costing.lines if line.key == "labour"), None)
    lines = [f"THIS RUN ({costing.currency})",
             f"  {prepared} prepared, {live} of them live"]
    if per_prospect and per_prospect.state == PRICED:
        lines.append(f"  preparing {prepared}: {costing.currency} "
                     f"{per_prospect.amount * prepared:,.2f}")
    else:
        lines.append(f"  preparing {prepared}: UNPRICED — set acquisition_per_prospect")
    if build and build.state == PRICED and live:
        lines.append(f"  building {live}: {costing.currency} {build.amount * live:,.2f}")
    elif live:
        lines.append(f"  building {live}: UNPRICED — set build_hours and hourly_rate")
    lines.append("  No revenue appears here on purpose. What a site is worth to somebody "
                 "is a negotiation, and what a retainer is worth next quarter is a "
                 "forecast this package refuses to make.")
    return "\n".join(lines)
