"""Is this book's price wrong, and by more than the ways we could be wrong about it?

This is a forecast, and this repository refuses forecasts nearly everywhere. `docs/future-
lanes.md` says a scoring model over opportunities will not be built; `lib/candidates.py`
argues at length that a weighted sum treats a disqualifier as a deduction; `lib/arb.py`
opens by saying it needs no model of what will happen. All of that stands, and none of it
is being quietly walked back here.

What makes this admissible is the precedent already in the repository:
`lib.stocks_reaper.Criterion` allows a `FORECAST` — and refuses to construct one without a
named human declaring it, because a prediction is not something a machine may originate on
its own authority. A mispricing model is a forecast, so it is built the same way. Nothing
in this file can produce a number that anybody acts on unless a person signed for it.

And an arb and a mispricing are not the same claim, which is why they are separate lanes
rather than one with a switch. An arb says *these two prices cannot both be right*, which
needs no view about the fixture. A mispricing says *this price is wrong*, which needs one.
The second is a bet. It is allowed to be a bet; it is not allowed to be printed in the
vocabulary of the first.

## The four ways this is wrong, and the guard against each

**1. Wrong because the vig was removed wrongly.** A book's prices sum well over 100%, and
turning them into probabilities requires choosing how to take that out. Proportional,
additive, power and Shin all give different answers, and they diverge most at long odds —
precisely where a model most often thinks it has found something. So `devig` runs every
method, reports the one that was DECLARED, and carries the spread across all of them. An
edge smaller than that spread is `METHOD_DEPENDENT`: it is an artefact of a modelling
choice rather than a disagreement with the book, and it is refused.

**2. Wrong because an input was missing.** Every feature has three states, and a required
feature that is UNKNOWN produces `UNPRICED` rather than a number computed from the ones
that happened to be readable. This is the repository's founding defect in the place a
model is most tempted to commit it: an absent injury report is not a fit squad, and a
weather call that timed out is not a still, dry evening.

**3. Wrong because the model is wrong.** Every model states its own error band, and an
edge inside that band is `FAIR` — not "a small edge". A model that cannot say how wrong it
usually is cannot be constructed at all.

**4. Wrong because nobody ever checked.** A model with no settled record is `PAPER`: it
runs, it publishes forecasts, and it cannot size anything. A named human promotes it to
`LIVE` against a stated number of settled predictions. This is the guard that matters most,
because every one of the others can be satisfied by a model that is simply bad, and the
only thing that finds that out is time and a ledger.

## What is deliberately not modelled

Motivation, "must-win", momentum, and anything else that cannot be read off a source. They
are real and they are unmeasurable here, and a feature that cannot be measured either drags
every forecast toward the mean or gets dropped from the average and flatters it — the
argument `lib/candidates.py` makes about scoring, applied to inputs.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from lib.thesis import AUTOMATION_PREFIXES

# Feature states. A feature is a fact somebody retrieved, and it can fail to be one in two
# different ways that need different responses from a person.
KNOWN = "KNOWN"
UNKNOWN = "UNKNOWN"
STALE = "STALE"

# What a de-vig produced.
PRICED = "PRICED"
UNPRICED = "UNPRICED"

# What the comparison concluded.
MISPRICED = "MISPRICED"
FAIR = "FAIR"
METHOD_DEPENDENT = "METHOD_DEPENDENT"
INDETERMINATE = "INDETERMINATE"

# Whether the model is allowed to size anything.
PAPER = "PAPER"
LIVE = "LIVE"

# De-vig methods. Named rather than defaulted; see `devig`.
PROPORTIONAL = "PROPORTIONAL"
ADDITIVE = "ADDITIVE"
POWER = "POWER"
SHIN = "SHIN"
METHODS = (PROPORTIONAL, ADDITIVE, POWER, SHIN)

#: Goals beyond which a Poisson tail contributes nothing a two-decimal probability can see.
#: 10 rather than 6: 6 truncates about 1 in 3,000 of the mass at the scorelines a big
#: favourite produces, which is small and is exactly the region a long-odds edge lives in.
MAX_GOALS = 10


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, AttributeError, TypeError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


# --- evidence -------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Feature:
    """One input to a forecast, and whether it is actually known.

    `value` is `None` unless `status` is KNOWN. Not zero, and not a plausible average: a
    missing wind speed rendered as 0.0 is a still evening, an absent injury count rendered
    as 0 is a fit squad, and both are the flattering reading arriving without a label.
    """

    name: str
    status: str
    value: float | None = None
    as_of: str = ""
    source: str = ""
    detail: str = ""

    def __post_init__(self) -> None:
        if self.status not in {KNOWN, UNKNOWN, STALE}:
            raise ValueError(f"a feature is {KNOWN}, {UNKNOWN} or {STALE}, "
                             f"not {self.status!r}")
        if self.status == KNOWN and self.value is None:
            raise ValueError(
                f"{self.name}: KNOWN with no value. A feature that is known has a number; "
                f"this combination is how an absence acquires a status that says otherwise")
        if self.status != KNOWN and self.value is not None:
            raise ValueError(
                f"{self.name}: {self.status} carrying a value of {self.value}. A stale or "
                f"unknown feature must not hand a caller something to use anyway")

    @property
    def usable(self) -> bool:
        return self.status == KNOWN

    def describe(self) -> str:
        if self.status == KNOWN:
            return (f"{self.name} = {self.value:g}"
                    + (f"  ({self.source}, {self.as_of})" if self.source else ""))
        return f"{self.name} {self.status}: {self.detail or 'no reason recorded'}"


@dataclass(frozen=True, slots=True)
class Evidence:
    """Everything retrieved about one fixture, with each absence kept as an absence."""

    subject: str
    features: tuple[Feature, ...] = ()
    #: When the fixture starts, as the source gave it. Empty when unknown — the lane's own
    #: gate decides what that means, and a bundle must not invent one.
    kickoff: str = ""

    def get(self, name: str) -> Feature | None:
        return next((f for f in self.features if f.name == name), None)

    def value(self, name: str, default: float | None = None) -> float | None:
        """The number if it is KNOWN, else the caller's default — which is usually None.

        Callers pass a default only for features the model can genuinely proceed without,
        and every such default is a modelling assumption that appears in the output. See
        `GoalsModel.forecast`, where each one is recorded as an assumption rather than
        absorbed.
        """

        feature = self.get(name)
        return feature.value if feature is not None and feature.usable else default

    def missing(self, required: Sequence[str]) -> tuple[str, ...]:
        """Required features that are absent, unknown or stale, in the order required."""

        return tuple(name for name in required
                     if (f := self.get(name)) is None or not f.usable)

    def describe(self) -> str:
        if not self.features:
            return f"{self.subject}: nothing was retrieved. No feature was even attempted."
        return "\n".join([f"{self.subject}"]
                         + [f"  {f.describe()}" for f in self.features])


# --- removing the book's margin --------------------------------------------------------

@dataclass(frozen=True, slots=True)
class FairBook:
    """A book's prices with its margin removed, and how much that removal decided.

    `sensitivity` is the whole reason this type exists. Every de-vig method is a guess at
    how a book distributes its margin across selections, they disagree by more at long odds
    than at short ones, and any of them can be made to produce an edge on a price that is
    perfectly ordinary. Carrying the spread means a claimed edge can be compared against the
    uncertainty in the arithmetic that produced it.
    """

    status: str
    method: str
    probabilities: Mapping[str, float] = field(default_factory=dict)
    #: Per selection, the widest gap between any two methods' fair probabilities.
    sensitivity: Mapping[str, float] = field(default_factory=dict)
    overround_pct: float = 0.0
    reason: str = ""

    def probability(self, selection: str) -> float | None:
        return self.probabilities.get(selection)

    def describe(self) -> str:
        if self.status != PRICED:
            return f"UNPRICED: {self.reason}"
        lines = [f"{self.method} de-vig, book overround {self.overround_pct:+.2f}%"]
        for selection, probability in self.probabilities.items():
            spread = self.sensitivity.get(selection, 0.0)
            lines.append(
                f"  {selection:<22} fair {probability * 100:6.2f}%  "
                f"(methods disagree by {spread * 100:.2f} points)")
        return "\n".join(lines)


def _implied(odds: Mapping[str, float]) -> dict[str, float]:
    return {selection: 1.0 / price for selection, price in odds.items()}


def _proportional(implied: Mapping[str, float]) -> dict[str, float]:
    total = sum(implied.values())
    return {k: v / total for k, v in implied.items()}


def _additive(implied: Mapping[str, float]) -> dict[str, float]:
    """Take the same number of points off every selection.

    Assumes the book spreads its margin evenly, which is the opposite assumption from
    proportional and is the reason both are computed: they bracket the real answer, and at
    long odds this one can go negative, which is reported rather than clipped.
    """

    excess = (sum(implied.values()) - 1.0) / len(implied)
    return {k: v - excess for k, v in implied.items()}


def _power(implied: Mapping[str, float]) -> dict[str, float]:
    """Raise every implied probability to a common power until they sum to one.

    Bisection rather than a solver: a dozen iterations is exact enough for a probability
    reported to two decimals, and it cannot fail to converge on a bracketed monotone
    function, which a Newton step on a badly conditioned book can.
    """

    low, high = 0.0001, 10.0
    for _ in range(80):
        mid = (low + high) / 2
        total = sum(v ** mid for v in implied.values())
        if total > 1.0:
            low = mid
        else:
            high = mid
    return {k: v ** ((low + high) / 2) for k, v in implied.items()}


def _shin(implied: Mapping[str, float]) -> dict[str, float]:
    """Shin's model: the margin is what the book charges for trading against insiders.

    Solves for z, the notional proportion of informed money, then backs out the underlying
    probabilities. It gives longshots a lower fair probability than proportional does, which
    is the direction the favourite-longshot bias actually runs — and it is included for that
    reason rather than for elegance: without it every method here would be biased the same
    way and the sensitivity spread would understate itself.
    """

    total = sum(implied.values())
    if total <= 1.0:
        return dict(implied)

    low, high = 0.0, 0.5
    for _ in range(80):
        z = (low + high) / 2
        derived = {
            k: (math.sqrt(z * z + 4 * (1 - z) * v * v / total) - z) / (2 * (1 - z))
            for k, v in implied.items()
        }
        if sum(derived.values()) > 1.0:
            low = z
        else:
            high = z
    z = (low + high) / 2
    derived = {
        k: (math.sqrt(z * z + 4 * (1 - z) * v * v / total) - z) / (2 * (1 - z))
        for k, v in implied.items()
    }
    scale = sum(derived.values())
    return {k: v / scale for k, v in derived.items()}


_ESTIMATORS = {PROPORTIONAL: _proportional, ADDITIVE: _additive,
               POWER: _power, SHIN: _shin}


def devig(odds: Mapping[str, float], *, method: str) -> FairBook:
    """The book's own probabilities with its margin removed, by a DECLARED method.

    `method` has no default on purpose. The choice changes the answer materially at the odds
    where a model most often thinks it has found something, so a caller that did not choose
    is a caller who does not know which of four different numbers they are comparing against.

    A market that is not complete, or whose prices are not prices, is UNPRICED. Not a small
    number and not a partial answer: de-vigging two of a three-way market removes a margin
    that was never spread over two selections.
    """

    if method not in _ESTIMATORS:
        raise ValueError(f"unknown de-vig method {method!r}; choose from "
                         f"{', '.join(METHODS)}")
    if len(odds) < 2:
        return FairBook(UNPRICED, method, reason=(
            "fewer than two selections. A margin cannot be removed from a market with no "
            "other side, and the number that came out would be the book's price wearing a "
            "different name"))
    if any(price <= 1.0 for price in odds.values()):
        return FairBook(UNPRICED, method, reason=(
            "at least one price is at or below 1.0, which is not a decimal price"))

    implied = _implied(odds)
    total = sum(implied.values())
    if total <= 1.0:
        return FairBook(UNPRICED, method, reason=(
            f"the prices imply {total * 100:.2f}%, at or under 100%. There is no margin to "
            f"remove — that is an arb, and lib/arbfind.py is what evaluates it. Treating it "
            f"as a mispricing would put a lock and a forecast in the same report"))

    everyone = {name: estimator(implied) for name, estimator in _ESTIMATORS.items()}
    chosen = everyone[method]
    if any(p <= 0.0 for p in chosen.values()):
        return FairBook(UNPRICED, method, reason=(
            f"{method} produced a probability at or below zero on this book, which means "
            f"the assumption behind it does not hold here. Reported rather than clipped: a "
            f"clipped zero is a certainty nobody computed"))

    sensitivity = {
        selection: max(v[selection] for v in everyone.values())
                   - min(v[selection] for v in everyone.values())
        for selection in implied
    }
    return FairBook(PRICED, method, chosen, sensitivity, (total - 1.0) * 100.0)


# --- the model ------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class MispricingModel:
    """A named human's forecast method, its known error, and whether it may size anything.

    The same guard as `lib.stocks_reaper.Criterion`'s FORECAST kind and for the same reason:
    a prediction asserts something no source establishes, so it needs somebody's name on it.
    Minting one from an agent would put the system back in the position of originating its
    own reasons to move money.

    `stated_error_pct` is mandatory and has no default. A model that cannot say how wrong it
    usually is offers no way to tell a real disagreement with the book from its own noise,
    and every edge it reports would be indistinguishable from rounding.

    `status` starts at PAPER and only a person moves it. A PAPER model runs, publishes and
    cannot size — which is the guard the other three cannot provide, because a model can
    satisfy all of them and still simply be bad. The only thing that establishes otherwise
    is a settled record, and `promoted_on` records what that record was.
    """

    name: str
    declared_by: str
    reasoning: str
    #: Feature names the model refuses to run without. UNPRICED when any is missing.
    requires: tuple[str, ...]
    #: How far out this model's probabilities typically are, in percentage points. An edge
    #: inside this is FAIR, never "a small edge".
    stated_error_pct: float
    #: How the book's margin is removed before comparing. Declared here so the comparison
    #: and the model cannot drift onto different assumptions.
    devig_method: str
    expires_at: str
    max_exposure: float
    status: str = PAPER
    declared_at: str = ""
    currency: str = "EUR"
    #: What a person saw before moving this to LIVE — how many settled predictions, over
    #: what period, and how the forecasts compared with the outcomes. Required for LIVE.
    promoted_on: str = ""

    def __post_init__(self) -> None:
        author = self.declared_by.strip().lower()
        if not author:
            raise ValueError("a forecasting model needs a named human author")
        if any(author.startswith(prefix) for prefix in AUTOMATION_PREFIXES):
            raise ValueError(
                f"{self.declared_by!r} cannot declare a mispricing model. This is a "
                f"FORECAST — it asserts something about a fixture that no source "
                f"establishes — and lib/stocks_reaper.Criterion refuses the same thing for "
                f"the same reason: automation originating its own reasons to move money")
        if not self.reasoning.strip():
            raise ValueError("a model without stated reasoning is a number with no argument")
        if self.stated_error_pct <= 0:
            raise ValueError(
                "stated_error_pct must be positive. A model claiming no error offers no "
                "way to tell a real disagreement with the book from its own noise, and "
                "every edge it reported would be indistinguishable from rounding")
        if self.devig_method not in METHODS:
            raise ValueError(f"unknown de-vig method {self.devig_method!r}")
        if self.status not in {PAPER, LIVE}:
            raise ValueError(f"a model is {PAPER} or {LIVE}, not {self.status!r}")
        if self.status == LIVE and not self.promoted_on.strip():
            raise ValueError(
                "a LIVE model must record what was seen before it was promoted: how many "
                "settled predictions, over what period, and how they compared with the "
                "outcomes. Without that, LIVE is a claim that somebody checked, made by "
                "somebody who may not have")
        if not self.requires:
            raise ValueError(
                "a model that requires no feature cannot be UNPRICED, so it will produce a "
                "number on a fixture nothing is known about")

    @property
    def may_size(self) -> bool:
        return self.status == LIVE

    def is_expired(self, now: datetime | None = None) -> bool:
        expiry = _parse(self.expires_at)
        # An unreadable expiry is treated as expired. The direction that halts.
        return True if expiry is None else expiry <= (now or _now())

    def describe(self) -> str:
        lines = [
            f"{self.name}  [{self.status}]  declared by {self.declared_by}",
            f"  {self.reasoning}",
            f"  states its own error at +/-{self.stated_error_pct:.2f} points; de-vigs by "
            f"{self.devig_method}; requires {', '.join(self.requires)}",
        ]
        if self.status == PAPER:
            lines.append(
                "  PAPER: it publishes forecasts and cannot size anything. A named person "
                "promotes it against a settled record, and until then every edge it finds "
                "is a note rather than an instruction.")
        else:
            lines.append(f"  promoted on: {self.promoted_on}")
        return "\n".join(lines)


# --- the forecast itself ---------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Forecast:
    """What the model thinks, what it assumed to get there, and what it could not see."""

    status: str
    subject: str
    probabilities: Mapping[str, float] = field(default_factory=dict)
    #: Assumptions taken because an optional feature was not available. Every one is a way
    #: this forecast is less informed than it looks, so they travel with it rather than
    #: being logged and forgotten.
    assumptions: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()
    reason: str = ""

    def probability(self, selection: str) -> float | None:
        return self.probabilities.get(selection)

    def describe(self) -> str:
        if self.status != PRICED:
            return (f"UNPRICED  {self.subject}\n  {self.reason}\n"
                    f"  Required and not available: {', '.join(self.missing) or 'none'}. "
                    f"This is not a forecast of an even market; nothing was forecast.")
        lines = [f"{self.subject}"]
        for selection, probability in self.probabilities.items():
            lines.append(f"  {selection:<22} {probability * 100:6.2f}%")
        for assumption in self.assumptions:
            lines.append(f"  ASSUMED: {assumption}")
        return "\n".join(lines)


def poisson_scoreline(home_lambda: float, away_lambda: float,
                      max_goals: int = MAX_GOALS) -> dict[str, float]:
    """Home / Draw / Away from two expected-goals figures, over a truncated grid.

    Independent Poisson, which is the standard and is known to under-predict draws and
    low-scoring scorelines — the effect Dixon and Coles corrected for. That correction is
    NOT applied here, deliberately: its parameter has to be fitted to a competition's own
    history, and fitting it from nothing would produce a plausible number with no data
    behind it. The under-prediction is instead declared, in the model's `stated_error_pct`
    and in `docs/mispricing-design.md`, so an edge on the draw has to clear a band that
    already knows this is the weakest part of the arithmetic.
    """

    home_probs = [math.exp(-home_lambda) * home_lambda ** k / math.factorial(k)
                  for k in range(max_goals + 1)]
    away_probs = [math.exp(-away_lambda) * away_lambda ** k / math.factorial(k)
                  for k in range(max_goals + 1)]

    home = draw = away = 0.0
    for h, p_h in enumerate(home_probs):
        for a, p_a in enumerate(away_probs):
            joint = p_h * p_a
            if h > a:
                home += joint
            elif h == a:
                draw += joint
            else:
                away += joint

    # The truncated tail is redistributed proportionally rather than discarded. Discarding
    # it makes the three probabilities sum to slightly under one, and a probability compared
    # against a book price is a comparison where "slightly under" is a free edge.
    total = home + draw + away
    return {"HOME": home / total, "DRAW": draw / total, "AWAY": away / total}


@dataclass(frozen=True, slots=True)
class GoalsModel:
    """Expected goals from team strengths, adjusted for what is actually known.

    The arithmetic is ordinary and is meant to be: attack and defence strengths relative to
    the league, a home advantage, and adjustments for the conditions. What is not ordinary
    is that every adjustment is applied only when its feature is KNOWN, and every one it
    could not apply is carried out with the forecast as an assumption.

    The adjustment sizes are small and each is stated where it is applied. They are
    judgement, not measurement, and a reader should be able to see that from the code
    rather than from a paper nobody has.
    """

    #: Goals per team per game in this competition, from league data. Not a constant: the
    #: Premier League and a low-scoring league are different priors and using one figure
    #: for both is a modelling error that shows up as a systematic edge on unders.
    league_goals_per_team: float = 1.4
    #: How much more the home side scores, as a multiplier. Beaten down since 2020 and
    #: further by empty stadiums; 1.15 is conservative and is a number to fit rather than
    #: to trust.
    home_advantage: float = 1.15

    def forecast(self, model: MispricingModel, evidence: Evidence) -> Forecast:
        """HOME/DRAW/AWAY, or UNPRICED naming exactly what was missing."""

        missing = evidence.missing(model.requires)
        if missing:
            return Forecast(UNPRICED, evidence.subject, missing=missing, reason=(
                f"{len(missing)} required feature(s) were not available. A forecast "
                f"computed from the inputs that happened to be readable is the same "
                f"confident answer as one computed from none of them, with a number "
                f"attached"))

        home_attack = evidence.value("home_attack_strength")
        home_defence = evidence.value("home_defence_strength")
        away_attack = evidence.value("away_attack_strength")
        away_defence = evidence.value("away_defence_strength")
        if None in (home_attack, home_defence, away_attack, away_defence):
            # Reachable only if a model's `requires` omits a strength, which is a
            # configuration a person can write. Refused rather than defaulted to 1.0, which
            # would silently forecast an average team against an average team.
            return Forecast(UNPRICED, evidence.subject, reason=(
                "team strengths are not all known, and this model cannot substitute an "
                "average side for one it has no figures on"),
                missing=tuple(name for name, value in (
                    ("home_attack_strength", home_attack),
                    ("home_defence_strength", home_defence),
                    ("away_attack_strength", away_attack),
                    ("away_defence_strength", away_defence)) if value is None))

        base = self.league_goals_per_team
        home_lambda = base * home_attack * away_defence * self.home_advantage
        away_lambda = base * away_attack * home_defence

        assumptions: list[str] = []
        home_lambda, away_lambda = self._weather(
            evidence, home_lambda, away_lambda, assumptions)
        home_lambda, away_lambda = self._absences(
            evidence, home_lambda, away_lambda, assumptions)
        home_lambda, away_lambda = self._rest(
            evidence, home_lambda, away_lambda, assumptions)

        # Bounded below at a tenth of a goal. A negative or zero expectation is not a team
        # that cannot score; it is an adjustment stack that has gone past what it models.
        home_lambda = max(home_lambda, 0.1)
        away_lambda = max(away_lambda, 0.1)

        return Forecast(PRICED, evidence.subject,
                        poisson_scoreline(home_lambda, away_lambda),
                        assumptions=tuple(assumptions))

    def _weather(self, evidence: Evidence, home: float, away: float,
                 assumptions: list[str]) -> tuple[float, float]:
        """Wind and rain suppress goals. Small effects, applied only when measured.

        The direction is well attested and the size is not, so these are deliberately
        modest: a strong wind is worth a few percent, not a goal. A model that moved the
        line hard on a weather forecast would be betting on the forecast.
        """

        wind = evidence.get("wind_speed_kph")
        if wind is None or not wind.usable:
            assumptions.append(
                "no wind reading was available, so no weather adjustment was applied. The "
                "forecast is for an ordinary evening, which is the commonest case and is "
                "not the same as knowing.")
            return home, away
        if wind.value is not None and wind.value >= 30.0:
            # Above roughly 30 km/h the ball's flight is affected enough to show up in
            # completed passes and shot accuracy. 4% off both sides.
            home, away = home * 0.96, away * 0.96

        rain = evidence.get("precipitation_mm")
        if rain is not None and rain.usable and rain.value is not None and rain.value >= 5.0:
            home, away = home * 0.97, away * 0.97
        return home, away

    def _absences(self, evidence: Evidence, home: float, away: float,
                  assumptions: list[str]) -> tuple[float, float]:
        """Key players missing. The largest real effect here and the worst-sourced.

        There is no free, reliable, machine-readable team-news source, so this is almost
        always UNKNOWN — and that absence is stated on every forecast rather than being
        allowed to read as a fully fit squad. It is the single biggest reason a model here
        should be expected to be beaten by a book, which knows the team news and prices it.
        """

        for side, key in (("home", "home_key_absences"), ("away", "away_key_absences")):
            feature = evidence.get(key)
            if feature is None or not feature.usable:
                assumptions.append(
                    f"{side} team news was not available, so the {side} side is being "
                    f"forecast as fully fit. The book is not making that assumption.")
                continue
            # 6% off the attack per key absentee, capped at three. Judgement, and the cap
            # is the important half: a fourth and fifth absentee do not keep subtracting
            # linearly, and without the cap a long injury list produces a team that
            # cannot score.
            absent = min(float(feature.value or 0.0), 3.0)
            factor = max(1.0 - 0.06 * absent, 0.82)
            if side == "home":
                home *= factor
            else:
                away *= factor
        return home, away

    def _rest(self, evidence: Evidence, home: float, away: float,
              assumptions: list[str]) -> tuple[float, float]:
        """Short turnarounds. Applied only on the DIFFERENCE between the two sides.

        Absolute rest days say little — both sides playing on three days' rest is an
        ordinary midweek round. What shows up is the asymmetry, so only the gap is used,
        and only when both figures are known.
        """

        home_rest = evidence.value("home_rest_days")
        away_rest = evidence.value("away_rest_days")
        if home_rest is None or away_rest is None:
            assumptions.append(
                "rest days were not known for both sides, so no turnaround adjustment was "
                "applied.")
            return home, away

        gap = max(-3.0, min(3.0, home_rest - away_rest))
        # 2% per day of advantage, on the rested side's attack only.
        if gap > 0:
            home *= 1.0 + 0.02 * gap
        elif gap < 0:
            away *= 1.0 + 0.02 * (-gap)
        return home, away


# --- comparing the two -----------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Edge:
    """What the model and the book disagree about, and whether that survives the doubt."""

    status: str
    subject: str
    selection: str
    book: str
    decimal_odds: float = 0.0
    model_probability: float | None = None
    book_probability: float | None = None
    #: Expected return per unit staked, in percent, at these odds. Positive means the model
    #: thinks the price is too long. Never a guarantee, and named `expected` for that reason.
    expected_value_pct: float = 0.0
    #: How far apart the four de-vig methods put this selection's fair probability, in
    #: PROBABILITY POINTS.
    method_sensitivity_points: float = 0.0
    #: The model's own stated error, also in PROBABILITY POINTS.
    stated_error_points: float = 0.0
    #: What one unit of probability is worth here, so the two bands above can be compared
    #: against an expected value. See `doubt_band_pct`.
    net_odds: float = 0.0
    assumptions: tuple[str, ...] = ()
    reason: str = ""

    @property
    def doubt_band_pct(self) -> float:
        """The two uncertainties, converted into the same unit as the edge itself.

        This conversion is not a detail. `expected_value_pct` is a percentage OF STAKE and
        both uncertainty figures are PROBABILITY POINTS, and comparing them directly — as
        the first version of this file did — makes the same three-point error look
        negligible at 1.5 and fatal at 15.0. Expected value moves by `net_odds` percent of
        stake for every point of probability, so the bands are multiplied up rather than
        the edge being divided down: at odds of 8.0, three points of model error is
        twenty-four percent of stake, which is most long-priced "edges" this model will
        ever report.

        The wider of the two binds. They are different doubts — one about the arithmetic
        that removed the book's margin, one about the model — and clearing the smaller
        while inside the larger is not clearing anything.
        """

        return max(self.method_sensitivity_points,
                   self.stated_error_points) * self.net_odds

    @property
    def survives_doubt(self) -> bool:
        """Whether the claimed edge is bigger than both ways it could be an artefact."""

        return self.expected_value_pct > self.doubt_band_pct

    def describe(self) -> str:
        if self.status == INDETERMINATE:
            return (f"INDETERMINATE  {self.subject} / {self.selection}\n  {self.reason}\n"
                    f"  Nothing was concluded. That is not a finding that the price is "
                    f"fair.")
        head = (f"{self.status}  {self.subject} / {self.selection} at {self.book} "
                f"{self.decimal_odds:.2f}")
        lines = [head]
        if self.model_probability is not None and self.book_probability is not None:
            lines.append(
                f"  model {self.model_probability * 100:.2f}%  vs  book "
                f"{self.book_probability * 100:.2f}% (de-vigged)  ->  "
                f"{self.expected_value_pct:+.2f}% expected per unit staked")
        lines.append(
            f"  the de-vig method choice alone moves this by "
            f"{self.method_sensitivity_points:.2f} probability points and the model states "
            f"its own error at {self.stated_error_points:.2f} — at {self.net_odds:.2f} net "
            f"odds that is a doubt band of {self.doubt_band_pct:.2f}% of stake")
        if self.status == METHOD_DEPENDENT:
            lines.append(
                "  The edge is smaller than the disagreement between de-vig methods, so it "
                "is an artefact of how the margin was removed rather than a disagreement "
                "with the book.")
        elif self.status == FAIR:
            lines.append(
                "  Inside the model's own error band. Not a small edge — no edge that this "
                "model is entitled to claim.")
        elif self.status == MISPRICED:
            lines.append(
                "  Bigger than both the method spread and the model's stated error. This "
                "is a FORECAST that the price is wrong, not a lock: if the model is wrong "
                "about this fixture the whole stake is lost.")
        for assumption in self.assumptions:
            lines.append(f"  ASSUMED: {assumption}")
        if self.reason:
            lines.append(f"  {self.reason}")
        return "\n".join(lines)


def find_edge(
    *,
    model: MispricingModel,
    forecast: Forecast,
    fair: FairBook,
    selection: str,
    book: str,
    decimal_odds: float,
    commission_pct: float = 0.0,
    subject: str = "",
) -> Edge:
    """The model against one book's price on one selection.

    Order matters and is cheapest-and-most-fatal-first, as everywhere else here. An
    unpriced forecast and an unpriced book are INDETERMINATE before any arithmetic runs,
    because a number computed from either would be a comparison against something that was
    never established.
    """

    subject = subject or forecast.subject
    net_odds = 1.0 + (decimal_odds - 1.0) * (1.0 - commission_pct / 100.0)
    common = {"subject": subject, "selection": selection, "book": book,
              "decimal_odds": decimal_odds, "assumptions": forecast.assumptions,
              "stated_error_points": model.stated_error_pct, "net_odds": net_odds}

    if forecast.status != PRICED:
        return Edge(INDETERMINATE, reason=(
            f"the model did not produce a forecast: {forecast.reason}"), **common)
    if fair.status != PRICED:
        return Edge(INDETERMINATE, reason=(
            f"the book's margin could not be removed: {fair.reason}"), **common)
    if model.is_expired():
        return Edge(INDETERMINATE, reason=(
            f"the model expired at {model.expires_at}. A forecast method is a claim about "
            f"a period, and past it nobody has said it still holds"), **common)

    model_p = forecast.probability(selection)
    book_p = fair.probability(selection)
    if model_p is None or book_p is None:
        return Edge(INDETERMINATE, reason=(
            f"{selection!r} is priced by one side and not the other — model "
            f"{'has it' if model_p is not None else 'does not'}, book "
            f"{'has it' if book_p is not None else 'does not'}. A selection the two are "
            f"not both talking about cannot be compared"), **common)

    expected = (model_p * net_odds - 1.0) * 100.0
    sensitivity = fair.sensitivity.get(selection, 0.0) * 100.0

    common = {**common, "model_probability": model_p, "book_probability": book_p,
              "expected_value_pct": expected, "method_sensitivity_points": sensitivity}
    candidate = Edge(MISPRICED, **common)

    if expected <= 0:
        return Edge(FAIR, reason=(
            "the model agrees with the book or thinks the price is short"), **common)
    # Which doubt binds decides which refusal a reader gets, and they send a person to
    # different places: METHOD_DEPENDENT means the de-vig choice manufactured this and
    # another method would not have, FAIR means the model is not entitled to claim it.
    # Compared in EV terms — see `doubt_band_pct` for why the points cannot be used raw.
    if expected <= sensitivity * net_odds and sensitivity >= model.stated_error_pct:
        return Edge(METHOD_DEPENDENT, **common)
    if not candidate.survives_doubt:
        return Edge(FAIR, **common)
    return candidate


def league_strengths(
    rows: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, dict[str, float]], float]:
    """Attack and defence strengths relative to the league, from a standings table.

    Each row needs `team`, `played`, `goals_for` and `goals_against`. Strength is the team's
    per-game rate over the league's, so 1.0 is exactly average and the two multiply into an
    expected-goals figure.

    Returns `({team: {"attack": a, "defence": d}}, league_goals_per_team)`. A team with no
    games played is OMITTED rather than given 1.0: a promoted side in August has no rate,
    and calling it average is the modelling equivalent of `or 0.0`.
    """

    played = sum(int(r.get("played", 0) or 0) for r in rows)
    scored = sum(float(r.get("goals_for", 0) or 0) for r in rows)
    if played <= 0 or scored <= 0:
        return {}, 0.0

    league_rate = scored / played
    strengths: dict[str, dict[str, float]] = {}
    for row in rows:
        games = int(row.get("played", 0) or 0)
        team = str(row.get("team") or "").strip()
        if games <= 0 or not team:
            continue
        strengths[team] = {
            "attack": (float(row.get("goals_for", 0) or 0) / games) / league_rate,
            "defence": (float(row.get("goals_against", 0) or 0) / games) / league_rate,
        }
    return strengths, league_rate
