# The end state, by function

Stated by Ian on 2026-08-08, at the end of the session that first ran all three money lanes
against real sources. `docs/target-functions.md` (2026-08-02) is the canonical list of what
each function IS and what it needs to exist; this document is the **autonomy target** — how
far each is meant to run on its own once it exists, in Ian's own words, with an engineer's
read on what each will actually take. It adds two functions beyond the original seven and a
second mode for arb.

It is a direction, not a plan. Nothing here is a commitment to a schedule, and several
entries are gated on judgements or profiles that do not exist yet. Read it to understand
where a lane is heading before you change it; read `next-work.md` for what is actually next.

**The doctrine still wins.** Where an end-state below wants a machine to originate a reason
to act, that reason still has to come from an evidence source and a thesis, not from
loosening a gate. Where it wants a human's judgement automated, `CLAUDE.md`'s never-automate
list still holds. An ambition to run autonomously is not permission to route around the
thing that makes the output trustworthy.

---

## Money lanes

### Stocks — fully autonomous
**Target:** feeds on information, selects its own names, buys at a price and sells at a
price, sized by its level. **Standing.**

The buy path is built to the edge of placing and the broker is wired. The two pieces
between here and the target are real: **a source that produces candidate names** (today the
watchlist is hand-picked — the lane disqualifies, it does not select), and **a sell
discipline** (today it only sizes buys; nothing decides when to exit). Selection is the
harder half, because "feeds on information and selects" is precisely the step the thesis
gate reserves for a human — so autonomous selection needs an evidence source good enough to
author a thesis from, reviewed as such, not a gate turned off. Capital by level is
`docs/levelling-design.md`.

### Crypto — fully autonomous, same shape as stocks
**Target:** feeds on information, makes its own selections, sized by level.

The gates and the reaper exist and the lane already reaches a sized instruction; its final
step is an unsigned transaction. Two things stand between here and the target, and they are
not the same size. The signing question is the smaller and the more dangerous:
`CLAUDE.md` says the chain lane cannot sign and that is not a setting — closing the loop to
"buys and sells on its own" means adding a signing path, which is a deliberate, isolated,
explicitly-authorised piece of work and nothing to reach for casually. The larger piece is
the same as stocks: a source of a *reason to buy*. The four chain gates are hygiene — they
prove a contract is what it claims — and hygiene is not an edge. Autonomous crypto needs an
evidence source (on-chain flow, liquidity depth, holder concentration) that can justify a
position, which is a genuine research project.

### Arb — manual, with two possible extensions
**Target now:** stays manual to the degree the venues force — bookmakers take no orders from
a program, so the slip is the deliverable and always will be. Within that, it can run
autonomously up to *producing* the slip and notifying urgently.

**Extension A — autonomous placing where a venue allows it.** The exchanges (Betfair,
Smarkets) do have APIs. An arb with an exchange leg could place that leg automatically while
the soft-book leg stays a manual slip. Real, and it changes the risk shape: a half-placed
arb is an unhedged single until the second leg lands.

**Extension B — a betting thesis, not an arb.** A separate mode that takes single-selection
positions on sports it forms a view on, rather than hedged pairs. This is a different animal
from arbitrage and must not be built inside it: an arb asserts nothing about the outcome and
is defensible under a standing authority for exactly that reason (`lib/arb.py`), whereas a
single bet IS a claim about the outcome and needs a thesis per selection, the same as
stocks. Sharing the odds plumbing is fine; sharing the authority model is the error to
avoid.

---

## Commerce lanes

### Flipper — autonomous to a notified suggestion, with urgency tiers
**Target:** runs on its own to the point of suggesting an item with a buy price and a sell
price. **Filtered by rarity and profit, with two urgency tiers:** a severely underpriced
item notifies *fast and loud*; a small-margin item notifies quietly and is explicitly not a
do-or-die.

The urgency split is the sharp design idea and it maps straight onto the notifier just
built — two message priorities rather than one. The hard part is upstream and unchanged from
`target-functions.md`: **sold price is evidence, asking price is not**, and eBay's
sold-comparables data is the approval-gated part of its API. The whole function rests on
reaching that data; verify it is reachable before building on it. The exit stays a
`REFERENCE_RATE` — sold comparables say others sold at a price, not that you will — so the
"sell price" in a suggestion is a distribution with a refusal to size against it as if it
were locked.

### Etsy / Shopify — autonomous as far as it can be taken
**Target:** as autonomous as possible, with Ian's acknowledgement that this one needs real
work from him — inventory, or a service, has to exist first.

Nothing here is arbitrage-shaped, so the reaper's disqualify-and-refuse machinery is a poor
fit. What this needs is unit economics (fees before margin, always) and a fee monitor, which
is closer to the pricing job than to a lane. The autonomy ceiling is low until there is a
real product with real costs to reason about.

---

## Content and discovery lanes

### App development — autonomous pain-discovery
**Target:** reads public forums, surveys and anything else we can lawfully access and feed
it, to answer: what apps do people want, what do they complain about, would they pay, or is
it ad-supported-free?

The engineering-review half exists (RBM-002). The missing half is a **complaint source**,
and the honest constraint is legality and terms-of-service: "anything we can access" has to
mean sources whose terms permit it, not scraping that a platform forbids — the same
discipline that keeps Facebook Marketplace out of the flipper. Willingness-to-pay is a
genuinely hard inference and should be reported as a `REFERENCE_RATE`-style estimate with
its uncertainty, never as a fact.

### Faceless YouTube — autonomous generation, human posting
**Target:** Ian picks the niche and sets up the accounts and the AI/info side; the system
generates the shorts — sound, overlay, background — and posts on a cadence.

`target-functions.md` says policy check first, and that stands: platform rules on AI-
generated content and monetisation eligibility decide whether this is viable *before* any
pipeline is worth building. Keep the human in the posting loop at least until the policy
position is settled, because the failure here is not a bad video, it is a terminated channel
that takes its back-catalogue with it.

---

## Cross-cutting engines

### Opportunity engine — always-on discovery
**Target:** constantly searches for ways to make money *outside* the existing functions,
however that ends up working.

This is the most open-ended entry and the one most in tension with the doctrine, so it needs
the tightest framing. A general "find money" agent is exactly the kind of thing that
manufactures a confident answer out of noise. The defensible version is narrow: it surfaces
*candidates* — a market, a mispricing, a gap — as `REFERENCE_RATE` leads with their evidence
attached, and every candidate then has to pass through a function that can actually gate it,
or become a new function designed deliberately. It proposes; it never authorises. If it ever
starts *acting* on its own finds, it has become the thing this whole system is built to
refuse.

### Security research engine — authorised-scope only, and this is not negotiable
**Target as Ian stated it:** a bounty-hunter AI for security issues in apps, code, websites
"or anything that may be worth money to someone if found", run autonomously.

The legitimate version of this is real and valuable: **automated research against targets
that have authorised it** — public bug-bounty programs within their stated scope, your own
code and infrastructure, and engagements with written permission. That is defensible,
lawful, and genuinely a way the system could earn.

The line that must be drawn in the design, not left to runtime judgement: **testing a system
you have not been authorised to test is unauthorised access, and "worth money to someone if
found" is not authorisation.** "Banking, anything" as targets is where this goes wrong — a
bank you have no agreement with is a crime scene, not a bounty. So if this is built, it is
built scoped: it takes a *list of authorised programs and their rules*, refuses anything
outside that list the way the arb lane refuses an undeclared settlement, and treats scope
the way every other lane treats a missing gate — absent scope blocks, it does not default to
permitted. Framed that way it fits the doctrine exactly. Framed as "find breaches anywhere
worth money" it does not, and I will build the first and not the second. Raising this once,
here: the scoped version is the one worth having, and it is also the only one that keeps you
out of a courtroom.

---

## What is common to all of these

Every "autonomous" above still bottoms out on the same two questions this system already
answers well: **where does the reason to act come from, and what stops it when it is
wrong.** A lane is ready to run on its own when it has an evidence source good enough to
justify the action, a thesis or declaration that a named human stood behind, breakers that
fail closed, and a notifier whose silence means something. Autonomy is the last thing you
add, not the first — and it is added per lane, asserted, never assumed, exactly as
`lib/operating.py` already requires.
