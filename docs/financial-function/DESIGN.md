# RBF-001 — The Allocation Function

*Design. No code yet.*

Everything built so far establishes what is true and refuses to claim more. Nothing
consumes it. `mandate.py` was the first half of the bridge — it answers *does this decision
permit this action?* — and it deliberately stops before the question a holder actually has,
which is *how much, and when do I get out?*

This document designs the piece that answers that, and the change to the review boards it
depends on.

It is **RBF-001**, not RBM-006, and the letter matters. An RBM is a methodology profile: it
reviews something and produces a verdict. This reviews nothing. It takes verdicts, prices,
a balance and a set of policies the holder chose in advance, and it allocates. Numbering it
alongside the boards would invite it to be read as one, and a board that allocated its own
capital would be marking its own homework in the most expensive way available.

---

## Part 1 — Price as admissible evidence

### The question

Can current and historical price enter the review boards as evidence, given the boards
produce no view on price?

**Yes.** A price is an observation. It happened, it can be pinned to a source, and it can be
re-derived by someone else — which is the entire admissibility test the boards apply to a
block height or an accession number.

But price is unlike every other evidence class here in three ways, and each needs a guard.

### Guard 1 — a price is not an address

A block height and an accession number are *addresses*. Hand one to a stranger and they
re-derive the identical value forever. A price is not: it needs **venue, instrument, side,
size and timestamp**, and it is only re-derivable while the venue keeps history.

So a price observation carries all five or it is not a price observation.

```text
PRICED          venue, instrument, side, size and timestamp all present
REFERENCE_RATE  a mid or index value with no size — usable for display, NOT for sizing
NOT_PRICED      one or more of the five is missing
```

`NOT_PRICED` is the third state, in the pattern this repository now uses everywhere:
`NO_VENUE_FOUND`, `NO_FUNCTION`, `NOT_CONFIGURED`, `UNREADABLE`. An absent price must never
render as a zero price, for the same reason an unread owner must never render as renounced.

### Guard 2 — a price with no size attached assumes infinite liquidity

The number everyone quotes is the one nobody can trade at. Mid-price at an instant is a
statement about the top of the book, and CG-05 already exists because that statement fails
at size: a position large enough to matter moves the price it is measured against.

`connectors/chain_costs.round_trip` already prices at *your* size rather than at the
headline. That is the model. Price evidence that cannot name a size is a `REFERENCE_RATE`
and may be displayed but may not feed sizing.

### Guard 3 — movement is one inference away from extrapolation

This is the one that decides whether the whole idea is safe.

> "Down 40% since May" is a fact.
> "Down 40%, therefore cheap" is a forecast wearing a fact's clothes.

Both sentences contain the same number. The second is the sentinel defect in its most
seductive form — a value read as meaning something it does not mean — and it is seductive
precisely because the factual half is genuinely well-sourced.

So the admissibility rule is a single line:

> **Price may enter a gate as a constraint. It may never enter as a signal.**

And the test for which one you have written is mechanical:

> **A gate that uses price honestly changes its output when price moves *against* the holder
> as well as for them.** A gate that only fires on cheapness is a signal.

Exit depth fires either way — a position gets harder to leave whichever direction the price
went. A moving-average crossover fires one way. That is the difference, and it is checkable
by reading the gate rather than by trusting its author.

### What this admits

All of these are constraints, and three of them already exist:

| | Uses price as | Status |
|---|---|---|
| exit depth / slippage at your size | how hard it is to leave | CG-05, built |
| round-trip cost as a fraction of position | what the trade costs to do at all | built |
| venue divergence | two books disagreeing, right now | RBM-005, built |
| realised volatility over a stated window | a measured dispersion that bounds size | **new** |
| filed-vs-market cross-check | shares × price against filed assets and liabilities | **new** |

The last deserves a note. It does not say cheap or dear. It says *this is what the market is
currently paying per filed dollar of assets*, both halves cited — one to an accession
number, one to a venue and timestamp. A reader draws their own conclusion, and the board has
stated two facts and no inference. That is exactly the register the boards already work in.

Realised volatility is admissible because it is arithmetic on observations that already
happened. It is **not** a prediction of future volatility, and any finding phrased as though
it were is the defect. Its only permitted use is bounding position size.

### What this forbids

- Any gate whose finding text makes a directional claim about future price.
- Any severity assigned on price alone. Price never makes a finding worse by itself.
- Indicators, crossovers, patterns, momentum. Those are a strategy; a strategy is a
  forecast; a forecast has no place in an evidence package.

Enforcement mirrors the existing tests that assert `NO_VENUE_FOUND` never collapses into
"no liquidity": a test over the gate corpus asserting no price-fed gate emits directional
vocabulary.

### The cost of adding it

Gates live in hash-pinned packages. Adding `CG-07` and `SG-07` means a new `PROFILE.json`
checksum, a new `MANIFEST.json` root, a methodology version bump, and reviewer specs for the
new gate.

It does **not** retroactively apply to `RBM003-USDC-0001` or `-0002`. Those were decided
under the profile as it stood, and they stay decided under it. That is correct — a published
decision that silently acquired a gate it was never reviewed against would be a fabricated
record — but it is worth saying out loud so nobody expects the exported bundles to change.

---

## Part 2 — The allocation function

### The one rule

> **It can refuse, size, or exit. It can never originate.**

A reason to buy must come from outside it. The boards cannot produce one — they establish
hygiene, and hygiene is not an edge. If the allocation function could originate, it would
have to hold a view on price, and every honest thing in this repository would become
decoration around that view.

The holder supplies the thesis. The function supplies: whether it is permitted, how much,
what it costs, and what obliges an exit.

### Shape

```text
    thesis (a named human, with reasoning)
         │
         ▼
    ┌─────────────────────────────────────────────────┐
    │  1  PORTFOLIO STATE     balance, positions,      │
    │                         basis, exposure          │
    │  2  ELIGIBILITY         mandate.evaluate()       │──▶ REFUSED / EXPIRED
    │  3  SIZING              risk limit ∧ volatility  │    / INDETERMINATE
    │                         ∧ exit depth             │
    │  4  COST FLOOR          round trip vs position   │──▶ UNECONOMIC
    │  5  OBLIGATIONS         what a monitor event     │
    │                         compels                  │
    └─────────────────────────────────────────────────┘
         │
         ▼
    6  EXECUTION ADAPTER  →  paper  →  broker  →  chain
```

### 1. Portfolio state

Append-only, like everything else here. Balance, open positions, cost basis, realised and
unrealised, exposure per asset and per lane.

One rule with teeth: **current value is never stored, only derived** — positions × a priced
observation. And when the price is unreadable the value is `UNPRICED`, not zero.

A stored value would go stale silently. A zero would show the portfolio shrinking the moment
a feed died, which is the sentinel defect pointed directly at the number the holder cares
about most.

### 2. Eligibility

A thin wrapper over `rbe_runtime/mandate.py`. It adds no judgement; it applies the existing
one to every held position and every proposal, and it re-applies it on a schedule because
`DriftObservation` and decision age both move without anyone acting.

Output per asset is the mandate's own vocabulary: `PERMITTED` / `REFUSED` / `EXPIRED` /
`INDETERMINATE`. `INDETERMINATE` stays distinct from `REFUSED` all the way to the surface —
"the decision says no" and "I cannot tell what it says" call for different responses from a
human, and merging them loses the one that needs attention.

### 3. Sizing

The substantive new work. Four inputs, and the size is the **minimum** of what each allows:

```text
free balance × per-asset risk limit      your rule
realised volatility over a stated window  the market's recent dispersion
exit depth at the candidate size          CG-05: what you can actually sell
cost floor                                below this the trade is not worth doing
```

The output names **which constraint bound it**:

```text
sized to €4,200
  bound by: exit depth at 1.8% slippage
  your risk limit would have allowed €11,000
```

That distinction is the whole value of the panel. "My rules are holding me back" and "the
market cannot absorb me" are different situations calling for different responses, and a
single number hides which one you are in.

### 4. Cost floor

`connectors/chain_costs.round_trip` for chain assets; broker commission plus spread for
equities. A trade whose round trip exceeds a stated fraction of the position is refused as
uneconomic **regardless of the thesis**, because a thesis that needs to overcome 4% of
friction before it is even wrong is a different proposition from the one that was argued.

### 5. The obligation table

This is what finally makes the monitor worth running, and it is the part to get right,
because it is the part that operates when the holder is least calm.

Each row is a **policy chosen in advance**, not a judgement made in the moment:

| Monitor event | What it means | Obligation |
|---|---|---|
| `implementation` changed | every fact reviewed was about different code | position under re-review; no additions; exit or re-review within N days |
| `admin` changed | who can swap the code changed | same |
| `paused` → true | you may be unable to exit at all | freeze, alert loudly, no new entry |
| `owner` / `masterMinter` changed | authority moved | material; re-review before adding |
| restatement on a holding | a figure you relied on was refiled | material; re-review before adding |
| tag change on a holding | your series may be silently stale | re-read before relying on it |
| mandate `EXPIRED` | the decision aged out | no new entry; existing position held, flagged |
| `UNREADABLE` | *nothing* | **no obligation** — a failed read is not an event |

That last row is the one that would be got wrong by default, and it is the reason the ledger
distinguishes five states rather than three. A monitor that liquidated a position because a
node timed out would be a catastrophe built out of an unhandled sentinel, and this
repository has produced that class of bug six times in less consequential places.

The N in "within N days" is the holder's, set once, recorded, and not negotiable in the
moment — which is the entire point of writing it down beforehand.

### 6. Execution adapter

Downstream only, and dumb on purpose. It receives a sized, permitted, costed instruction and
places it. It has no strategy and never sees the boards.

Take an existing bot for *this layer only* — `ccxt` for venues, a broker SDK for equities.
Adopting an existing bot's **strategy** means adopting its backtest, and backtests are the
richest known source of exactly the defect this repository keeps meeting. Execution
plumbing is months of unglamorous, well-solved work worth taking. Strategy is not.

Three modes, in order: `PAPER` → `MANUAL_CONFIRM` → `LIVE`. Live is a long way off and
requires the holder to turn it on explicitly, per lane.

---

## The honest first version

`mandate.evaluate()` has never returned `PERMITTED`. RBM-003 §11 states that a review under
it can never authorise a transaction, so the authority condition refuses every time.

**So the first fully wired version of this refuses every crypto trade.** A bot connected, a
balance loaded, sizing computed, and a refusal at the gate every time.

That is the correct first milestone and it should not be worked around. A system whose first
act is to decline is a system whose gate is real. The way it eventually says yes is a board
profile that grants authority to authorise, written deliberately and reviewed as such — not
by loosening the check that currently works.

Stocks are the lane where a `PERMITTED` can honestly arrive first: RBM-004 has no
equivalent of §11, the evidence needs no key material, and the worst failure is a bad order
rather than a drained wallet.

## Build order

1. Portfolio state and the append-only ledger. No prices, no decisions. Pure bookkeeping.
2. Eligibility wrapper over `mandate.py`, applied across a portfolio rather than one action.
3. Price evidence: the `PRICED` / `REFERENCE_RATE` / `NOT_PRICED` triple and a connector.
4. Sizing, with the binding constraint named in the output.
5. The obligation table, wired to `monitor.py`'s exit code and change list.
6. `PAPER` execution against equities only.

Steps 1, 2 and 5 need no price feed and no credentials at all. That is where to start.

## What this will never do

Pick an entry. Time anything. Hold a view on direction. Decide the thesis. Tell you what to
buy.

It tells you whether you may, how much, what it costs, and when to leave.
