# The mispricing lane, designed and built

Written 2026-08-29 alongside the code, because the arguments here decide numbers that a
reader will otherwise be tempted to tune. `lib/mispricing.py` holds the model,
`lib/mispricing_evidence.py` the wiring to the sources, `lib/mispricing_reaper.py` the lane.

## Why this exists at all, given that this repository refuses forecasts

`docs/future-lanes.md` says a scoring model over opportunities will not be built.
`lib/candidates.py` argues at length that a weighted sum treats a disqualifier as a
deduction. `lib/arb.py` opens by saying it needs no model of what will happen. All of that
stands and none of it has been walked back.

What makes this admissible is the precedent already in the repository:
`lib.stocks_reaper.Criterion` allows a `FORECAST` kind and refuses to construct one without
a named human declaring it, because a prediction asserts something no source establishes.
A mispricing model is a forecast, so it is built the same way. `MispricingModel` refuses an
automation author outright, and every guard below exists because this thing predicts where
everything else in the repository merely establishes.

**An arb and a mispricing are different claims.** An arb says two prices cannot both be
right, which needs no view about the fixture. This says one price is wrong, which needs
one. That is why they are separate lanes rather than one lane with a switch, and why the
ticket says THIS IS A BET, NOT A LOCK where the arb slip says LOCK.

## The four ways this is wrong

### 1. The vig was removed wrongly

A book's prices sum well over 100% and turning them into probabilities requires choosing
how to take that out. Four methods are implemented — proportional, additive, power and
Shin — because they disagree, and they disagree **most at long odds**, which is precisely
where a model most often believes it has found something.

`devig` therefore runs all four, reports the one that was DECLARED, and carries the spread
across them as `sensitivity`. An edge smaller than that spread is `METHOD_DEPENDENT`: it is
an artefact of a modelling choice rather than a disagreement with the book.

Shin is included specifically because it is biased the other way from the rest. It gives a
longshot a lower fair probability than proportional does, which is the direction the
favourite-longshot bias actually runs — without it, every method here would be biased alike
and the sensitivity spread would understate itself.

### 2. An input was missing

Every `Feature` is `KNOWN`, `UNKNOWN` or `STALE`, and construction refuses `KNOWN` with no
value or `UNKNOWN` carrying one. A missing required feature produces `UNPRICED` naming it,
not a forecast computed from whatever happened to be readable.

Every adjustment that could NOT be applied travels out with the forecast as a stated
assumption. The most important one, on essentially every fixture:

> home team news was not available, so the home side is being forecast as fully fit.
> **The book is not making that assumption.**

### 3. The model is wrong

`stated_error_pct` is mandatory and positive, in **probability points**. An edge inside it
is `FAIR` — not "a small edge".

The arithmetic here is the part worth reading. `expected_value_pct` is a percentage **of
stake** and both uncertainty figures are **probability points**, and comparing them
directly made the same three-point error look negligible at 1.5 and fatal at 15.0. Expected
value moves by `net_odds` percent of stake per point of probability, so `doubt_band_pct`
multiplies the bands up rather than dividing the edge down. At odds of 8.0, three points of
model error is 24% of stake — which is most long-priced "edges" this model will ever report.

### 4. Nobody ever checked

Every guard above can be satisfied by a model that is simply bad. The only thing that
establishes otherwise is a settled record, so a model starts `PAPER`: it evaluates every
fixture completely and `size` refuses with `Unworthy` carrying what it WOULD have staked.
That accumulating record is what a person reads before promoting it, and `LIVE` without a
written `promoted_on` account is refused at construction.

## What the model actually computes, and what is deliberately absent

Attack and defence strengths relative to the league, a home advantage, and independent
Poisson over a truncated grid. Ordinary, and meant to be.

**The Dixon-Coles correction is NOT applied.** Independent Poisson is known to under-predict
draws and low-scoring scorelines, and Dixon-Coles corrects for it — but its parameter has to
be fitted to a competition's own history, and fitting it from nothing would produce a
plausible number with no data behind it. The under-prediction is instead declared here and
carried in `stated_error_pct`, so an edge on the draw has to clear a band that already knows
this is the weakest part of the arithmetic.

The truncated Poisson tail is **redistributed** rather than discarded. Discarding it makes
the three probabilities sum to slightly under one, and a probability compared against a book
price is a comparison where "slightly under" is a free edge.

Adjustment sizes — 4% off both sides above 30 km/h of wind, 3% above 5mm of rain, 6% per
key absentee capped at three, 2% per day of rest advantage — are judgement rather than
measurement, and each is stated where it is applied so a reader can see that from the code
rather than from a paper nobody has. The absentee cap is the important half: a fourth and
fifth absentee do not keep subtracting linearly, and without it a long injury list produces
a team that cannot score.

**Not modelled, on purpose:** motivation, "must-win", momentum. Real, unmeasurable here,
and a feature that cannot be measured either drags every forecast toward the mean or gets
dropped from the average and flatters it.

## The sources, and the gap that decides how good this can be

| source | key | what it gives | what it does not |
|---|---|---|---|
| The Odds API | free tier, **shared with the arb lane** | the prices to disagree with | nothing about the fixture |
| football-data.org | free | league tables → attack and defence | expected goals, shots, anything about fitness |
| open-meteo | **none needed** | wind, rain, temperature at the ground | anything indoors |
| team news | **there is no source** | — | the biggest input a book prices |

That last row is the honest reason to expect a book to beat this model more often than not.
There is no free, structured, reliable feed of confirmed absentees; the sites that look like
one are scrapes of press conferences with no guarantee about accuracy or timing, and
confirmed line-ups appear about an hour before kick-off — after the prices worth taking have
moved. So `connectors/teamnews.py` reads what a person typed in, and every fixture with no
report is forecast as fully fit **and says so**.

## Team names, and the friction that is on purpose

The odds feed says `Manchester United`; football-data says `Manchester United FC`. Suffixes
are stripped by a short stated list; anything else is an alias a person records once.

Matching further than that automatically is where a system like this quietly goes wrong. A
fuzzy matcher that is right 95% of the time models the wrong team's goals one fixture in
twenty, with nothing downstream able to tell. So an unmatched name is `UNKNOWN` naming both
spellings — more annoying than a fuzzy match, in the direction that produces a question
rather than a wrong number.

## The cadence, which is set by the odds allowance rather than by the model

This lane and the arb lane buy the same h2h prices from the same key. The free tier is 500
requests a month and the arb lane at eight hours across two sports already spends about six
credits a day. A mispricing lane on the same cadence would double that to answer a slower
question: a fair-value model does not change between breakfast and lunch, and a fixture list
changes once a day.

So the cadence is 24 hours, `preflight` prints what both lanes spend together, and the lane
ships **disabled**. An exhausted key reports no opportunity, which is indistinguishable from
a quiet market for the rest of the month.

## What is still open

1. **Nobody has run this against a real book.** Every threshold here is reasoned rather than
   fitted, and the first honest thing to do with the lane is leave it PAPER for a season and
   read what it would have done.
2. **The league-goals prior is one number for every competition.** `GoalsModel`'s
   `league_goals_per_team` defaults to 1.4 and should come from the table being used —
   using one figure for the Premier League and a low-scoring league is a modelling error
   that would show up as a systematic edge on unders.
3. **Home advantage is 1.15 and is a number to fit rather than to trust.** It has been
   beaten down since 2020 and further by empty stadiums.
4. **Nothing records a forecast for later comparison.** The journal captures harvests, so
   the record exists in a form somebody can read; a purpose-built calibration file would be
   better and is what promotion out of PAPER should eventually be argued from.
