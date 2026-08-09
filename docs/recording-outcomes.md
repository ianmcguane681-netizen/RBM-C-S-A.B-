# Recording what happened, designed

Designed 2026-08-09, not yet built. The input surface for the return leg: how a result gets
from the world into `data/outcomes.json`, where the breakers read it.

## Why this is not a convenience feature

Three of the six circuit-breaker controls — the daily loss limit, the losing run, and the
previously-tripped check — are computed entirely from settled results. A lane nobody records
is a lane whose limits read zero forever and which permits the fifth losing position as
cheerfully as the first. That was the state of this repository until `lib/outcomes.py`
existed, and it is the state any lane returns to the moment recording becomes a chore.

Today the only way in is the command line:

```bash
python positions.py --placed arb "Everton v Brighton" --staked 499.98
python positions.py --settle POS-abc123 --returned 528.85
```

That is the right interface for a person at a desk and the wrong one for every other moment
this actually happens in: at a card fair with a phone, at a match, on a Sunday evening with
twelve items to reconcile. **An interface people skip is a breaker reading zero**, and the
failure arrives disguised as a quiet week.

So this document designs the surface. It does not lower the bar for what gets recorded — it
raises the number of places the same honest record can be made from.

## The states, and why two buttons is the wrong shape

The tempting design is *I have bought* and *I have sold*. It is wrong in a specific way
that this repository has already been bitten by: it flattens outcomes that are not alike.

`positions.py` takes four verbs, and each exists because something different is true:

| verb | what it means | why it cannot fold into another |
|---|---|---|
| `--placed` | it went on, at this stake | the stake is the exposure. A wrong one mis-sizes every subsequent limit |
| `--settle` | it resolved, this came back | the only one that feeds profit and loss |
| `--void` | abandoned, non-runner, both sides returned | **a void is not a loss.** `test_a_void_does_not_end_a_losing_run` exists because this was got wrong once, and a rained-off match tripping the losing-run breaker is a lane stopped by weather |
| `--unknown` | a book restricted the account mid-settlement; the outcome is not established | an unknown outcome is not a zero. Recording it as settled-at-nothing is the founding defect with a keyboard attached |

A fifth case is not a verb but shows up constantly: **placed at a different size than the
slip said**, because the book took £180 of the £261.78 offered. For an arb that is not a
smaller arb — it is a hedged £180 and an unhedged £81 on a selection nobody chose.

Any input surface has to carry all five or it will quietly launder one into another.

## Per lane, because the lanes are not alike

### arb — confirmation is one tap, and settlement is never win or loss

Every outcome of a true arb returns the same. That is the whole point of it, so *win* and
*lose* are not the states — these are:

```
SETTLED AS EXPECTED   the guaranteed return, already computed at placement
A LEG VOIDED          now unhedged on the other leg. The state that costs money
RESTRICTED / UNKNOWN  a book limited the account mid-settlement; nothing is established
```

Confirmation needs no numbers at all in the ordinary case: **the slip already knows both
stakes**, so "both legs on, as sized" is one tap, with an adjustment field for the partial
match. The slip is also what makes settlement predictable — `guaranteed_return` was computed
before the bet went on, so "as expected" is a known figure rather than one to look up.

### flipper — the one lane with two real numbers

Buying and selling are yours; `NO_ADAPTER` says so and eBay will not confirm a purchase to a
program. So the flipper is where a genuine *I have bought / I have sold* form belongs, with
what you paid and what it sold for, both typed.

It needs one state the others do not: **the 50-day write-down** (`docs/flipper-design.md`,
Decision 5). An item nobody bid on for fifty days has not been sold and has not been lost —
it comes off the list and stops counting as an open position at cost. Recording that as a
sale at zero would report a loss that has not happened; leaving it OPEN forever overstates
the book and permanently blocks promotion under `docs/levelling-design.md`, which reads the
pessimistic book.

### stocks and crypto

Both have programmatic return legs available — Alpaca reports fills, a chain receipt is
readable — so manual entry here is the owner-operating case rather than the normal one. The
same five states apply; nothing lane-specific is needed.

## The surface, in the order worth building it

### 1. A form on the dashboard

`backend/app.py` already has the shape: a two-key model, a POST endpoint behind a key, and a
served dashboard. Recording outcomes is a new endpoint and a form, following the pattern
that is there.

### 2. A third key scope, and this is the load-bearing part

`_require_command_key`'s docstring is explicit that the command key must never end up in
browser storage: it can run lanes and move money, and the VIEW key exists precisely so the
one that reaches a browser is the one whose entire power is *seeing what the CLI already
prints*.

A phone recording "this settled at 528.85" must not be holding the key that can place
orders. So recording gets its own scope:

```
PROVENA_VIEW_KEY      read what the CLI prints
PROVENA_RECORD_KEY    append an outcome to the ledger. NOTHING else
PROVENA_COMMAND_KEY   run a lane, place, act. Never leaves the operator's shell
```

`RECORD` cannot run a reaper, cannot place, and **cannot reset a breaker** — re-arming is on
`CLAUDE.md`'s never-automate list and stays a named human act at a terminal. It can only
append, because an outcome that can be edited later is a ledger that can be made to say what
somebody wishes had happened.

### 3. A deep link from the notification

The message carries a link to the prefilled form: position identified, stake filled in from
the slip, change it if the book took less. One tap from the phone, and **the notifier stays
send-only**, which is the property the next section is about.

### 4. Telegram buttons — assessed, deliberately later

Inline keyboards with callback data are straightforward to add. Two reasons not to reach for
them first:

Receiving a callback means running a webhook or polling `getUpdates`, which turns the bot
from a one-way channel into an **inbound control surface**. Today a stolen bot token leaks
information, which is bad. After that change it can write to the ledger the breakers read —
inject a settled loss and trip a lane, or a settled win and un-trip one. That is a real
escalation of what one leaked credential costs, in exchange for one saved tap.

And a button cannot carry a number. "Settled at 528.85" is not expressible as a tap, which
is most of what needs recording.

If it is built later, the safe subset is: buttons only for facts with no free number
(`void`, `placed as sized`), accepted only from the configured chat id, landing in the same
validated ledger path as everything else — never a second way in with its own rules.

## Automatic settlement, where the venue actually reports it

The exchanges report your settled bets. Betfair's account API returns cleared orders with
realised profit and loss including voids; Smarkets has an equivalent. That closes the return
leg for the arb lane **completely** — no typing, no "did that void or not", and the breakers
get their numbers from the venue rather than from memory a day later.

`connectors/betfair.py` has login, markets, quotes and balance today. Reading cleared orders
is a small addition on top of machinery that already works.

**Never derive settlement from a scores feed.** A score says who won. It does not say
whether a book voided the market, restricted the account, or applied a palpable-error rule —
and those are precisely the arb failure modes, the ones the equivalence declaration exists
for. A settlement inferred from a result is a confident answer about the one thing the
result cannot establish.

So auto-settlement must be able to answer `UNRESOLVED` and stop. A leg that does not appear
in cleared orders when expected is not a leg that settled at nothing; it is a leg nobody has
found yet, and the difference between the expected return and the account balance is the
signal worth acting on.

## What this costs, and the sequencing decision

Recorded 2026-08-09. Smarkets charges **£150 one-off** to activate API access; Betfair
charges **about £299** for a live App Key, with a free delayed-data key for development.
Verify both before paying — the figures move and only the account can confirm them.

That is roughly **£450 before a single bet goes on**, and the honest reading is that it buys
automation rather than opportunity. **The odds feed already carries both books**, so the lane
can find these arbs and a person can place them by hand today at no additional cost.

**Decided: do not pay it yet.** Run the lane against the feed, place a few by hand, and find
out whether it surfaces repeatable arbs at a real stake size. If it does, £450 is recovered
without argument and buys both automatic placing and — the more valuable half — automatic
settlement. If it does not, that has been learned for nothing rather than for £450, which is
the same discipline the flipper's fee arithmetic imposed on a €40 card.

## What must not happen

- **A write that fails silently.** The endpoint answers `RECORDED`, `REFUSED` or `UNKNOWN`,
  and the last one means the ledger may or may not have taken it — the same third state
  `lib/placing` uses for an unresolved order, for the same reason.
- **A void laundered into a settlement.** See the table above.
- **An edit path.** Append only. A ledger that can be rewritten is one that can be made
  agreeable.
- **Recording standing in for placing.** Nothing here places anything at any venue. It
  records what a person already did, which is why it can be reached from a phone at all.
