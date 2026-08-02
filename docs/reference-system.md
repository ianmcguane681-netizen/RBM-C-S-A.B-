# A reference system, and what to take from it

Seven screenshots of somebody else's build, sent 2026-08-02 as "what an end goal could
ideally look like". Worth writing down properly, because it is specific enough to argue
with and there is a lot in it worth copying.

## What it is

Named agents, running on cycles, across five modules:

```
RESEARCH LAB   idea pipeline: PROPOSE → VERDICT → EXECUTE, 48h cycles
               PENDING VERDICT 9 · APPROVED 0

MARKETS        "THE SHOWDOWN — STOCKS vs CRYPTO vs SPORTS"
               BOLT (crypto) · SAGE (stocks) · ACE (sports)
               paper-trade arc, positions, full trade history with reasons

SCOUT          signal intelligence, software opportunity feed
               READY TO APPROVE 2 · BORDERLINE 0 · SIGNALS SCANNED 203 · CYCLES 54

FORGE          MVP builder, ships SCOUT's approved problems as Vercel products
               WAITING TO BUILD 2 · AWAITING YOUR CALL 0 · LIVE PRODUCTS 3
               PREVIEW 0 · LIVE 3 · QUEUE 2 · KILLED 0
```

Plus a per-instrument detail view: price, candles, RSI, MACD, volume, news, and a verdict.

## Five things to take, more or less unchanged

**1. "WHAT WOULD FLIP ME."** The best single idea in the whole set.

> `→ BUY if close above SMA20 $154.08 on >1.5x avg volume, RSI < 65`

A stated, falsifiable condition that would change the verdict, committed to *before* the
condition occurs. That is not a forecast — it is a pre-commitment, and it is exactly what
`lib/sizing.py`'s obligation table already does for monitor events. Extending it so every
verdict carries its own flip condition is a small change and a large improvement, because
a verdict with no stated way to be wrong is not a verdict.

**2. "AWAITING YOUR CALL" as a first-class counter.** The human-in-the-loop queue, on the
dashboard, with a number on it. This repository has exactly that problem — three boards at
`GOVERNANCE_VALIDATION` and six reports that sat unverified across a container death — and
solved it nowhere on a screen. `status.py` should carry this count.

**3. `KILLED · 0` and `critic iterations: 3`.** Recording what did *not* ship and how many
revisions it took. Most dashboards show only successes; a `KILLED` counter beside `LIVE` is
the honest denominator, and this repository's `NO_ARB`, `SINGLE_BOOK` and `INCOMPLETE_BOOK`
statuses exist for the same reason.

**4. A trade history where every entry carries the reason recorded at the time.**

> `Stop-loss -4.20%. Cost $82.10 → current $78.65 = -$3.45/unit. Hard rule: no exceptions.`

`Entry.reason` in `lib/portfolio.py` is already this field. What the reference does better
is *display* it, so the reason travels with the position rather than living in a database.

**5. `PENDING VERDICT 9 · APPROVED 0`.** A pipeline showing that nothing has been approved
yet, prominently, without embarrassment. Structurally identical to this repository's mandate
never having returned `PERMITTED`, and it is the right way to show it.

## Three things not to take, with reasons

**1. `SELL · CONF 3/5`.** A confidence score. The argument against is in
`lib/candidates.py` and does not weaken here: a scalar over heterogeneous inputs treats a
disqualifier as a deduction, and has no honest value for an input that was not measured.

**2. The judgement layer is technical analysis.** SMA20/SMA50 crossovers, RSI, MACD,
"relative strength leader in a down week". These are forecasts — legitimate ones that many
people trade on, and nothing in them is *verifiable* in the sense this repository means. A
board can establish that a filing says what it says and a contract does what it does. It
cannot establish that a moving-average crossover predicts anything, and neither can anyone
else without a backtest, which is the input class already refused.

**3. SCOUT's weighted signal bars** — FREQUENCY, REVENUE, AVAILABILITY, MARKET GAP rendered
as four filled bars. Same scoring model, moved into opportunity discovery.

## The number on the screen that matters most

The sports agent's own header reads **-16.50%**, and its bankroll shows **$8,350.33 from
$10,000 started**. The crypto and stocks agents are at roughly break-even on a paper arc —
$10,091.67 and $10,109.63 from $10,000, over 43 and 25 days.

That is the reference system reporting honestly on itself, and it deserves to be read rather
than skipped past. Betting is one of our lanes. The most sophisticated-looking module in the
set is the one that lost money, and it lost it while displaying confident per-bet reasoning
for every one of twenty-nine settled bets.

It is also, in fairness, a **paper** arc and says so on its face: *"AI paper-trading
experiment. Not real money. Not financial advice."* The system is honest about what it is.

## What this suggests building

**The shape is right and the judgement layer is the disagreement.** Those are separable, and
taking one without the other is the whole opportunity:

- named agents on cycles, with visible queues — **take it**
- a verdict that states what would flip it — **take it, it is the best idea here**
- an "awaiting your call" counter — **take it**
- killed and revision counts beside live ones — **take it**
- reasons displayed with positions — **take it**
- a confidence score deciding the verdict — **do not**
- indicators as the evidence base — **do not**

A dashboard that looks like this, where every figure is either sourced to a primary record
or explicitly `UNPRICED` / `INDETERMINATE` / `NOT_ASSESSED`, is a better product than
either half alone. The reference has the ergonomics this repository lacks. This repository
has the discipline the reference does not.
