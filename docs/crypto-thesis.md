# Two crypto theses, and what each one needs

Stated by Ian on 2026-08-09. Recorded here because they are the *reasons*, and this
repository is built so that reasons come from a named human and gates come from the
machine. Each is written out verbatim, followed by an engineer's read of what it would take
to run — which differs enormously between them.

**These are not equivalent pieces of work.** The first is close to usable with what exists.
The second is a different lane with different controls, and it deliberately targets the
asset profile the current crypto gates were built to refuse.

---

## Thesis A — conviction

> Acquire and hold cryptoassets where independently verifiable evidence supports durable
> demand, sustained network relevance, credible security and decentralisation, and a clear
> mechanism through which continued adoption benefits the asset itself. Capital is deployed
> when long-term expected value materially exceeds current valuation, not because of
> short-term price momentum.

### What this is compatible with today

Almost everything. This is the same shape the stocks lane already runs: **Ian names the
asset and states the reason; the machine disqualifies.** The four chain gates —
does the contract answer, can the code be swapped under you, is there a way out, is the
round trip affordable — are exactly the hygiene an asset held under this thesis should pass,
and a major asset generally will.

So Thesis A needs no new profile, no loosened gate and no signing path. It needs assets
named, a thesis per asset, and the lane run. Its output is a sized instruction and an
unsigned transaction Ian signs — the same manual final step as an arb slip.

### The two honest gaps

**The gates do not measure what the thesis argues.** "Durable demand, sustained network
relevance, credible security and decentralisation" is not what a proxy check or a liquidity
probe establishes. The gates prove a contract is what it claims — hygiene, not an edge. So
the *evidence* for Thesis A is Ian's research, and the system's role is to refuse assets
that fail hygiene regardless of how good the story is. That is the correct division of
labour and matches stocks exactly; it should just not be mistaken for the system agreeing
with the thesis.

**"Long-term expected value materially exceeds current valuation" is a judgement nothing
here computes.** No valuation model exists, and building one would be a forecast — which
`status.py` says plainly it does not make. So the *trigger* to buy is Ian's, and the lane's
job is to size it, gate it and refuse it when a control says no.

Adding evidence that speaks to this thesis is a real, buildable project: network activity,
active addresses, developer activity, holder distribution, staking or fee-burn mechanics for
the "adoption benefits the asset" clause. That is a connector and a set of gates, not a
change to any guard.

### To run it

1. Name the assets. The lane disqualifies; it does not select.
2. A thesis per asset under this heading, with what could go wrong for that asset
   specifically — the same shape as `examples/theses.ai-infrastructure.json`.
3. Check each contract on Etherscan character by character before it goes in a watchlist.

---

## Thesis B — capped speculative

> Deploy strictly capped, disposable capital into highly speculative low-priced/microcap
> cryptoassets when observable market data indicates an abnormal acceleration in liquidity,
> volume, attention and price discovery that may precede a short-lived speculative
> expansion. The objective is not to identify durable value, but to capture part of the
> move while enforcing predetermined loss, exposure and exit constraints.

This is well-formed and unusually honest — it states what it is not, it caps the capital,
and it names its controls up front. That is the right frame. What follows is what it would
actually take, because the gap between this thesis and this codebase is wide and specific.

### It targets the asset profile the crypto gates exist to refuse

This is the central point and it is structural, not an implementation detail.

| gate | why a microcap typically fails it |
|---|---|
| the code cannot be swapped under you | low-cap tokens are overwhelmingly upgradeable proxies |
| there is a way out | thin books; the exit is the whole risk |
| the round trip is affordable | fixed costs dominate on small notional; tax-on-transfer is common |

Those three gates are a fairly precise description of what makes a microcap dangerous. So
Thesis B cannot run through the existing crypto lane: with the gates intact it finds
nothing, and with them loosened the existing lane loses the guarantees that make it worth
having.

**The answer is a separate lane, not a mode of the crypto lane.** Its own gates, appropriate
to its own risk, its own ring-fence, its own cadence. Sharing the chain connector is fine;
sharing the crypto lane's gate set is the error to avoid — the same reasoning as keeping a
single-selection betting thesis out of the arb lane in `docs/end-state.md`.

### Four mechanisms it needs that do not exist

**1. Exit logic. Nothing in this system has ever produced a sell.** `lib/portfolio.py` and
the Alpaca adapter both understand `SELL`, but no reaper emits one. Every lane sizes an
entry and stops. Thesis B is *defined* by its exit — "capture part of the move… enforcing
predetermined loss, exposure and exit constraints" — so the exit is not a later feature, it
is the thesis. A lane that can buy a microcap and cannot sell it is strictly worse than no
lane.

**2. A cadence that matches the horizon.** Crypto runs every six hours
(`REAP_CADENCES = {"crypto": 6 * 3600}`). A short-lived speculative expansion is minutes to
hours. Six hours does not observe it; it observes the aftermath. Whatever cadence this needs,
it is a different order of magnitude, and that has cost and rate-limit consequences that
must be designed rather than discovered.

**3. Signing, which is the one that collides with doctrine.** `CLAUDE.md`: *the chain lane
cannot sign, and that is not a setting. Do not add one.* A strategy whose window is minutes
cannot have a human signing each transaction — so Thesis B, executed as written, requires a
signing path. That is a deliberate, isolated, explicitly-authorised piece of work with its
own review, and it is the single most dangerous change that could be made to this
repository. **It is not to be added as part of building a lane.** If Thesis B is built, the
honest first version notifies urgently and Ian signs; if that proves too slow to capture
anything, that is a finding, and the signing question is then asked on its own merits rather
than smuggled in as plumbing.

**4. Per-position stops and targets.** The breakers are portfolio-level — daily loss,
consecutive losses, deployed capital, concurrent positions. They stop a *lane*. Thesis B
needs a control that exits a *position* at a predetermined level, which is a different
mechanism and does not exist. Ian has already specified the right three (loss, exposure,
exit); none of them has an implementation.

### One market-structure fact worth stating once

"Abnormal acceleration in liquidity, volume, attention" is, in microcaps, frequently
manufactured by people who are positioned to sell into it. The signal and the adverse
selection are the same event observed from two sides. That is not an argument against the
thesis — it is the reason the thesis's own framing is right: **strictly capped, disposable,
predetermined exits.** Those constraints are the correct response to that fact, and they are
load-bearing rather than decorative. A version of this lane that quietly relaxed the cap
would not be a more aggressive version of the same strategy; it would be a different and
much worse one.

### What a first version looks like

Deliberately modest, and useful even if it never places:

- a **detector**, not a trader: observe the market data, and when the acceleration
  criteria fire, notify **URGENT** through `lib/notify.py` with what was observed
- its own ring-fence, sized as capital Ian is prepared to lose entirely
- its own gates: liquidity depth on both sides, honeypot and transfer-tax checks, holder
  concentration — the checks that matter for this asset class, rather than the ones that
  matter for a durable holding
- entry, stop and target stated **in the notification**, so the exit is decided before the
  position exists rather than in the middle of a move
- manual execution while it is proven

That version is buildable without touching a single guard, and it answers the question that
decides everything else: **does the detector actually fire before the move, or after it?**
If it fires after, no amount of execution speed helps and the lane should not exist. If it
fires before, the case for faster execution can be made on evidence.

---

## Where this leaves the crypto side

| | Thesis A | Thesis B |
|---|---|---|
| new lane needed | no | **yes** |
| existing gates suit it | yes | **no — they refuse the asset class by design** |
| needs exit logic | not for a hold | **yes, it is the thesis** |
| needs signing | no | yes, as written — deferred deliberately |
| buildable now | **yes, name the assets** | detector first, execution on evidence |

**Recommended order.** Thesis A first, because it runs on what exists and produces a real
holding path. Thesis B as a detector second, because it is genuinely interesting, cheap to
prove or disprove, and tells us whether the expensive parts are worth building.

## Open inputs — Ian's, not the code's

1. **Which assets for Thesis A.** The lane disqualifies; it does not select.
2. **The Thesis B ring-fence** — capital he would be content to lose in full.
3. **The three constraints numerically**: predetermined loss, maximum exposure, exit rule.
4. **What counts as "abnormal acceleration"** — the thresholds are the strategy, and they
   are his to set, not the system's to infer.

---

## Measured 2026-08-09, and the reason this lane is parked

Both theses above were written before the assets were checked against the chain. They were
then checked, and what the checks found is why the crypto side is **parked** — not
abandoned, and not because either thesis is wrong.

### The lane can only see ERC-20 contracts on Ethereum

Every gate is built on `eth_call` against a **token contract address**: `totalSupply`,
`symbol`, the proxy storage slots, the round-trip probe. That is the whole evidence model,
and it has a consequence nobody had stated:

| candidate | gateable | why |
|---|---|---|
| **Bitcoin** | **no** | different chain. No Ethereum contract, no `eth_call`, nothing to read |
| **Ethereum (ETH)** | **no** | the *native* asset has no contract address. WETH is a wrapper, not ETH |
| **Hyperliquid** | **no** | its own L1, not Ethereum mainnet |
| ERC-20s on Ethereum | yes | the only thing this lane evaluates |

**The assets with the strongest Thesis A case are the ones the lane is least able to
gate**, and that is not an implementation gap to close. The gates exist to catch a contract
being swapped under you, a book with no exit, a round trip that costs more than it returns.
BTC and ETH structurally do not have those risks — there is no admin key and no contract.
Routing them through this lane would be ceremony, not safety. Hold them directly, as the
stables are held, and let portfolio valuation cover them once `docs/pricing-design.md` is
built.

### The proxy gate, run against real candidates

Measured on live chain state at block ~25,713,003 via a public endpoint:

| token | proxy gate | detail |
|---|---|---|
| **USDC** | **UPGRADEABLE** | `zeppelinos_admin`, `zeppelinos_implementation` |
| **AAVE** | **UPGRADEABLE** | `eip1967_implementation` |
| USDT, DAI, LINK, UNI | INDETERMINATE | **every storage probe unreachable** |

**The four INDETERMINATE results are not findings about those tokens.** The public endpoint
used (`1rpc.io`, which this repository's own measurements document as unreliable) failed
every probe. `proxy_finding` correctly refuses to conclude NO_PATTERN_MATCHED from probes
that never ran — "a measurement over an incomplete numerator" — so the third state is
working exactly as designed. Re-run on the keyed QuickNode endpoint for real answers.

AAVE being an upgradeable proxy is a real fact about a real candidate, found before any
money moved. That is the lane earning its keep.

### Stablecoins do not fit Thesis A

Thesis A deploys capital when "long-term expected value materially exceeds current
valuation". A stablecoin is engineered so that never happens. There is no mechanism by which
adoption benefits the asset — adoption benefits the *issuer*, who keeps the interest on the
reserves. USDT, USDC and DAI are **cash**: the settlement asset held between positions.
Legitimate, and not a holding under this thesis. Do not write one for them.

### Why parked rather than dropped

The lane already does the thing `docs/target-functions.md` said it was for: **the veto and
the monitor**. It told Ian something true and specific about USDC, and about AAVE. That
keeps working at zero further cost.

What is deferred is *execution*, which is where all the cost and all the risk are. Nothing
here needs undoing to restart it, and both theses stay on file as recorded judgement.

**If crypto exposure is wanted meanwhile**, the honest route is the lane that already runs:
crypto-infrastructure equities — exchanges, custody, tokenisation rails, stablecoin issuers
— are real businesses with filings, gateable by EDGAR and sizeable today, where a token
offers contract hygiene and an asserted mechanism.
