# The flipper, designed

Designed 2026-08-09, not yet built. Function 4 of the seven in `docs/target-functions.md`;
the autonomy target is in `docs/end-state.md`. The next session can pick this up from cold.

## The one thing to check before writing any code

**Can your eBay account read SOLD listings?**

The entire function rests on it. `target-functions.md` says eBay is the only viable source
*because* completed sales are real transactions — and sold data is the most restricted part
of eBay's API surface. Browse gives active listings freely; historical sold prices sit
behind approval.

Half an hour on the developer portal, checking what your production keys can actually call,
**before** anything is built on the assumption. If sold data is not reachable, the honest
answer is that this function does not work as designed — not that we substitute asking
prices. That substitution is the failure this whole document exists to prevent.

---

## Decision 1 — sold price is evidence, asking price is a `REFERENCE_RATE`

This is the whole discipline of the function.

A completed sale is a transaction that happened, with a date and a price: **evidence**. An
active listing is somebody's hope. A flipper built on asking prices computes margins against
numbers nobody paid, and it will produce confident, wrong, profitable-looking suggestions
all day.

The vocabulary already exists here. Sold comparables are `PRICED`. Active listings are
`REFERENCE_RATE` — displayable, useful for orientation, **refused for sizing**. The
distinction must be in the type, not in a comment, so that no later change can quietly
size against an asking price.

## Decision 2 — the exit is not contracted, and the output must say so

A flip is arbitrage-shaped only when the exit is contracted, and it never is. Sold
comparables say *others sold at that price*, not that you will.

So a suggestion carries a **distribution, not a number**: what similar items actually
fetched, how many sales, over what window, and the spread. `n=3 over 90 days` and
`n=47 over 14 days` are different facts and must not both render as "sells for £120".

**A minimum comparable count is required before an item is sizeable at all.** Below it the
verdict is `INDETERMINATE` — not a low estimate, not a wide range, *unestablished*. Ian sets
the number; a starting proposal is **5 sales within 90 days**.

## Decision 3 — fees before margin, always

Platform commission, payment processing, postage by weight band, and an assumed returns
rate. Every one of them before a margin is stated, never after.

These are numbers only Ian has, and they belong in config rather than in code, because they
change and because getting them from the wrong account is how a margin becomes fiction.
`connectors/chain_costs.py` is the worked precedent — the round trip is costed before the
opportunity is called one.

## Decision 4 — two urgency tiers, and the quiet one must stay quiet

Ian's requirement, and the sharpest idea in the function:

| tier | when | how it notifies |
|---|---|---|
| **URGENT** | severely underpriced against sold comparables | immediately, loudly, expected to be acted on within minutes |
| **ROUTINE** | a real but small margin | notified, explicitly **not** a do-or-die |

This maps directly onto `lib/notify.py`, which already exists. The tier is a property of
the *opportunity*, computed from margin against the comparable distribution — not a
notification setting, so that the same instruction always carries the same urgency wherever
it is read.

**The failure to design against is tier inflation.** If ROUTINE items start arriving
frequently, they are read as noise, and the day an URGENT arrives it is skimmed with them.
So the thresholds are set to keep URGENT rare by construction, and the daily digest —
already built — carries the routine finds instead of pushing each one.

## Decision 5 — the exit horizon is a state, not a hope

Stocks and arb settle on their own. **A flip never does.** An item can sit unsold
indefinitely, so `unsettled_exposure` grows and nothing resolves it.

Two things follow, and neither is optional:

- **A write-down rule.** After how many days unsold is an item marked down, and at what
  point does it become a realised loss rather than an open position? Ian's number.
- **`docs/levelling-design.md` interacts here.** Promotion reads the *pessimistic* book,
  marking every OPEN position as a total loss. A flipper lane with slow stock would never
  clear that bar and would sit permanently at level 1. That is the safe failure — but
  without a write-down rule it is also a permanent one.

## Decision 6 — physical capacity is the binding constraint, and no code models it

`max_concurrent_positions` is a risk control for stocks. For the flipper it is **how many
items fit in your house and how many you can pack and post in a week**. That number is
Ian's, it is probably tighter than the ring-fence, and a lane that ignores it will suggest a
fifteenth item while fourteen sit unlisted in a hallway.

Treat it as a hard limit alongside the ring-fence, with the same refusal shape: at capacity,
the lane reports `AT_CAPACITY` rather than finding nothing.

---

## Sourcing: what is reachable, and what is not a missing adapter

| source | reachable | note |
|---|---|---|
| **eBay** | **yes, with caveats** | a real API. Sold data is the gated part — see the top of this document |
| Amazon | partly | PA-API needs an affiliate account *with sales*, so it is gated behind having the thing you are trying to start |
| Facebook Marketplace | **no** | no public API, and scraping is against its terms |
| DoneDeal | **no public API** | would need permission or a partnership |

**Facebook and DoneDeal being absent is not a missing adapter**, exactly as bookmakers
having no betting API is not a missing adapter for arb. Do not build a scraper for either.
The same discipline applies to the app-development lane's complaint sources.

This narrows the function considerably and honestly: **v1 is eBay-to-eBay**, or
eBay-comparables against a source you input by hand.

## Execution: `NO_ADAPTER`, like arb

You cannot automate buying on eBay in any way worth relying on, and Facebook and DoneDeal
are manual by construction. So the flipper belongs in `lib/placing.NO_ADAPTER` with a stated
reason, **not** in `PLACERS`. The deliverable is a notified suggestion you act on by hand,
and settlement is manual entry through `positions.py` — the same shape as the arb slip.

Right now `lib/placing.py` refuses `flipper` by name for being in neither registry, which is
the guard working. Adding it to `NO_ADAPTER` is a one-line change and should be done *with*
the lane, not before it.

---

## Shape

The five callables every lane supplies, plus the registry entries:

```
lib/flipper_reaper.py
    look()        -> candidate listings, sources asked, sources answered
    screen()      -> the cascade below
    gates()       -> capacity, ring-fence, duplicate-sighting
    thesis_for()  -> see the authorisation question below
    size()        -> a buy price and a comparable-backed exit distribution

lib/reaping.LANES          += "flipper"
lib/reaping.LANE_CURRENCY  += flipper: EUR
lib/placing.NO_ADAPTER     += flipper: "eBay takes no automated purchase; the suggestion IS
                                        the deliverable"
```

Adding a lane is one decision and not five edits — that work is already done, and
`tests/test_lane_registry.py` uses `flipper` as its worked example of a planned lane.

### The cascade

Cheapest and most fatal first, as everywhere else:

```
the item is what it says          title/condition/completeness parsed and consistent
there are enough sold comparables n >= floor within the window, or INDETERMINATE
the exit is a distribution        spread and count stated, never a single number
the round trip is affordable      fees, postage, returns rate, before margin
there is capacity                 physical, not just financial
```

### The authorisation question, which is Decision 7 and is Ian's

Arb has a `StandingAuthority` and it is defensible for one stated reason: *an arb makes no
claim about the fixture*. **A flip does make a claim** — that this item is underpriced and
will resell — so a standing authority for flipping authorises a judgement in advance, which
is exactly what the arb one is careful not to do.

Per-item theses are honest and do not scale, and volume is the whole point of the function.
Three options:

1. per-item throughout — honest, slow, probably unworkable
2. a bounded standing authority — category, price ceiling, minimum comparable count
3. **a hybrid: standing authority under a figure, per-item above it**

Recommended: **3**. The figure is Ian's, and it is the number at which he wants to look at
something himself before money moves.

## Tests to write

Properties, not coverage:

- an asking price is never used to size; only sold comparables are
- below the comparable floor the verdict is `INDETERMINATE`, not a wide estimate
- a margin is computed after fees, postage and the returns rate, never before
- an item with a wide comparable spread does not present as a point estimate
- `n=3` and `n=47` produce visibly different confidence in the output
- an URGENT tier requires a margin materially above the ROUTINE threshold, so the tiers
  cannot collapse into each other
- at physical capacity the lane reports `AT_CAPACITY`, not "nothing found"
- an unsold item past the write-down horizon stops counting as an open position at cost
- the lane is in `NO_ADAPTER` and never reaches a placer
- a source that could not be reached is `COULD_NOT_LOOK`, never "no deals today"

## What this job is not

- Not a scraper for Facebook Marketplace or DoneDeal.
- Not a price predictor. Sold comparables are evidence of what happened, not a forecast.
- Not an automated buyer. The deliverable is a suggestion.
- Not a listing generator. Selling the item is a separate piece of work — closer to the
  Etsy/Shopify function than to this one.

## Open inputs — Ian's, not the code's

1. **Does your eBay account reach sold data?** Everything else is moot until this is known.
2. **Fee structure**: final value fee %, payment processing, postage bands, returns rate.
3. **Comparable floor**: proposal 5 sales in 90 days.
4. **The two tier thresholds**, and the ratio between them.
5. **Physical capacity** — items you can hold and post per week.
6. **Write-down horizon** for unsold stock.
7. **The per-item authorisation figure** from Decision 7.
8. **Categories** you can actually verify. The lane disqualifies; it does not select.

## Rough size

The wiring is a day once the decisions are made. The comparable-distribution work and the
fee model are most of it. **None of it is worth starting before question 1 is answered.**
