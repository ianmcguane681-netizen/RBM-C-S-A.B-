# The equity guard, designed

Designed 2026-08-09, not built. Ian's shape, and it is the right one: **he declares a
challenge, connects the account read-only, places his own buys and sells, and the system
watches the equity against the floor and tells him long before he reaches it.**

The occasion was a funded-account challenge — 10,000 of capital on the rule that the balance
must never fall 5% below its starting value. But the guard is not about that programme, and
this document is careful to keep the two apart: **the blindness it fixes exists today, in the
stocks lane, with no challenge involved.**

## What this is not

It is not a lane. `monitor.py` is the precedent and the right one — a watcher that reads a
primary source on a schedule, says when something the system relied on has moved, and
**decides nothing**. There is no `look → screen → gate → size` here because there is no
instruction at the end of it. Forcing this into the reaper shape would produce four empty
callables and one real one, and the empty ones would eventually be filled in by somebody who
thought they were supposed to be.

It also does not trade. Not to close a position, not to hedge one, not to flatten at the
floor. See "the capability it does not have" below.

## The blindness it fixes, which is not hypothetical

`Breakers.profit_today()` sums **settled** outcomes. `consecutive_losses()` walks settled
outcomes. Everything the daily-loss limit and the losing-run check know, they know from
results a person has already recorded.

Open positions are invisible to all of it. `status.py` says so in as many words, and
`tests/test_status.py` asserts the phrase — *"invisible to the daily loss limit"*. Today
that is an honest statement of a limitation. Under a rule measured on live equity it becomes
something worse: **the one control that would save you cannot see the thing that fails you.**
Protection that looks present and cannot engage is this repository's founding defect, and
this is that defect standing exactly where the money is.

So the guard is not a feature for a prop challenge. It is the missing half of the breakers,
and the challenge is what made the hole visible.

## The four states, and which one is the dangerous one

```
WITHIN     equity above the warning band. Nothing to do
WARNING    inside the band between the warning level and the floor
BREACHED   at or below the floor. Whatever that floor was declared to mean
UNKNOWN    the equity could not be established
```

**`UNKNOWN` is the state this whole design turns on.** An equity that cannot be read is not
a safe equity. The API key expired, the exchange is down, a price is stale — in every case
the honest answer is *"I do not know where you are"*, and the flattering reading a person
adopts is that no news is good news. That is the notifier's founding argument arriving in a
monitor: a guard that goes quiet when it breaks is worse than no guard at all, because you
will keep trading in the belief that you are covered.

Two consequences, neither optional:

- **`UNKNOWN` notifies, and keeps notifying.** It is not a quiet state. It is the state in
  which you should consider closing positions by hand, because nothing is watching them.
- **The guard carries its own heartbeat.** While a challenge is live it reports where you
  are on a fixed cadence even when the answer is comfortable — *"3,140 of headroom, 1.2%
  used"* — for the same reason the daily digest reports lanes that found nothing. Silence
  has to mean something, and it can only mean something if noise means nothing.

## The rules are the vendor's, and a human declares them

The guard enforces somebody else's rule, which it cannot read from an API. Four questions
decide what the floor actually is, and getting any of them wrong makes the guard confidently
wrong:

| question | why it changes everything |
|---|---|
| static or **trailing**? | 5% below the starting balance is a fixed line. 5% below the high-water mark moves up every time you profit, and a trader who has been up 3% has a floor 3% higher than they think |
| does it include **unrealised** P&L? | almost always yes, and it is the entire reason this guard exists |
| measured **intraday** or at a daily close? | a position that dips 6% at 3am and recovers by morning has either failed or not, and only the vendor's answer counts |
| is there a **separate daily** loss limit? | passing the overall floor while breaching a daily one is still a fail |

So a challenge is **declared**, the way a thesis or a settlement equivalence is declared: by
a named person, with the parameters written down and dated. Not read from a webpage by the
machine, because if the machine misreads a rules page the person who pays for it is the one
who did not check.

**Where a parameter is unstated, the guard assumes the strictest reading** — trailing rather
than static, unrealised included, intraday rather than close. Failing that direction costs a
warning you did not need. Failing the other direction costs the challenge. And **every alert
states which interpretation it used**, so a wrong assumption is visible and correctable on
the first message rather than discovered at the end.

## What the message actually says

A percentage is not actionable at 2am. Three things are:

```
CHALLENGE · 3.1% used · 1,900 of headroom

  equity     9,690   against a floor of 9,500 (5% of 10,000, static, unrealised included)
  headroom   190
  open       BTC 0.08 at 61,240 — a 3.9% adverse move from here reaches the floor
  read at    2026-08-11T02:14:07Z   (Kraken, 40s ago)
```

The line that matters is the last one before the timestamp: **the floor translated into a
move in the instrument you are actually holding.** "You are 3.1% down" is a fact about the
past. "A 3.9% move against you ends this" is a fact you can act on, and it is the same move
the arb slip makes when it prints stakes to the penny instead of a percentage.

## Escalation, and the one place the notifier's dedupe must not apply

`lib/announce` suppresses a repeat inside a six-hour window, which is right for a standing
opportunity and wrong here. Deterioration is news every single time it deteriorates.

So the guard escalates in bands, and **crossing into a worse band always sends, whatever was
said before**:

```
2.0% used   informational   you are being watched, and here is where you are
3.5% used   urgent          the headroom in money, and the move that ends it
4.5% used   unmissable      and every band crossing below this point re-sends
UNKNOWN     urgent          nothing is watching your positions right now
```

Within a band the ordinary window applies, so a position bumping along at 3.6% does not
buzz every minute. Improving is never urgent — recovering from 4% to 2% is good news and can
wait for the heartbeat.

## The capability it does not have

The account connects with a **query-only key**. Kraken's API keys carry granular permissions,
so a key with no trade permission and no withdrawal permission cannot place, close or move
anything — and that is the point. It is the same argument as `connectors/chain_exec` having
no signing path: a policy is something somebody relaxes at eleven at night, and an absent
capability is not.

This forecloses the tempting feature, which is worth naming so nobody adds it later: **the
guard must not close positions at the floor.** An automatic flatten sounds like protection
and is a liquidation trigger wired to a price feed — one stale quote, one bad decimal, one
exchange returning a wrong number for four seconds, and it closes a winning position at the
worst moment. Ian places, Ian closes. The system watches and shouts.

This also means the guard fits the existing mode model with nothing new: the lane is
`OWNER_OPERATING_MANUALLY` by construction, because there is no execution path to be
autonomous with.

## Cadence, and where it lives

The supervisor already wakes every 60 seconds and the guard belongs on that tick — a private
balance query is cheap and well within any exchange's rate limits. That is a different
cadence from the reapers, which run in hours, and the difference is the point: a drawdown
rule does not care what your cadence is.

```
lib/challenge.py      the declaration, the floor arithmetic, the four states
connectors/kraken.py  read-only balance and open positions. No trade method
run.py --serve        checks the guard each tick, alongside the digest
```

Nothing here touches `lib/reaping`, because nothing here produces a harvest.

## What I would build first, and it is not the Kraken part

**The guard against Alpaca**, using position data the system can already read.

The blindness is real today: a stocks position drifting badly is invisible to the daily-loss
limit until it settles. That gap deserves closing whether or not any challenge is ever
started, it exercises every part of this design against a source already connected, and it
does not depend on a programme whose terms nobody has verified yet.

Kraken is then a second connector against a proven guard rather than a new connector and a
new guard at once.

## Open, and it is Ian's

1. **Is the programme real, and is it Kraken's own?** Confirm it lives on `kraken.com`.
   Brand-lookalike "funded account" offers are common in crypto, and the failure mode there
   is not a lost fee but a lost API key.
2. **The four rule questions above**, from the programme's terms, not from a summary.
3. **Is capital real or simulated**, and what is the profit share on it.
4. **Do the rules permit automated tooling at all?** A read-only monitor is not automated
   trading by any reasonable reading, but "any reasonable reading" is not the same as
   "written down", and it is cheaper to ask than to be disqualified for it.

## What must not happen

- **A silent guard.** `UNKNOWN` is loud, and the heartbeat runs even when the news is good.
- **A guard that trades.** No trade permission on the key, and no flatten-at-the-floor.
- **A machine-read rulebook.** The parameters are declared by a named person and dated.
- **An assumed-permissive default.** An unstated rule resolves to the strictest reading, and
  the alert says which reading it used.
- **The guard standing in for the breakers.** It watches one declared account against one
  declared floor. It is not a ring-fence, it does not size anything, and a lane's breakers
  still apply to that lane.
