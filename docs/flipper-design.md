# The flipper, designed

**BUILT 2026-08-29**, to this document. `lib/flipper.py` holds the identity key, the
comparable distribution, the fee arithmetic and the write-down; `lib/flipper_reaper.py` the
lane; `connectors/ebay.py` the two comparable sources. Every property in "Tests to write"
below is now a test in `tests/test_flipper.py` and `tests/test_flipper_reaper.py`.

**What is NOT built, and why that was the right call:** the eBay completed-sales client.
Question 1 at the top of this document is still unanswered, and which endpoint serves sold
data — in what shape, under which scopes — depends on which programme the account is
approved for. A client written against a guessed contract would look finished and return
nothing. `EbaySoldSource` is the shape and it answers NOT_CONFIGURED; `RecordedComparables`
reads sales typed in by hand, which is the same evidence at lower volume and works today.

Designed 2026-08-09. Function 4 of the seven in `docs/target-functions.md`;
the autonomy target is in `docs/end-state.md`. The next session can pick this up from cold.

## Scope, decided 2026-08-09, extended 2026-08-09 (evening)

**In: graded sports cards, graded trading cards (Pokémon), and graded video games.** PSA,
BGS, SGC and CGC for cards — CGC matters because it grades a large share of TCG and
omitting it would discard comparables that exist; WATA and VGA for games. Nothing else in
v1.

**Pokémon was added on the same reasoning that admitted sports cards, not as a second
category.** The matching key is the same shape and just as exact, and TCG comparable
density is *higher* than sports for the popular sets, so the comparable floor will refuse
less often there than anywhere else in the lane. Where it differs is that grade inflation
between graders is a live argument in TCG — a CGC 9.5 and a PSA 10 are not the same item,
which is exactly why the comparable floor already requires matching grade **and** grader.

The axis is not category enthusiasm, it is **matchability** — how exactly an item can be
tied to the sold comparables that price it. Graded items sit at the top of that scale for
one reason: the matching key is exact and machine-readable, and two items sharing it are
genuinely fungible.

    card:  title + set + year + parallel + grade + grader (+ cert number)
    game:  title + platform + region + seal/box type + grade + grader (+ cert number)

Everything below that line was considered and left out, with the reason recorded so it is
not relitigated from enthusiasm:

| considered | verdict | why |
|---|---|---|
| **sports memorabilia** | **out** | a signed shirt is a unique item. No comparables by definition — value is authentication plus provenance, which is a different discipline, and it is where fakes concentrate |
| **retro games, loose** | **out** | a loose cart is 10-30 EUR and cannot clear fees at any realistic markup. See the floor below |
| **retro games, CIB** | **later** | genuinely matchable with effort. A real candidate once v1 proves the sold-data pipeline |
| **consoles** | **later** | model, region, what is in the box, modded or not. Matchable but messy |
| **games/consoles/electronics, ungraded** | **later, and the criterion is written below** | Ian asked on 2026-08-09 whether these come in "if they fit criteria". They fit when an exact matching key exists — and for working electronics one does not, because **whether it works cannot be established from a listing**. See the note under this table |
| **"mispriced anything"** | **a different function** | this is the **opportunity engine** in `docs/end-state.md`, which surfaces candidates with their evidence and never sizes them. Folding it in here would replace exact matching with a fuzzy matcher, and a fuzzy matcher produces confident wrong margins — the failure this whole document exists to prevent |

**What ungraded hardware would need before it could enter.** A graded item carries its
condition in its key: the grader looked, and the number is the evidence. A console does not.
"Tested, working" in a listing is a seller's claim, and the lane would be pricing that claim
against comparables whose own claims it also cannot check — two unverified assertions
multiplied together and reported as a margin. So hardware enters only with (a) an identity
key as exact as a cert number (model + region + revision + box contents), and (b) a third
state for condition, `CLAIMED_WORKING` beside `TESTED`, which never counts as the same thing
when comparables are matched. Both are real work rather than a config change, which is why
this stays *later* rather than becoming a v1 toggle. **CIB retro games are the closer of the
two** — a sealed or complete-in-box title has a genuine key and no working-order claim to
verify.

**Expect games to refuse more often than cards.** WATA took reputational damage in 2021 and
the sealed retro market corrected hard, so comparable density is far lower. Frequent
`INDETERMINATE` on games is the comparable floor working, not the lane failing.

## The decided parameters

Set by Ian on 2026-08-09 after the fee arithmetic below was run against his first proposal.

| | value |
|---|---|
| minimum buy price | **75 EUR** |
| URGENT tier | **>= 50% net after fees** |
| ROUTINE tier | **>= 30% net after fees** |
| physical capacity | **20 items** |
| unsold horizon | **50 days**, then off the list |
| comparable floor | **>= 5 sales within 90 days, matching grade AND grader** |

The 90-day comparable window is deliberately tight. Cards bubbled through 2020-22 and
corrected; a sale from 2021 is a different market, not an old data point.

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
verdict is `INDETERMINATE` — not a low estimate, not a wide range, *unestablished*. Set at
**5 sales within 90 days, matching grade AND grader**.

The grade is part of the key, not a modifier on it. The same card raw and at PSA 10 can
differ by fifty times, so a comparable that does not match on grade and grader is not a
comparable — it is a different item with the same name. A listing whose grade cannot be
read reliably is `INDETERMINATE`, never an estimate.

## Decision 3 — fees before margin, always, and there is a floor below which nothing works

Platform commission, payment processing, postage by weight band, and an assumed returns
rate. Every one of them before a margin is stated, never after.

These are numbers only Ian has, and they belong in config rather than in code, because they
change and because getting them from the wrong account is how a margin becomes fiction.
`connectors/chain_costs.py` is the worked precedent — the round trip is costed before the
opportunity is called one.

### What the arithmetic did to the first proposal

Ian's opening figures were a 200 EUR buy at 40-65% and a 40 EUR buy at 15-25%. Run against
indicative eBay card-category fees (13.25% of the total plus a 0.30 fixed fee) and tracked
postage:

| buy | markup | net profit | |
|---|---|---|---|
| 40 | 15% | **-5.90** | loss |
| 40 | 25% | **-2.42** | loss |
| 40 | 40% | +2.78 | barely |
| 200 | 25% | +7.57 | thin |
| 200 | 40% | +33.60 | works |
| 200 | 65% | +76.98 | works |

**A 40 EUR item needs a 32% markup merely to break even; a 200 EUR item needs 21%.** The
small tier was inverted — it asked the thinnest margin from the item least able to carry
one — and the reason is that postage and the fixed fee do not scale down. On a 40 EUR item
they are about 15% of the sale price before the platform takes 13%.

**So there is a minimum viable item price, exactly as the stocks lane has a minimum viable
ring-fence.** To net 25 EUR, which is roughly what justifies sourcing, listing, packing and
posting something:

| markup | minimum buy |
|---|---|
| 30% | ~245 EUR |
| 40% | ~145 EUR |
| 50% | ~105 EUR |
| 65% | ~75 EUR |

Below about 75 EUR no realistic markup makes an item worth touching, which is where the
floor comes from. It also settles the loose-retro-games question on arithmetic rather than
taste.

**Scale, so nobody is surprised by it:** 20 items at 200 EUR and 40% is about 670 EUR a
turn on 4,000 EUR deployed. Real, and worth knowing before the lane is built rather than
after.

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

Thresholds decided: **URGENT at 50% or better net of fees, ROUTINE at 30%**, both above the
75 EUR floor. Stated NET rather than as a markup, because a markup that has not had fees
taken out of it is the number that made the original 40 EUR tier look viable.

**The failure to design against is tier inflation.** If ROUTINE items start arriving
frequently, they are read as noise, and the day an URGENT arrives it is skimmed with them.
So the thresholds are set to keep URGENT rare by construction, and the daily digest —
already built — carries the routine finds instead of pushing each one.

## Decision 5 — the exit horizon is a state, not a hope

Stocks and arb settle on their own. **A flip never does.** An item can sit unsold
indefinitely, so `unsettled_exposure` grows and nothing resolves it.

Two things follow, and neither is optional:

- **A write-down rule.** Set at **50 days unsold, then off the list.** After that it stops
  counting as an open position at cost, because an item nobody bid on for fifty days is not
  worth what you paid for it and carrying it at cost overstates the book.
- **`docs/levelling-design.md` interacts here.** Promotion reads the *pessimistic* book,
  marking every OPEN position as a total loss. A flipper lane with slow stock would never
  clear that bar and would sit permanently at level 1. That is the safe failure — but
  without a write-down rule it is also a permanent one.

## Decision 6 — physical capacity is the binding constraint, and no code models it

`max_concurrent_positions` is a risk control for stocks. For the flipper it is **how many
items fit in your house and how many you can pack and post in a week**. Set at **20**. It is
probably tighter than the ring-fence — 20 items at the 75 EUR floor is 1,500 EUR, and at
200 EUR each it is 4,000 — and a lane that ignores it will suggest a twenty-first item while
twenty sit unlisted in a hallway.

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

## Open inputs — what is still Ian's

Most of this document's questions were answered on 2026-08-09. Three remain, and the first
one decides whether any of the rest matters.

1. **Does the eBay account reach SOLD data?** Unanswered. The developer account went in
   for verification on 2026-08-09 and takes a business day, so **the answer is expected
   Tuesday 2026-08-11**. Everything below the top of this document is moot until it lands,
   and a "no" is a real answer that stops the function rather than a setback to work
   around.
2. **The real fee rate.** The arithmetic above uses 13.25% plus a 0.30 fixed fee, which is
   indicative. A Store subscription changes it materially, and every floor and threshold in
   this document moves with it. Confirm from the account, not from a help page.
3. **Whether raw-buy-then-grade is in scope.** It is a different strategy: grading costs
   15-30 EUR, takes weeks to months, and its outcome is uncertain — which breaks both the
   fee model and the 50-day horizon. **Assumed OUT** unless Ian says otherwise, because a
   lane that buys raw and hopes for a grade is making a forecast.

Answered and recorded above: scope (including Pokémon, and what ungraded hardware would
need first), raw-buy-then-grade OUT, the 75 EUR floor, both tier thresholds, capacity of 20,
the 50-day horizon, and the comparable floor.

## Rough size

The wiring is a day once the decisions are made. The comparable-distribution work and the
fee model are most of it. **None of it is worth starting before question 1 is answered.**
