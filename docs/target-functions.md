# The seven target functions

Stated 2026-08-02. This supersedes the scattered notes in `future-lanes.md` and
`seven-sectors-plan.md` as the canonical target. More will be added; the point of writing
it down is that adding one should be a decision rather than a drift.

## Summary

| # | Function | Built | Missing | Blocked on |
|---|---|---|---|---|
| 1 | **Arb betting** | discovery, gates, staking | one live source | a free Smarkets account |
| 2 | **Stocks** research + execution | research complete | price feed, broker | an Alpaca paper key |
| 3 | **Crypto** research + execution | research complete | *execution is refused by design* | a deliberate profile decision |
| 4 | **Flipper** | nothing | sourcing, comparables | eBay is the only viable source |
| 5 | **App making** | engineering review (RBM-002) | pain discovery | a complaint source |
| 6 | **Faceless YouTube** | nothing | everything | policy check first |
| 7 | **Etsy / service** | nothing | unit economics, fee monitor | inventory or a service to sell |

Two of the seven are essentially done. Two need one free credential each. Three do not
exist. One of them cannot exist in the form described without a deliberate change to a
methodology, and that is function 3.

---

## 1. Arb betting

**State.** `lib/arbfind.py` finds candidates across books; `lib/arb.py` verifies a position;
`screen.py` runs the cascade; staking is complete — stakes split so every outcome returns
the same, floored to pennies, commission applied per leg before choosing the best price.
RBM-005 has convened once and reached a decision.

**Missing.** A second live source. Betfair alone reports `SINGLE_BOOK` and refuses, which is
correct: one book pricing both sides under 100% is an error it will void, not two
counterparties.

**The constraint nobody's data solves.** The real arb is exchange versus soft bookmaker, and
soft books limit or close accounts that arb consistently. That is the binding constraint on
this function and it is commercial, not technical.

## 2. Stocks — research and execution

**Research is complete.** SEC EDGAR needs no key, six filing gates, and `RBM004-MOD-0001`
sits at `GOVERNANCE_VALIDATION` awaiting a signature.

**Execution needs one thing and it is not a broker.** It needs a *reason to buy*, and the
board does not produce one. RBM-004 establishes what a filer filed and where the filings
disagree with each other; it has no view on price and cannot acquire one. So "execution"
here means: **you supply the thesis, the system sizes it, gates it and refuses it when it
should.** That is `RBF-001` and most of it is built — portfolio state, sizing that names its
binding constraint, the obligation table.

An Alpaca paper key completes it. This is the lane where a `PERMITTED` can honestly arrive
first: no §11 equivalent, no key material, and the worst failure is a bad order rather than
a drained wallet.

## 3. Crypto — research and execution

**Research is complete.** Two published decisions, six chain gates, a monitor watching seven
facts per token.

**Execution is refused by design, and this is worth understanding rather than working
around.** RBM-003 section 11 states that a review conducted under it can never authorise a
transaction. `mandate.evaluate()` has therefore never returned `PERMITTED` and structurally
cannot. That is the profile being honest about its own weight: the gates establish that a
contract is what it claims — which is hygiene, not an edge — and hygiene is not a reason to
buy.

To execute crypto you would need a profile that grants authorising weight, written
deliberately and reviewed as such. That is a real piece of work with a real argument behind
it, not a configuration change, and **loosening the check that currently works is the one
way not to do it.**

What crypto is genuinely good for meanwhile is the veto and the monitor: what you may not
hold, and the day a prior review stops being true.

## 4. Flipper — Facebook, DoneDeal, eBay, Amazon

Nothing built. The most important thing here is which sources are actually reachable, and
the answer is narrower than the list.

| Source | Reachable | Note |
|---|---|---|
| **eBay** | **yes** | a real API, and *sold* listings are the key thing |
| Amazon | partly | PA-API needs an affiliate account with sales; price history is paid |
| Facebook Marketplace | **no** | no public API, and scraping is against its terms |
| DoneDeal | **no public API** | would need permission or a partnership |

**Sold price is evidence. Asking price is not.** This is the whole discipline of the
function and it maps exactly onto what already exists. A completed eBay sale is a
transaction that happened, with a date and a price — `PRICED`. An active listing is
somebody's hope — a `REFERENCE_RATE`, displayable and refused for sizing. A flipper built on
asking prices computes margins against numbers nobody paid.

**And the rule from the earlier note stands.** A flip is arbitrage-shaped only when the exit
is contracted. Sold comparables are the closest available thing and they are still not a
contract: they say others sold at that price, not that you will. So the honest output is a
`REFERENCE_RATE` exit with a stated distribution of what similar items actually fetched, and
a refusal to size against it as though it were locked.

Fees before margin, always: platform commission, payment processing, postage, returns rate.
An unmodelled fee reads as margin that does not exist, which is the same defect as an
unmodelled Etsy fee and an unmodelled exchange commission.

## 5. App making — research and development

**Half of it exists.** RBM-002 reviews engineering artefacts against a commit hash, and its
six gates are defects this codebase produced and shipped. `RBM002-GSCF001-0001` reached a
decision today. Pointing it at a new repository is a new review, not new machinery.

**The missing half is discovery, and it is the honest half.** The Project Xchange principle
— find verifiable pain, fix it with an app — is well suited to this system precisely because
*pain is observable*. "Forty people asked for this in a forum thread" is a fact with a
source, a date and a count. It is not a forecast.

What is a forecast, and what this will not produce: **that they would pay.** Demand is not
established by complaint volume, and a discovery lane that scored ideas on projected revenue
would be the scoring model again. The honest output is a *count of evidenced requests, with
citations*, and the judgement about whether to build stays yours.

The chain here is the one the reference system demonstrated and the only one in the seven
that needs no forecast at any link: **observe pain → build → publish → observe use.**
`lib/orchestrator.py` supports it today via declared dependencies.

## 6. Faceless YouTube

Nothing built, and I would check before building rather than after.

**The "untapped" premise is the part I would test first.** It is a heavily worked space, and
YouTube maintains explicit policy on mass-produced and repetitive content with monetisation
gated behind review. Those terms change, and a channel built on volume carries the same
class of exposure an Etsy shop carries to a fee change — a policy decision elsewhere voids
the model. That should be read from the current Partner Programme terms rather than from
anybody's memory, including mine.

**The differentiated version.** Generic AI-narrated content is the saturated part. A channel
about *building this* is not, because the material does not exist anywhere else: a system
whose board has never returned `PASS`, six defects found in one day by running code rather
than reading it, a monitor that reports its own lost memory rather than pretending to a
fresh start. That is a content lane where the honesty is the product.

Nothing in this repository verifies anything about function 6, and that should be said
plainly rather than dressed up.

## 7. Etsy / Craigslist — a sellable service

**Operations, mostly outside what the boards do.** Two pieces fit and they are the two worth
having.

**Unit economics is filing-shaped.** The platform's own API is the primary source, the way
EDGAR is for an equity: orders, fees and payouts are retrievable and settled. The recurring
error is this repository's own — an unmodelled fee reads as margin that does not exist.
Listing fee, transaction fee, payment processing, offsite ads charged on some orders and not
others, postage subsidy, refunds.

**The fee monitor is the strongest fit of anything in the seven.** A platform changes its
fees and every margin resting on the old numbers is void — structurally identical to a proxy
implementation swap voiding a contract review, and the obligation table already has the
shape for it.

The prerequisite is not technical: it is having a service worth selling.

---

## What is refused across all seven

- **A score.** Opportunity score, shop health, confidence out of five. The argument is in
  `lib/candidates.py` and does not weaken by being moved to a new domain.
- **Demand forecasting.** What will sell, what an app will earn, what a channel will draw.
- **Asking prices treated as achievable prices**, in flipping or anywhere else.
- **Backtest-derived confidence**, including "historical reliability" as an input.

## The order that holds

1. Ratify the three decisions sitting at `GOVERNANCE_VALIDATION`. Closes 2, 3 and 5.
2. One free credential each for arb (Smarkets) and stocks (Alpaca paper). Those two lanes
   then run end to end.
3. Persistence, once. Everything above stops dying with the container.
4. **Prove one function produces something real before starting a fourth.**
5. Then flipping via eBay sold listings, then app discovery, then the rest.

Step 4 is the one that gets skipped. Four lanes exist and none has yet produced a pound.
