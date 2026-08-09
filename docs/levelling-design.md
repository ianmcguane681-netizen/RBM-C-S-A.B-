# Levelling: capital earned rather than granted

Designed 2026-08-08 with Ian, not yet built. The next session can pick this up from cold.

## What this is

Every lane sizes today as though it had always been right. `docs/next-work.md` has carried
this as an open question for weeks — *"a lane with zero settled outcomes sizes identically
to one with two hundred. Ian has been asked for the shape and has not specified one; do not
invent it."* This document is that shape, specified.

**A lane starts at level 1 with a small ring-fence. Settled outcomes earn it a higher
level. A higher level surfaces a recommendation to deploy more capital, which Ian accepts
or declines.** The system computes eligibility; a named human moves the money.

That split is not a courtesy. It is the same structure as `board verify --by <name>` and
`Breakers.reset` — the machine assembles the evidence, a person makes the judgement — and
it is what keeps a levelling system from being an automatic capital-allocation loop that
nobody authorised.

## What already exists

Almost all of it, which is why this is a small job.

- `Ringfence.starting_balance` is the lane's capital, and **every other limit is a
  percentage of it**: `per_position_limit`, `daily_loss_limit`, `deployed_limit`. Raising
  one number raises all of them, in proportion. A level is one number.
- That number comes from `settings["balance"]` in `data/reapers.json`, a file edited by
  hand. Deploying capital is *already* a manual act; levelling only decides when to
  recommend it.
- `OutcomeLedger.realised(lane)` returns a `Realised` carrying `profit`, `settled`,
  `staked`, `returned`, `void`, `open`, `unknown`, `readable` and `covers_the_whole_book`.
  Every input a level needs is on that object.
- `lib/journal.py` holds the run history, so "when did this lane reach level 2" has an
  answer that outlives a process.

Nothing needs a price source. Levels are computed from what came back, which is the one
money figure that needs no valuation — see the realised P&L section of `next-work.md`.

---

## Decision 1 — promotion is a human act, demotion is not

**Asymmetric on purpose.** A level rises only when Ian accepts it. A level falls on its own,
immediately, without waiting for him.

Every failure of the levelling machinery then errs toward less capital: a bug that fails to
promote costs an opportunity, a bug that fails to demote costs money. That is the
`CLAUDE.md` corollary — *fail toward stopping* — applied to sizing.

Promotion therefore refuses the automation prefixes, exactly as `Breakers.reset` does:

```python
levels.accept("stocks", to=3, by="Ian McGuane")   # refuses agent:, ai:, model:, ...
```

Demotion needs no author. It is a measurement, not a judgement.

## Decision 2 — promote on the pessimistic book, demote on the realised one

**This is the decision the whole design turns on.** `Realised.profit` sums SETTLED positions
only. A lane that closes its winners and leaves its losers open shows an excellent realised
figure forever, and it needs no bad intent to happen — losers are exactly what one is
slowest to close.

So the two directions read different books:

- **Promotion** computes profit with every OPEN and UNKNOWN position marked as a **total
  loss of its stake**. If the lane still clears the bar, the level is genuinely earned. An
  unknown outcome is not a zero, and for the purpose of granting more capital it must be
  assumed to be the bad case.
- **Demotion** uses the plain realised figure, which falls sooner.

Both directions are pessimistic in the direction that reduces capital.

**Any UNKNOWN position bars promotion outright**, regardless of arithmetic. A lane that
placed something and could not find out what happened has not demonstrated that it can
operate. That is a statement about what has been proven, not a penalty.

## Decision 3 — the ladder is config, and nothing in the code writes it

```json
"stocks": {
  "level": 1,
  "level_balances": [2000, 3000, 4500, 7000, 10000],
  "balance": 2000
}
```

`balance` stays the live figure the breakers read. `lib/levels.py` may **read** `level` and
`level_balances`; it must never write either, and it must never write `balance`. A module
that can raise its own ring-fence has automated capital deployment by the back door, and
that belongs on the never-automate list beside settlement equivalence.

Adding a sixth level must be appending to `level_balances` — never a code change. Nothing
hardcodes a `5`. The lane registry is the precedent: one place decides, everything else
derives.

## Decision 4 — the percentages tighten as the balance grows

A level is not only a balance. `per_position_pct`, `max_deployed_pct` and
`max_concurrent_positions` move with it, in the opposite direction:

| level | per position | deployed cap | concurrent |
|---|---|---|---|
| 1 | 25% | 75% | 4 |
| 2 | 20% | 70% | 5 |
| 3 | 15% | 60% | 6 |
| 4 | 10% | 50% | 7 |
| 5 | 5% | 40% | 8 |

Two reasons, and the second is the one that is easy to miss.

**A wide per-position percentage at level 1 is not the risk it appears to be** — the
absolute money is small — **but it is bad evidence.** At 40-50%, a promotion could rest on
two or three settled positions. This repository exists to refuse to conclude more than the
evidence carries; levelling on a three-position sample is a coin flip that got promoted.
The tighter percentage buys more, smaller data points, which is precisely what level 1 is
for.

**The deployed cap, not the per-position cap, is what generates evidence.** `Ringfence`
already refuses `per_position_pct > max_deployed_pct` with *"a single position would breach
the total cap, so the lane could never place anything"*. At the default 40% deployed cap,
25% per position fits **one** position at a time — the lane places one, waits weeks for it
to settle, places another, and twenty settled outcomes take years. Opening the deployed cap
to 75% at level 1 is what makes the ramp move at all.

The pleasant property: absolute risk per position stays roughly flat while the discipline
increases. If level 1 is $2,000 and level 5 is $10,000, capital grows 5× while position
size grows 1×.

## Decision 5 — level 1 has a mechanical floor, and it is not a risk-appetite number

`lib/stocks_reaper.py:382` does `shares = int(size.amount // price)` and refuses below one
share: *"a position too small to round to one share is too small to be worth the
position."* Fractional is deliberately not used.

So **the per-position limit must cover one whole share of the priciest watchlist name**,
and per-position is a percentage of the balance:

    minimum level-1 balance = share price ÷ per_position_pct

At 25%, that is 4× the priciest share. At 5% it would be 20×.

Watchlist prices on 2026-08-08: **ALAB $333.99**, **NET $302.01**, **CRDO $249.99**. ALAB
binds, so the floor is `334 ÷ 0.25` = **$1,336**.

| level 1 | per position | ALAB $334 | NET $302 | CRDO $250 |
|---|---|---|---|---|
| $1,336 | $334 | 1 (bare) | 1 | 1 |
| **$2,000** | **$500** | **1** | **1** | **2** |
| $2,800 | $700 | 2 | 2 | 2 |

**Do not sit on the floor.** At $1,336 the limit is $334.00 against a $333.99 share, so a
1% move produces a zero-share refusal and the lane stops finding anything it can size.
$2,000 is the recommendation.

**The deadlock this avoids, which must be named in the code:** a balance below the floor
gives a lane that cannot place, therefore cannot settle, therefore can never earn a
promotion. Permanently level 1, and — if nothing says so — indistinguishable from a lane
that is simply performing badly. `UNDER_MINIMUM_VIABLE` is its own state, and it names the
share price that binds.

## Decision 7 — capital returns in full before any profit comes out

Ian's rule, 2026-08-09, and it answers the gap this document had: everything here promotes
capital *upward* on performance and nothing ever described taking money *off the table*. A
system that only compounds hands it all back in the drawdown that eventually arrives.

> The stake or capital should always be returned in full before profit is taken out.

Read strictly, and per lane rather than per position. **A lane's withdrawable amount is what
it holds above its assigned capital, and nothing else:**

```
withdrawable = max(0, lane_equity - assigned_capital)
```

Per position would be the flattering reading and is wrong for the usual reason. A lane that
buys ten items, sells three at a profit and is sitting on seven unsold has "returned the
capital" on three of them, and paying out against that is paying out of capital while
calling it profit. The seven are the ones that decide whether the lane made money.

Two consequences worth stating rather than discovering:

- **A loss must be earned back before anything is withdrawable again.** If a lane drops to
  9,400 against 10,000 assigned, the first 600 of profit is capital repair and not gain.
  This is a high-water mark against assigned capital, which is the same shape as the
  pessimistic book above: it errs toward keeping money in the lane.
- **It composes with promotion rather than fighting it.** Promotion raises `assigned_capital`
  and therefore *raises the bar* for withdrawal — a lane promoted to a larger level has more
  capital to keep whole before it pays out. That is the right direction: a lane earning more
  capital is a lane being asked to hold more, not one being asked to distribute more.

Unresolved, and Ian's: whether withdrawal is a manual act he performs or something the
system proposes on a cadence, and whether an OPEN position counts against equity at cost or
at the pessimistic mark used for promotion. The second matters — marking OPEN positions as a
total loss would make almost nothing withdrawable, which is safe and possibly too safe.

## Decision 6 — a level earned on paper is not a level

The stocks lane has never met a real broker. Paper fills have no slippage, no partial
fills and no rejections, so outcomes settled against `paper` are not the same currency as
live ones. **Reset to level 1 at the paper→live transition** rather than carrying the
record across. `AlpacaCredentials.paper` already distinguishes them and `Position.source`
records how an outcome was known.

---

## The states

```
EARNED             the bar is cleared on the pessimistic book; awaiting a human
NOT_YET            the bar is not cleared, and what is outstanding is named
AT_RISK            the realised book has fallen far enough to demote
UNDER_MINIMUM      the ring-fence cannot buy one share of the binding name
NOT_APPLICABLE     this lane cannot place, so it cannot earn
INDETERMINATE      the ledger could not be read, so nothing is known
```

`NOT_YET` must never render as a verdict. A lane with nothing settled has not underperformed
— `Realised` already tests `NOTHING_SETTLED` before `COMPLETE` for exactly this reason, and
that ordering is the precedent to copy.

`INDETERMINATE` **blocks promotion and does not demote.** An unreadable ledger already stops
the lane through the existing breaker path — `Assembly` returns UNREADABLE and nothing can
place — so the lane is halted already, and demoting on top would lose an earned record to a
transient disk fault. State this in the docstring; it looks like an inconsistency with
"fail toward stopping" and is not, because the stopping has already happened elsewhere.

## The three lanes are not alike

**Crypto is `NOT_APPLICABLE`, permanently, and this is the point most likely to be got
wrong.** `connectors/chain_exec.py` has no key path, no signing library and no send method,
by design. The lane never places, so it never settles, so it sits at zero settled outcomes
forever. Rendering it as "level 1, 0 of 20" would show the worst-performing lane on the
dashboard for a lane that is structurally incapable of performing. That is the founding
defect — *unknown rendered as nothing* — pointed at a lane's reputation.

**Arb's level should probably not track P&L at all.** A true arb's edge does not grow with
evidence; its ceiling is what bet365 and Sky Bet will accept before they restrict the
account. Levelling arb on profit produces a lane that has "earned" more capital than it can
physically deploy. Its level wants to track *account health* — whether the books have
limited you — which is a different measurement and is **out of scope for this job**. Ship
arb at a fixed level with a stated reason rather than modelling it wrongly.

**Stocks is the lane this is for.** Note that a settled equity outcome takes weeks, so level
2 is months away, not days. Say so in the status output, so a slow ramp is not mistaken for
a broken one.

---

## Shape

```
lib/levels.py
    LEVEL_LIMITS: tuple[LevelLimits, ...]     per position / deployed / concurrent
    @dataclass(frozen=True, slots=True) class Assessment:
        lane, level, status, settled, needed, pessimistic_profit, blocking: tuple[str, ...]
    def assess(lane, ledger, settings, *, now) -> Assessment
    def accept(lane, to, by) -> ...           refuses the automation prefixes
```

`status.py` shows current level, next level, and exactly what is outstanding for it.
`positions.py --apply` is the natural moment to reassess, since that is when outcomes reach
the breakers. `lib/reaping.breakers_for` reads `level_balances[level - 1]` if present and
falls back to `balance`.

Keep `lib/levels.py` free of connector knowledge, as `docs/pricing-design.md` asks of
pricing. The binding share price for `UNDER_MINIMUM` is passed in, not fetched.

## Tests to write

Properties, not coverage.

- a lane with nothing settled reports `NOT_YET`, and `NOT_YET` is not a poor result
- a lane whose winners settled and whose losers sit OPEN is **not** promoted
- one UNKNOWN position bars promotion however good the realised figure is
- promotion refuses `agent:`, `ai:`, `model:`, `automation:`, `bot:`, `system:`
- demotion needs no author and happens without one
- an unreadable ledger blocks promotion and does not demote
- a ring-fence below one share of the binding name reports `UNDER_MINIMUM` naming the price
- a lane that cannot place reports `NOT_APPLICABLE`, never level 1 with zero outcomes
- `accept` does not write `data/reapers.json` — assert the file is byte-identical after
- adding a sixth entry to `level_balances` needs no code change *(add one, watch it work,
  remove it — the lane-registry test is the precedent)*
- every level's `per_position_pct` is ≤ its `max_deployed_pct`, so no level can construct a
  `Ringfence` that refuses to place

## What this job is not

- Not automatic capital deployment. Nothing writes `balance`.
- Not a sizing model. The level sets the ring-fence; `lib/sizing.py` still decides the
  position, and the volatility bound still overrides the risk limit when it is tighter.
- Not arb account-health tracking. Named above, deliberately deferred.
- Not a performance chart. That needs a stored time series and has its own staleness
  questions — the same carve-out `pricing-design.md` makes.

## Open inputs — Ian's, not the code's

1. **Level 1 for stocks.** The mechanical floor is $1,336 and the recommendation is $2,000.
   Ian has said this needs more discussion; do not pick it unilaterally.
2. **The top of the ladder** — the most a lane should ever run, whatever it proves. The
   intermediate steps interpolate.
3. **The bar itself** — how many settled outcomes and how much elapsed time earn a level.
   A starting proposal is 20 settled and 60 days for stocks, both required, but this is the
   number that decides how much money moves and it is his.

Five levels for now. More get installed if performance warrants it — which is why nothing
hardcodes the count.

## Rough size

Two to three hours, if the decisions above are taken as made rather than rediscovered. The
machinery it reads all exists; the work is the states and the guards.
