# The Kraken funded account — a paper model

**Built 2026-08-23, revised the same day when two terms came back.** Nothing here has met a
venue, a key or a balance. It is a simulator and a rulebook, and the only thing running it
can cost is electricity.

```bash
python funded_model.py                                   # the whole comparison
python funded_model.py --paths 20000                     # tighter numbers
python funded_model.py --strategy momentum-swing         # sections 2-4 for one candidate
python funded_model.py --daily none                      # if there is no daily rule
```

Figures below come from `--paths 8000` at the default seed, except section 4's, which are
`--paths 2500 --strategy momentum-swing`. Each can be regenerated from the line that made
it: a number nobody can reproduce is a number nobody should act on.

## What is known, what is assumed, and the difference between second-hand and confirmed

Two terms came back on 08-23, from a search summary rather than Kraken's own rules page:

- **The venue is Kraken Pro perpetual futures**, not spot, with up to 50x leverage.
- **The drawdown is a static maximum pinned to the initial balance.** 8% of a $10,000
  account puts a permanent floor at $9,200 that neither rises with the peak nor falls when
  profit is withdrawn.

Both are now the defaults. Neither is *confirmed*: an AI-written search summary is a reading
of a document by something that cannot be asked what it meant, so `terms_confirmed_by` stays
empty and every report still prints **TERMS UNCONFIRMED**. That is not fastidiousness about
provenance. Static and trailing floors invert the correct withdrawal policy — see the
correction below — and which one is on offer is exactly the kind of detail a summary
flattens.

Still assumed: the profit target, the deadline, the minimum trading days, the seat price,
and **whether there is a daily loss limit at all**. That last one is now the most valuable
unknown in the whole model, for reasons that are finding 4.

## A correction

The first version of this document reported that the payout/floor clause was worth a factor
of eleven. **That is a property of trailing floors only**, and with the static answer above
it does not apply here. A floor left where the peak put it can rise above the post-payout
balance and breach an account that never had a losing day; a floor pinned to the starting
balance has nothing to rise from.

The code had this right from the first commit —
`test_a_static_floor_is_indifferent_to_the_payout_term` — and the summary of it did not.
There are now four tests under `TestThePayoutTrapIsAPropertyOfTRAILINGFloorsOnly` where
somebody will see the distinction, and `ChallengeRules.describe()` refuses to print the
clause at all on a static floor rather than printing it as satisfied.

## What the model found

Ordered by how much survives the per-trade estimates being wrong. The first four are
arithmetic on the rulebook. The last two are consequences of numbers a person guessed and
should be read as illustrations of a mechanism rather than as forecasts.

### 1. The perpetuals engine is what makes any of this possible

Fees look negligible as a percentage of notional and are decisive as a fraction of risk:

    cost_r = (2 x fee_per_side + 2 x slippage_per_side) / stop_distance

A scalper working a 0.4% stop pays **1.35R a round trip on spot** and about **0.3R on
perps**. On spot it must make 1.35 units of risk to stand still, which no win rate on a
symmetric payoff achieves. `spot-scalp` is kept in the candidate table as the
counterfactual: it loses 15R a day and breaches the floor in 100% of 8,000 accounts, and it
is refused before any simulation runs, by the sign of its edge alone.

The same arithmetic sets a floor under how tight a stop can be. At entry-tier **spot** fees,
symmetric-payoff scalping needs roughly a 60% hit rate merely to break even. On perps the
same strategy is merely difficult. This was the question worth asking first, and the answer
was the good one.

### 2. Position size has an interior optimum, and overshooting is far worse

| risk/trade | pass | lost to floor | lost to clock | net per account |
|---|---|---|---|---|
| 0.25% | 0.0% | 0.0% | 100.0% | -500 |
| 0.75% | 28.5% | 0.0% | 71.5% | 86 |
| 1.50% | 93.5% | 0.0% | 6.2% | 3,328 |
| **2.00%** | **97.9%** | **0.0%** | **2.1%** | **4,848** |
| 3.00% | 80.8% | 0.0% | 0.1% | 2,295 |

Too small and the clock beats you; too large and the floor does. Both failures are total,
and the curve is not symmetric: **a breach costs the fee AND the account, a timeout costs
only the fee.** When the estimate is uncertain — and it always is — the smaller size is the
correct error.

### 3. Retained profit defends against the floor and not against the daily limit

This is what replaced the withdrawn finding, and it is the live question on a static floor.
Money left in the account widens the permanent gap to a floor that never moves, and that gap
is what a strategy spends during a bad week. It widens *nothing* against a daily allowance
computed as a percentage of the account **size** — tomorrow's allowance is the same number
of dollars whether the balance is $10,000 or $14,000.

The same strategy, the same seed, the only difference being whether a daily rule exists:

**With a 3% daily limit** — retention is pure cost:

| retain | net | floor breaches | daily breaches |
|---|---|---|---|
| **0%** | **946** | 287 | 1,344 |
| 50% | 770 | 103 | 1,485 |
| 90% | 28 | 70 | 1,509 |

**With no daily limit** — retention is a purchase:

| retain | net | floor breaches | daily breaches |
|---|---|---|---|
| 0% | 2,934 | 1,126 | 0 |
| **25%** | **3,172** | 725 | 0 |
| 50% | 3,140 | 438 | 0 |
| 90% | 1,399 | 188 | 0 |

Retention cuts floor breaches hard in both tables — 287→70 and 1,126→188 — so the buffer
argument is *correct*. It simply does not matter when something else is doing the killing.
So: **read the two breach columns and let them choose the retention.** Where a strategy
barely breaches at all the report says `NOT DECIDABLE FROM THIS STRATEGY` rather than
reading a rule off thirteen events.

This is why **whether there is a daily loss limit is now the question to put to the
provider**, ahead of the target and the seat price. It flips the withdrawal policy from
"take everything" to "leave a quarter in".

### 4. The strategies that pass are not the ones with the biggest edge

`momentum-swing` has the largest edge per day of any candidate (+0.38R) and finishes fourth
by what the trader keeps. It loses 21% of accounts to the daily limit, because it holds
overnight and **a stop you have to be awake to apply does not bound a position held through
the night.** The model refuses to let a profile claim both: `holds_overnight=True` with a
self-imposed daily stop raises at construction.

`funding-carry` is the same lesson from the other end. It wins 88% of the time and passes
4.7% of challenges, because +0.037R a day cannot cover 8% in 45 days at any survivable size.
It is a fine way to run money and a bad way to pass a challenge — different objectives, and
the account rewards only one.

### 5. On the estimates as given, one candidate dominates — and its estimate is the shakiest

`cross-venue-arb` tops the table at 97.9% pass and $4,848 per account. **That is almost
entirely a restatement of its assumed 96% win rate**, which is a number somebody typed, not
one this repository has measured. Take the shape rather than the level: a strategy that is
rarely wrong fails a challenge on the **clock**, not the floor — 2.1% ran out of days, none
touched the drawdown limit — and that is a completely different failure to engineer against.
For it you buy more opportunity or a longer deadline. You never buy a bigger size.

`lib/arbfind.py` already does this arithmetic for bookmakers. It has no crypto venue feed,
so until it does, the 96% is an aspiration.

### 6. Leverage does not bind, which is worth having checked

The widest candidate needs 2x the account in notional against a 50x cap. Risk-based sizing
says nothing about the notional required to express that risk, so `implied_leverage()`
computes it rather than assuming it is fine, and a profile that does not state its stop
returns `None` — not computable — rather than zero.

## What this is not

These are simulated returns from an assumed per-trade distribution. **Nothing here is
evidence that any of these strategies has an edge.** Every win rate and payoff in
`lib/funded_kraken.py` is somebody's estimate; the model computes their consequences
exactly, so a wrong estimate produces a wrong answer in the same direction with more decimal
places. It is the distinction the reapers draw when they say the audit chain is what is
lost: a working number is not a reviewed one, and a simulated number is not an observed one.

Not modelled, every one of which pushes against the trader:

    slippage that widens exactly when the strategy needs it not to
    a stop gapping through on a Sunday wick
    the exchange unreachable with a position open
    the overnight gap itself — a held position resolves in the next day's trades rather
        than jumping the account through its floor while nobody is at the screen
    correlation ACROSS days, so a bad week is only ever four independent bad days
    any decay in the edge over the horizon

Treat every pass rate here as an optimistic bound rather than a forecast.

## Open with the provider

| | what | why it matters |
|---|---|---|
| 1 | **Is there a daily loss limit, and at what?** | flips the withdrawal policy — finding 3 |
| 2 | Profit target %, deadline, minimum trading days, seat price | assumed; section 3 shows the verdict holds across the floor's plausible range |
| 3 | Confirm the two second-hand terms at the source | perps and the static floor both change the answer enough to read directly |
| 4 | Is the daily allowance a % of account size or of that day's opening equity | decides whether it shrinks as the account shrinks |
| 5 | What counts as a trading day | a day flat in cash is not one, and the model counts it that way |

## Where it lives

```
lib/funded.py         the rulebook and the day-by-day walk. Knows nothing about Kraken.
lib/funded_sim.py     the paper model: profiles, correlated days, payout policy, campaigns.
lib/funded_kraken.py  fees, the terms, the seven candidates, the four sweeps.
funded_model.py       the CLI that prints the six sections.
tests/test_funded*.py 100 tests
```

The separation is load-bearing. The venue's fee schedule and the programme's terms are the
two things most likely to be corrected next week, and they are correctable in one file
without touching a line of the maths — which is exactly what happened on the day it was
built.

## Deliberately absent

**No connector, no key path, no order.** This lane cannot place anything and nothing here
moves toward letting it. `lib/operating.py` is not wired to it and should not be until there
is a confirmed rulebook and a measured edge rather than an estimated one.

**No fourth lane in `lib/reaping.LANES`.** A funded account is a venue and a set of
constraints, not a source of opportunities — whatever eventually trades it would be one of
the existing lanes under a tighter ring-fence, and `lib/breakers.Ringfence` already expresses
most of these limits. That is a design question to answer after the terms are known.
