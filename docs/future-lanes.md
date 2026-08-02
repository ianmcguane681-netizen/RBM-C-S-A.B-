# Future lanes: Etsy, flipping, app development

Recorded 2026-08-02, not yet built. Noted here rather than left in a conversation, and with
an honest assessment of how much of the existing machinery each one can actually use —
because the appealing answer is "another profile" and for two of the three that would be
wrong.

## What they have in common

All three are **operating activities**, not positions. The boards verify claims against
primary sources and refuse to conclude past the evidence; that transfers. What does not
transfer is anything needing a forecast, and each of these has one hiding in it.

`lib/portfolio.py` handles all three cleanly as **capital deployed with a cost basis**, in
its own lane. Stock bought for resale, an Etsy inventory, and hours sunk into an app are all
positions with an entry price and no reliable mark. `UNPRICED` is the correct valuation for
every one of them until something sells, and the existing rule — an unpriced holding is
absent from the total, never counted as zero — is exactly right here.

---

## App development — no new profile needed

**RBM-002 already reviews engineering artefacts.** Its artefact is a commit hash, its six
gates are defects this codebase produced, and an app is the same class of thing. Pointing it
at a new repository is a new *review*, not a new *profile*.

What it will not answer is "should I build this", which is a forecast about demand. The
board can establish that what was built does what it claims and that the tests measure
something; it has no view on whether anyone wants it.

The one genuine gap: RBM-002 has six drafted reports still unverified from its first live
run. Finishing that is worth more than authoring anything new.

## Flipping — the closest fit, with one hard condition

Buy at X, sell at Y, minus fees, over a holding period. That is arbitrage shaped, and
`lib/arb.py` already models the parts that matter: two prices, fees applied per side, and a
refusal when the two sides are not the same thing.

**But the sell side is not contracted, and that is the whole difference.** A betting arb
locks both legs at the moment of placing. A flip locks the buy and *hopes* for the sell. The
gap between them is a forecast about resale value, which is precisely what
`lib/candidates.py` was built to refuse to score.

So the honest rule, if this is built:

> A flip is arbitrage-shaped **only when the exit is contracted**. A confirmed buyer, a
> trade-in quote, a buyback price, a standing bid — something that makes the sell leg a
> price rather than a hope. Everything else is a directional position on resale value, and
> the system should say so rather than compute a margin that implies otherwise.

That maps onto the existing statuses without inventing any: a contracted exit is `PRICED`
with a size and a counterparty; an expected exit is a `REFERENCE_RATE` — usable for display,
refused for sizing. Comparables from completed sales are the reference rate, and treating
them as a price is the same error as sizing against a mid-price with no depth behind it.

Fees are the second thing people get wrong and they are knowable: platform commission,
payment processing, postage, returns rate. All belong on the leg, before the margin, the way
exchange commission already decides which book wins a selection.

## Etsy — mostly operations, and the monitor is the part that fits

A shop is run, not held. Most of what makes one work — listings, photography, keywords,
customer service — is outside anything this repository does, and a profile pretending to
review it would be a checklist rather than a set of gates.

Two pieces genuinely fit.

**Unit economics as a filing-shaped artefact.** Etsy's own API is the primary source, the
way EDGAR is for an equity: orders, fees and payouts are retrievable, immutable once
settled, and checkable by someone who was not there. The recurring error in a shop's
accounts is the same one this repository keeps meeting — a fee not modelled reads as margin
that does not exist. Listing fee, transaction fee, payment processing, offsite ads (charged
on some orders and not others), postage subsidy, refunds. A margin computed from revenue
minus cost of goods is wrong in the flattering direction, every time.

**The monitor is the strongest fit of anything here.** Etsy changes its fee structure and its
policies, and when it does, every margin calculation resting on the old numbers is void —
structurally identical to a proxy implementation swap voiding a contract review. The
obligation table already has the right shape: a changed fee is `EXIT_OR_RE_REVIEW` on the
unit economics, and an unreadable API is no obligation at all.

---

## What I would refuse to build

A scoring model over any of them. "Opportunity score" for a flip, "shop health score" for
Etsy — same defect, argued at length in `lib/candidates.py`: a weighted sum treats a
disqualifier as a deduction, and an unmeasured dimension either drags the total down or
raises it by dropping out of the average.

And demand forecasting, for all three. What sells, what an app will earn, what a shop will
turn over next quarter. Nothing here can establish those, and a system that produced them
would be borrowing the credibility of the parts that can.

## Order, if these are picked up

1. Finish RBM-002's six unverified reports. App development needs nothing else.
2. Extend `lib/portfolio.py` with the operating lanes. No forecast, pure bookkeeping, and it
   makes all three visible in one place.
3. Etsy connector against the API, unit economics only, plus the fee-change monitor.
4. Flipping last, and only with the contracted-exit rule enforced at the type level the way
   `Leg` enforces a settlement rule.
