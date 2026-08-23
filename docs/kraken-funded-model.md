# The Kraken funded account — a paper model

**Built 2026-08-23. Nothing here has met a venue, a key or a balance.** It is a simulator
and a rulebook, and the only thing running it can cost is electricity.

```bash
python funded_model.py                 # the whole comparison, ~30 seconds
python funded_model.py --paths 20000   # tighter numbers, a few minutes
python funded_model.py --strategy thesis-gated --sizes 0.5,1,1.5,2
```

Every figure below came from `python funded_model.py --paths 8000` at the default seed and
can be regenerated from that line. That is deliberate: a number nobody can reproduce is a
number nobody should act on.

## The terms are not confirmed, and that is the first thing to fix

Nobody has read the provider's published rules and put their name to them. The model runs
on the industry-standard shape — a $10,000 seat at $500, an 8% target, a 6% lifetime floor,
a 3% daily limit, 45 days, and Ian's stated 80/20 split — and it says **TERMS UNCONFIRMED**
at the top of every report until somebody passes `--confirmed-by "Name"`. `confirm_terms`
refuses the automation prefixes for the same reason `lib/arb.py` refuses them on a
settlement equivalence: stating that two documents say the same thing is a reading, and a
reading is somebody's.

Not knowing the exact floor was not a reason to stop, because section 3 of the report runs
the whole plausible range instead of guessing a point inside it. As it turns out the answer
does not move between a 4% floor and a 12% one for the strategy that wins, so **the exact
term does not need to be known before deciding whether to buy a seat.** It very much needs
to be known before choosing a position size.

## What the model found

Ordered by how much I would still believe if the per-trade estimates turn out to be wrong.
The first three are arithmetic on the rulebook and survive a bad estimate. The last two are
consequences of numbers a person guessed and should be read as illustrations of a mechanism
rather than as forecasts.

### 1. Whether the account is spot or perpetual futures decides more than the strategy does

This is the first question to put to the provider, ahead of the floor, the target and the
split. Fees look negligible as a percentage of notional and are decisive as a fraction of
risk, and the conversion is one line:

    cost_r = (2 x fee_per_side + 2 x slippage_per_side) / stop_distance

A spot scalper working a 0.4% stop at Kraken's entry taker fee pays **1.35R a round trip**.
It must make 1.35 units of risk to stand still, which no win rate on a symmetric payoff
achieves. `spot-scalp` in the report loses 15R a day and breaches the floor in 100% of
8,000 simulated accounts — and it is refused before any simulation runs, by the sign of its
edge. On perpetuals the same trade costs about 0.3R and the strategy is merely difficult.

The same arithmetic sets a floor under how tight a stop can be. **At entry-tier spot fees,
symmetric-payoff scalping needs roughly a 60% hit rate merely to break even**, and a
strategy quoting 55% is describing a loss.

### 2. Position size has an interior optimum, and overshooting is far worse than undershooting

Too small and the clock beats you; too large and the floor does. Both failures are total,
so there is a size to find rather than a direction to push in:

| risk/trade | pass | lost to floor | lost to clock | net per account |
|---|---|---|---|---|
| 0.25% | 0.0% | 0.0% | 100.0% | -500 |
| 0.75% | 28.5% | 0.0% | 71.5% | 86 |
| 1.50% | 93.4% | 0.0% | 6.3% | 3,327 |
| **2.00%** | **97.8%** | **0.0%** | **2.1%** | **4,842** |
| 3.00% | 80.8% | 0.0% | 0.1% | 2,295 |

The curve is not symmetric and the asymmetry is the point: **a breach costs the fee AND the
account, a timeout costs only the fee.** Undershooting wastes $500 and a month;
overshooting destroys the seat. When the estimate is uncertain — and it always is — the
smaller size is the correct error.

### 3. A payout can breach a winning account, and the term that decides it is not the headline one

Withdrawing profit lowers the balance. Whether the loss floor comes down with it is a term,
and most people read the split and not that line. Identical accounts, identical strategy,
one term different:

| | net per account | funded account life |
|---|---|---|
| floor follows the money out | 4,842 | 180 days (the whole horizon) |
| floor stays at the peak | 431 | **28 days** |

That is a factor of eleven in what the trader keeps, from a clause about withdrawals. The
mechanism is worth stating precisely, because it does not always bite:
`test_a_short_payout_cycle_does_not_spring_the_trap` pins the boundary. **The trap needs
profit per payout cycle to exceed the lifetime allowance.** Make $900 against a $600
allowance and then withdraw to the starting balance, and the floor — left at the $10,900
peak — now sits at $10,300, above the $10,000 you are standing on. You are breached by your
own payout, with no losing day in the series. Withdraw every $300 instead and the peak
never gets far enough ahead for the floor to overtake the balance.

So the payout schedule is a risk parameter, not an administrative preference, and on a
trailing floor that does not reset, **withdraw little and often**. On a static floor the
term is irrelevant and any schedule is safe. Read which one is on offer.

### 4. The strategies that pass are not the ones with the biggest edge

`momentum-swing` has the largest edge per day of any candidate (+0.38R) and finishes fourth
by what the trader keeps. It loses 18.9% of accounts to the daily limit, because it holds
overnight and **a stop you have to be awake to apply does not bound a position held through
the night.** The model refuses to let a profile claim both: `holds_overnight=True` with a
self-imposed daily stop raises at construction, so nothing can quietly bank protection it
does not have.

`funding-carry` is the same lesson from the other end. It wins 88% of the time and passes
4.7% of challenges, because +0.037R a day cannot cover 8% in 45 days at any survivable
size. It is a fine way to run money and a bad way to pass a challenge — those are different
objectives and the account only rewards one of them.

### 5. On the estimates as given, one candidate dominates — and its estimate is the shakiest

`cross-venue-arb` tops the table at 97.8% pass and $4,842 per account. **That result is
almost entirely a restatement of its assumed 96% win rate**, which is a number somebody
typed, not one this repository has measured. What is worth taking from it is the shape
rather than the level: a strategy that is rarely wrong fails a challenge on the CLOCK, not
the floor — 2.1% of its accounts ran out of days and none touched the drawdown limit — and
that is a completely different failure to engineer against. For it you buy more opportunity
or a longer deadline. You never buy a bigger size.

`lib/arbfind.py` already does this arithmetic for bookmakers. What it does not have is a
crypto venue feed, and until it does, the 96% is an aspiration.

## What this is not

These are simulated returns from an assumed per-trade distribution. **Nothing here is
evidence that any of these strategies has an edge.** Every win rate and payoff in
`lib/funded_kraken.py` is somebody's estimate; the model computes their consequences
exactly, so a wrong estimate produces a wrong answer in the same direction with more
decimal places. It is the same distinction the reapers draw when they say the audit chain
is what is lost: a working number is not a reviewed one, and a simulated number is not an
observed one.

Not modelled, every one of which pushes against the trader:

    slippage that widens exactly when the strategy needs it not to
    a stop gapping through on a Sunday wick
    the exchange unreachable with a position open
    the overnight gap itself — a held position resolves in the next day's trades rather
        than jumping the account through its floor while nobody is at the screen
    correlation ACROSS days, so a bad week is only ever four independent bad days
    any decay in the edge over the horizon

Treat every pass rate here as an optimistic bound rather than a forecast.

## Blocked on the provider, not on code

| | what | why it matters |
|---|---|---|
| 1 | **Spot or perpetual futures?** | decides which strategies are possible at all — see finding 1 |
| 2 | **Does the loss floor reset after a payout?** | worth a factor of eleven — see finding 3 |
| 3 | The lifetime floor %, target %, daily %, deadline, seat price | run `--confirmed-by` once read; the model already spans the plausible range |
| 4 | Is the floor static or trailing, and measured on the close or the intraday high | `TRAILING` vs `TRAILING_LOCKED` vs `STATIC` are three different games |
| 5 | Minimum trading days, and what counts as one | a day flat in cash is not one, and the model counts it that way |

## Where it lives

```
lib/funded.py         the rulebook and the day-by-day walk. Knows nothing about Kraken.
lib/funded_sim.py     the paper model: profiles, correlated days, campaigns. Stdlib only.
lib/funded_kraken.py  fees, the unconfirmed terms, the seven candidates, the sweeps.
funded_model.py       the CLI that prints the five sections.
tests/test_funded*.py 83 tests
```

The separation is load-bearing. The venue's fee schedule and the programme's terms are the
two things most likely to be wrong today and corrected next week, and they are correctable
in one file without touching a line of the maths.

## Deliberately absent

**No connector, no key path, no order.** This lane cannot place anything and nothing here
moves toward letting it. `lib/operating.py` is not wired to it and should not be until
there is a confirmed rulebook and a measured edge rather than an estimated one.

**No fourth lane in `lib/reaping.LANES`.** A funded account is a venue and a set of
constraints, not a source of opportunities — whatever eventually trades it would be one of
the existing lanes operating under a tighter ring-fence, and `lib/breakers.Ringfence`
already expresses most of these limits. Deciding that is a design question, not a task, and
it should be answered after the terms are known.
