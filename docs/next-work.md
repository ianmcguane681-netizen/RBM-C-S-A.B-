# Next work — checkpoint 2026-08-03

> **Updated `7d7b12b`. ALL FIVE GAPS ARE CLOSED.** The checkpoint below is the record of
> how they were closed, not a plan. Gaps 4 and 5 came from Codex on
> `codex/request-for-feedback` and were merged at `c6c02ce`.
>
> The stocks lane runs the whole loop unattended: research → breakers → place at Alpaca →
> position recorded → settled outcome fed back to the breakers that gate the next one, on a
> 24h cadence, deduped, with the owner able to take the wheel from a file.
>
> **Next is not a gap — it is the fourth of the seven functions: the flipper.** See the
> "After the gaps" section for why it needs a different architecture from these three.
> Open questions: no sizing ramp (a lane with zero settled outcomes sizes like one with
> two hundred), and no Obsidian vault. 1187 tests.

Written to be picked up cold, by a session that has none of the conversation behind it.
Read this, then `README.md`'s "Running the lanes without a board" section, and you have
enough.

**State at this checkpoint:** 992 tests, 2 skipped, `main` at `ba01517`. All three reaper
lanes reach `READY`. `python run.py --reap` runs them.

---

## The picture

```
   RESEARCH ─────────────────────────────────────────►  EXECUTION
   ┌──────────────────────────────────────────┐         ┌──────────────┐
   │ look → screen → gates → thesis → size    │         │   adapter    │
   │                          │               │         │   places it  │
   │                     ┌────▼────┐          │         │              │
   │                     │BREAKERS │          │         └──────┬───────┘
   │                     └────┬────┘          │                │
   │                          ▼               │                │
   │                       READY  ────────────┼── ✗ ───────────┘
   └──────────────────────────────────────────┘   GAP 2: NO WIRE
                                                            │
                              ┌── ✗ ─────────────────────────┘
                              │   GAP 1: NO RETURN LEG
                         ┌────▼────┐
                         │BREAKERS │  ← never receives an outcome
                         └─────────┘
```

Everything left of `READY` is built and tested. Nothing crosses either gap.

### Verified facts, not recollection

Checked at this checkpoint with grep:

- `Breakers.record()` (`lib/breakers.py:294`) is called by **no production code**. Only
  `monitor.py:151` and `scan_arb.py:185` / `screen.py:101` call `.record(` on anything, and
  those are the monitor ledger and the seen register.
- `AlpacaBroker` is imported in `lib/stocks_reaper.py:483` **for reading only** —
  `quote()` and `daily_closes()`. `AlpacaBroker.place()` is called by nothing.
- `connectors/betfair_exec.py::place_arb` is called by nothing.
- There is **no** `Instruction(` construction anywhere outside `connectors/alpaca.py`, so
  no `StockOrder` → `Instruction` bridge exists.
- `SeenRegister` is used by `scan_arb.py` and `screen.py` only — no reaper touches it.

---

## Gap 1 — the return leg  ✅ CLOSED

Three of the six circuit-breaker controls can never fire, because nothing ever tells a
breaker what happened. Daily loss reads zero. Consecutive losses reads zero.
Previously-tripped can never have tripped. The kill switch, position cap and sanity bound
work; the three that catch *a strategy going wrong over time* are decorative.

This is the recurring defect one level up: protection that looks present and cannot engage.
It has to be closed before Gap 2, because wiring execution first means placing real orders
into a system with three dead safety controls.

### `lib/outcomes.py`

Follow the `SeenRegister` / `Breakers` shape exactly: a JSON file, a `readable` flag, a
`reason`, a `.receipt.json` beside it, and `lib/store.inspect` for the LOST/FRESH status.

```python
OPEN     = "OPEN"       # placed, not yet settled
SETTLED  = "SETTLED"    # we know the result
VOID     = "VOID"       # stake returned; neither a win nor a loss
UNKNOWN  = "UNKNOWN"    # placed, and we could not find out what happened
```

**The sentinel this type exists to prevent.** An unsettled position is *not* a
zero-profit position. Recording `0.0` for something still running would contribute nothing
to the daily loss AND end a losing streak, both in the flattering direction. So `Position.profit`
returns `None` unless the status is `SETTLED`, and `apply_to_breakers` skips everything else.

**`VOID` is deliberately not fed to the breakers at all.** A voided bet is neither a win nor
a loss, and passing `0.0` would end a consecutive-loss run without a win having happened.
Check `Breakers.consecutive_losses()` with the code in front of you and confirm — the
existing test `test_a_win_ends_the_run` records `+1.0`, so a `0.0` may or may not break the
run depending on whether the comparison is `< 0` or `<= 0`. Whichever it is, VOID must not
reach it.

```python
@dataclass(frozen=True, slots=True)
class Position:
    position_id: str        # deterministic: lane + subject + opened_at
    lane: str
    subject: str
    status: str
    staked: float
    returned: float = 0.0
    opened_at: str = ""
    settled_at: str = ""
    source: str = ""        # MANUAL | BROKER | CHAIN — how we know
    note: str = ""
    applied_to_breakers: bool = False

    @property
    def profit(self) -> float | None:   # None unless SETTLED
```

`OutcomeLedger`:

- `open_position(lane, subject, staked, source)` → `Position`
- `settle(position_id, returned, *, source, note)`
- `void(position_id, note)` / `mark_unknown(position_id, reason)`
- `unsettled_exposure(lane)` — the number the daily-loss limit is blind to
- `stale_open(hours)` — positions open too long, which is how an `UNKNOWN` hides as an `OPEN`
- `save()` — refuses to overwrite an unreadable file, same as `Breakers.save()`

### `apply_to_breakers(ledger, breakers)`

Idempotent via the `applied_to_breakers` flag, because `Breakers.record()` appends and
re-applying would double-count.

**Ordering matters and it fails in the safe direction:**

```
breakers.record(profit) → breakers.save() → set applied flag → ledger.save()
```

A crash between the flag and the ledger save double-counts a loss on the next run, which
trips a breaker *earlier*. The reverse ordering would silently drop the loss. Fail toward
stopping. State this in the docstring.

### `positions.py` — the CLI  *(built)*

Bookmakers have no settlement API, so manual entry is the honest interface for the arb lane.
That is fine. What is not fine is a breaker silently reading zero.

```bash
python positions.py --list                              # open, stale first
python positions.py --placed arb "Arsenal v Chelsea" --staked 499.98
python positions.py --settle POS-0001 --returned 541.08
python positions.py --void POS-0001 --note "abandoned, both books voided"
python positions.py --unknown POS-0001 --note "bet365 restricted the account"
```

Exit codes: `0` nothing needs you, `1` positions await settlement, `2` the ledger is
unreadable.

### Tests to write

- an OPEN position contributes nothing to the breakers, and is not a zero
- a VOID does not end a consecutive-loss run
- applying twice does not double-count
- an unreadable ledger refuses to be overwritten
- `stale_open` surfaces a position open for days
- four losses recorded through the ledger actually trip the lane's breaker *(this is the
  end-to-end proof that the gap is closed)*

### Gitignore

`data/outcomes.json` — it records what was staked and on what. Same reasoning as the seen
register: the repo is public. The `.receipt.json` stays trackable (counts and dates, never
subjects).

---

## Gap 2 — `READY` → adapter  ✅ CLOSED

The seam is a missing conversion. `lib/stocks_reaper.StockOrder` carries ticker, shares,
price, cash, bound_by. `connectors/alpaca.Instruction` needs symbol, side, quantity,
`permission`, `client_order_id`. `instruction_id()` at `connectors/alpaca.py:414` already
computes the stable id from `(subject, side, quantity, thesis_declared_at)` — that is the
retry-safety mechanism, so the bridge must use it rather than inventing an id.

Design notes:

- Placing stays a **separate deliberate command**, not something `--reap` does. Something
  like `python place.py POS-0001` reading the harvest back, or `--place <lane>` behind an
  explicit flag. `autonomous_execution` exists on `Reaper` and defaults to `False`; the user
  has authorised turning it on for stocks, but that is a second step after a placement path
  exists at all and has been watched working.
- On a successful place, open a `Position` in the ledger immediately, in the same call. An
  order that filled and was never recorded is exactly the hole Gap 1 just closed.
- `OrderResult.UNKNOWN` (5xx) must open the position as `UNKNOWN`, not skip it.
  `order_by_client_id()` is the resolver.
- **Arb:** `betfair_exec.place_arb()` covers *exchanges only*. Since the pivot to
  bookmakers (bet365 one price, Sky Bet the other), the bet slip **is** the deliverable —
  those books have no betting API and no amount of engineering changes that. Do not build an
  adapter for them. Wiring `place_arb` is a side path worth doing only if Smarkets/Betfair
  come back into play.
- **Crypto: nothing to wire, by design.** `connectors/chain_exec.py` has no key path, no
  signing library and no send method. Leave it.

---

## Gap 3 — dedup  ✅ CLOSED

`SeenRegister` exists and no reaper uses it, so the same arb resurfaces every 30 minutes as
if new.

Put it on `Reaper` itself rather than per lane — it is a cross-lane concern:

- new fields `register` and `identity: Callable[[subject], str]`
- new `Harvest.seen: SeenVerdict | None`, printed by `describe()`
- record on reaching `READY` (not on every subject examined — the register means "was put in
  front of you")
- `arb_identity(market, legs)` already exists in `lib/seen.py`; stocks and crypto need
  trivial equivalents (ticker, token address)

**Decision already taken:** an unreadable register **blocks**, consistent with
`gate_findings` and `Breakers` failing closed. That means **deleting the arb-specific
`SEEN_REGISTER_UNREADABLE` gate** in `lib/arb_reaper.gates_for` so there are not two
mechanisms doing the same job. Its test moves to the reaper-level tests.

---

## Gap 4 — cadence  ✅ CLOSED (Codex)

`--reap` is manual. Add it to `run.py`'s `LANES` so it runs under the orchestrator's queue
throttle — which matters here, because three lanes producing `READY` instructions is exactly
what the throttle exists for.

Three separate orchestrator lanes rather than one, because the cadence principle already
stated in `run.py`'s docstring is "how fast the underlying thing actually moves":

| lane | cadence | why |
|---|---|---|
| `reap-arb` | 30 min | odds move in seconds; bounded by API quota, not usefulness |
| `reap-crypto` | 6 h | chain state and pool depth move slowly |
| `reap-stocks` | 24 h | filings move slowest of all |

Needs `python run.py --reap [lane]` to accept a single lane name. `run.py` invoking itself
by subprocess is safe — `--reap` does not call `main()`, so there is no recursion.

`findings_exit_codes=(1,)`, `unconfigured_exit_codes=(2,)` — the codes are already right.

---

## Gap 5 — `status.py` sees the money side  ✅ CLOSED (Codex)

Currently reports connector readiness and nothing about money. Add:

- ring-fence balance and currency per lane
- breaker state — ARMED / TRIPPED, what tripped it, when, and that it does not self-clear
- open positions and unsettled exposure from the Gap 1 ledger
- anything that reached `READY` and was never resolved
- the third states throughout: a lane with no breaker file is `NOT_CONFIGURED`, not "£0 at
  risk"

Also worth folding into `preflight.py`: it reports connector readiness but not the two things
that will actually stop a run — *no settlement declaration for the books the arb lane wants*
and *no thesis on file for a watchlist entry*.

---

## After the gaps

**The Obsidian vault** (discussed, not started). One-directional, system → vault. A markdown
file per `READY` instruction and per settled outcome, with YAML frontmatter so the Dataview
plugin renders a live table. `python run.py --reap --vault ~/vault/trading`. Roughly two
hours. Worth doing *after* Gap 1, because a slip with no record of what happened to it is
half a note. Writing *back* from Obsidian stays out of scope — the ledger needs validation
and atomic writes, and a hand-edited markdown file has neither. The vault lives in a user
directory, never in this public repo.

**Function 4 of seven: the flipper** (Facebook / DoneDeal / eBay / Amazon).

Note the architectural split, because it is real and the flipper must not be built as a copy
of the arb lane:

| functions | input | LLM in the loop? |
|---|---|---|
| arb, stocks, crypto | numbers, already structured | **no** — it would make them worse |
| flipper, apps, YouTube, Etsy | freeform text and images | **yes** — that is the whole problem |

The first three are arithmetic on structured data, and a model in the decision path adds
nondeterminism where it is least affordable. The next four are judgement on unstructured
text. The pattern that survives contact with money: a model reads listings and emits
*structured output*, then deterministic code decides. Not agents talking to agents.

Remaining after that: app making, faceless YouTube, Etsy/Craigslist.

---

## Blocked on Ian, not on code

- **The QuickNode URL is still unrotated.** It embeds an auth token in its path. It lives
  only at the scratchpad path in `$QUICKNODE_ETHEREUM_URL`, mode 600, and a test asserts it
  never reaches preflight output — but it has been flagged repeatedly across sessions and
  QuickNode's Console API is plan-gated, so the connector cannot rotate it.
- **The CourtListener token** appeared in an earlier transcript and should be rotated.
- **No lane can reach a source until keys exist:** `~/.oddsapi/key` and `~/.alpaca/`, both
  mode 600. Never paste credentials into chat.
- **A settlement declaration** for whichever two bookmakers will actually be used — an
  evening with their abandonment and non-runner rules pages, once. Until then the arb lane
  correctly stops at `INDETERMINATE` and names the exact key it wants.

---

## Conventions a fresh session needs

- **The recurring defect this whole repository is organised around:** a value meaning *not
  found / unknown* rendering as *not there*. Every module has a third state for it. When in
  doubt, add one rather than picking a default.
- Tests state a property in their name and the file docstring argues why the property
  matters. Match that; do not write `test_returns_true`.
- Comments explain *why*, and several record the specific bug that motivated the line.
- A refusal must name what a person can go and do about it.
- Ratifying, verifying, declaring settlement equivalence and authoring a thesis are human
  acts. Every automation prefix — `agent:`, `ai:`, `model:`, `automation:` — is refused, and
  that guard must not be worked around.
- Ian granted standing authority for engineering decisions on 2026-08-02, and separately
  authorised board ratifications. He has approved autonomous decision-making for the money
  lanes (stocks, crypto, flipper, app development) since the system is deployed in-house
  rather than sold. `autonomous_execution` still defaults to `False` and the chain lane
  refuses it outright.


---

# The UI contract, and what was declined with it

Added 2026-08-04 from a review of `codex/request-for-feedback-73js4m` (PR #3). That branch
was cut before `lib/placing.py` existed and merging it would have deleted the placing path
and its 424 tests, so it was taken apart rather than merged. What was taken:

- `--json` on `run.py --reap`, `positions.py` and `status.py`, plus `to_dict()` on the
  types behind them. `docs/ui-integration.md` states the contract; `lib/ui_contract.py`
  holds the one version number.
- `Usage.to_dict()` on the odds feed. `scan_arb --json` was publishing the `-1` sentinel
  as `quota_remaining`, which is this repository's own defect at the last layer.
- The bookmaker filter, **opt-in** rather than the branch's default of five hard-coded
  provider keys. Naming books halves what a scan costs and also narrows what was looked
  at, and a key that is wrong or not carried in this region returns 200 with the book
  absent — a quiet market from a narrower look than anybody chose.

**Three things were declined, and the reasons matter more than the code.**

1. **`DeclarationCoverage`** — composing per-book declarations into one covering a set of
   books. Equivalence is a claim about a *pair*: that two differently worded rules settle
   the same way. Two people each reading one book's rules have not made it, so the type
   manufactured a human judgement nobody made, and did it by duck-typing past
   `EquivalenceDeclaration.__post_init__` — the guard that refuses automation prefixes.
   The arb lane stopping at INDETERMINATE and naming the key it wants is the feature.
2. **`lib/functions.py`** — a hard-coded UI registry asserting `ALPACA_ADAPTER_UNWIRED`
   and "READY StockOrder is not yet converted to an Alpaca Instruction". Both were true
   before Gap 2 closed and false when written. A registry that tells a front end
   placement is unwired while it is wired is the same defect pointing the other way; if
   one is wanted it has to be derived from real state.
3. **An `sre` "Security Research Engine" slot**, which appears in none of the seven
   functions and arrived with a scanner roadmap attached.

Also declined from the same branch: raising the arb grant's `max_exposure` from 20 to 50
with no stated reason, and deleting `OutcomeLedger.amend_stake`.

## The execution path could be borrowed by a lane it was never written for

Found while extending the lane registry into the reapers. `place_harvest` ENDED with
`return _place_stock(...)`. Every refusal above it named a lane — arb and crypto have no
adapter, the mode is not AUTONOMOUS, the ledger is unreadable — and anything surviving them
went to the stock placer. Not because it was stocks; because it was not one of the two
lanes that had been thought about.

A flipper instruction with a broker attached would have been submitted as an equity order.
This module records the position BEFORE it sends, so the first evidence would have been a
phantom position beside a broker error — the direction the whole repository refuses to fail
in, in the one module that cannot undo what it does.

`PLACERS` now maps a lane to the single function permitted to submit for it, and a lane in
neither `PLACERS` nor `NO_ADAPTER` is REFUSED by name, before anything is recorded, saying
which of the two registries its answer belongs in. `BROKER_FACTORIES` does the same for the
`if lane == "stocks"` branch that used to sit in `lib.reaping._place`.

**Two things restated in the code while there.** `lib/reaper.py`'s "Autonomy stops before
money" section still said placing was never automatic — true before `lib/placing.py`
existed, and understating what the system does with money is the wrong direction to be
wrong in. It now says autonomy is the target, asserted via `autonomous_execution` and
overridden by `data/MANUAL`, `data/HALT` and `NEVER_AUTONOMOUS`. The board being optional
was already argued there and needed nothing.

## Adding a fourth lane is one decision now, 2026-08-04

The focus stays the core three. But more lanes have always been planned — flipper, an app
studio, media, commerce and more — and the code had drifted into needing **five** edits to
add one, in five files, four of which fail silently:

| Where | What a fourth lane did |
|---|---|
| `lib/reaping.assemble` | `builders[lane]` → **KeyError**, losing every other lane's result with it |
| `status.MONEY_LANES` | a second lane list; absent from the one screen that shows what can spend |
| `backend.ReaperCommand` | `Literal` three names long → 422 from a file nobody would look in |
| `run.LANES` | never scheduled, and never running looks exactly like finding nothing |
| `preflight.all_lanes` | no `engines` row, so **no division card at all** on the dashboard |

All five now derive from `lib.reaping.LANES`. What remains per lane is the real work —
an `assemble_<lane>()` and a `<lane>_lane()` readiness description — and both are now
*reported* when missing rather than crashing or vanishing: a declared lane with no builder
is REFUSED naming the function to write, and one with no readiness description is BLOCKED
saying nobody has written down what it needs. An undescribed lane must never read as a
lane with everything it needs.

Verified by adding `flipper` to `LANES`, one line, nothing else edited: it was scheduled at
the default cadence, accepted by the API, listed in the money panel with its ring-fence,
and rendered as a complete division card on the dashboard. `tests/test_lane_registry.py`
holds that property by adding a lane that does not exist.

Two things that surfaced only by looking at the page: the REAPER STATUS badge was the
literal string `3 LANES` with an id nothing ever set, and only `.profile small` was
display:block, so connector details ran into their label — "Flippera readiness description
for flipper".

## Review of the two merged PRs, 2026-08-04

PR #1 (cadence + money status) and PR #2 (operator API, dashboard, operational migrations)
were already on `main`. Reviewed against the doctrine above; four things fixed.

**The API published the money view to anyone who could reach it.** `/api/v1/overview`
needed no key and returns the portfolio, every open decision's subject, and each lane's
ring-fence and unsettled exposure — the exact set that is gitignored because this
repository is public — and `backend/__main__` binds every interface by default so
container previews work. A test asserted the open read, so it was deliberate rather than
an oversight. Reads now take the same key as commands, an unset key answers 503 instead of
serving the data, and the key compare is `compare_digest`. `allow_credentials` is off: the
key is a header the caller sets, not a cookie, so it bought nothing and would have been
dangerous beside a wildcard origin. The dashboard names which of the two applies rather
than reporting a running server as offline.

**`status.py` had built its own ring-fence, twice.** `money_panel` and `money_state` each
constructed a `Ringfence` directly and dropped `max_deployed_pct` and
`max_concurrent_positions`, so a lane configured to keep 20% deployed was described
against the default 40, and each built `Breakers` without the outcome ledger that the
deployed-capital control needs to evaluate at all. Nothing visible was wrong yet, because
the panel only reads breaker state off disk — which is what made it worth removing. Both
now go through `lib.reaping.breakers_for`, the same code the lane runs under, which is the
rule `positions.py --apply` already states in its own docstring.

**`OutcomeLedger.stale_open` was the one of four filters that took no lane**, so both
callers wrote the filter themselves and the two copies had already diverged on whether an
empty lane means all or none. It takes `lane` now and the copies are gone.

Checked and sound, for the record: the API cannot route around the operating modes —
`place=true` only permits, and `place_harvest` still refuses anything whose mode is not
`AUTONOMOUS`. `migrations/0002` is fail-closed: RLS on, `operations` revoked from
`anon`/`authenticated`, and the `public.operator_*` views are `security_invoker`, so the
`GRANT ... TO anon` on them cannot actually read the underlying tables.

**The dashboard question that fix opened, and the answer taken.** Putting reads behind the
key left the static dashboard permanently showing its offline layout, since it holds no
key. Resolved with a second secret rather than by reopening the reads: `PROVENA_VIEW_KEY`
grants the two GETs and nothing else, `PROVENA_COMMAND_KEY` runs lanes and is accepted on
reads because it already outranks the view key. The dashboard asks for the view key by
name and keeps it in `sessionStorage`, so it dies with the tab.

The reasoning, because a future session will be tempted to collapse them back into one: a
dashboard has nowhere safe to keep a secret, so live state in a browser means a key in
browser storage. The only question is which key. One key for both would make the
convenient act — paste it into the dashboard — also the act that puts a lane-running
credential one cross-site script away. Two secrets means what an XSS can steal is the
ability to see what `status.py` already prints.

**Two capital defects found by running the dashboard, not by reading it.** Both were
visible the moment the operator API was served against a demo data directory, and both are
the founding defect at the presentation layer.

`as_json` never consulted the portfolio's store state, so a book that had VANISHED —
receipt claiming entries, file holding none — reported `EMPTY_BOOK` with a cost basis of
`0.0`. `capital_panel` returns early on LOST and has always been right about this; the JSON
mirror was not. A vanished ledger reporting FIRST_SEEN is on the list at the top of
`CLAUDE.md`, and this was that, about the portfolio.

The larger one: `capital.cost_basis` was taken from `Exposure.cost_basis`, which sums only
the PRICED subset. No price source is wired for any lane, so it was `0.0` however much was
held — and the dashboard labels that figure CAPITAL AT COST, in the largest type on the
page. A fully stocked book rendered as €0.00 for the same reason an empty one did. What
was paid needs no price source, which is exactly why it is the figure worth showing while
pricing is unwired; the priced subset keeps its own name in `priced_cost_basis`.

`value_status` now separates `NOT_CONFIGURED` (no book has been started) from `EMPTY_BOOK`
(a book exists and holds nothing) from `LOST` / `UNREADABLE`, and `cost_basis` is null for
all four rather than `0.0`.

Noted, not changed:

- `index.html` exists at the repo root and again at `backend/static/index.html`, identical
  but for two asset paths. Two copies of a dashboard will drift; left alone because the
  README documents publishing the root directly to a static host.
- The API's `_run_lock` is per-process, so it serialises reaper runs under one uvicorn
  worker and not across several.
- The bind default stays `0.0.0.0` for the preview case, which is defensible now the
  money data behind it needs a key.

---

# HANDOFF — read this first if you are picking up cold

Written 2026-08-03 against `main` at `47045c5`. **1187 tests, 2 skipped.** Working tree
clean, nothing unpushed. Every gap listed above is closed; what follows is what has not
been started.

## If you are Codex (or anything whose sandbox cannot reach GitHub)

The last run here hit `CONNECT tunnel failed, response 403` on `git push`. Raw pushes from
that environment do not work. **Open a pull request through the GitHub integration
instead** — that path worked, and the branch `codex/request-for-feedback` reached the remote
that way and was merged at `c6c02ce`.

Branch from `main`, never rebase a stranded branch onto a moved `main` on your own: the
conflicts land in `lib/reaping.py`, `run.py` and `lib/outcomes.py`, and those files carry
orderings that look wrong and are load-bearing (see below). Push the branch as it stands and
let whoever holds the context resolve it.

## Three orderings that look backwards and must not be "fixed"

A reviewer or a rebase will be tempted by each of these. All three are deliberate and each
has a test asserting the property.

1. **`lib/placing.py` records the position BEFORE sending the order.** Placing first leaves
   a window where a crash produces a real position nothing in the system knows about.
   Recording first can leave a phantom on rejection, which is visible and fixed in one
   command. Over-reporting exposure is the direction to fail in.
2. **`lib/reaping.apply_outcomes` runs BEFORE any lane looks at anything**, and applies to
   the reaper's OWN `Breakers` object rather than a freshly loaded one. A second instance
   would write the trip to disk and leave the reaper checking the armed in-memory copy —
   tripping and permitting in the same run.
3. **The breakers are the LAST gate, after sizing**, because a breaker needs a number. A
   reaper with no breakers attached cannot reach READY at all.

## What is next: the flipper (function 4 of 7)

Facebook Marketplace / DoneDeal / eBay / Amazon — underpriced items bought and resold.

**It needs a different architecture from the three built lanes, and this is the whole
point.** Arb, stocks and crypto are arithmetic on structured data, and a model in the
decision path there adds nondeterminism where it is least affordable. The flipper's input is
freeform text and photographs, which is the opposite problem.

The pattern that survives contact with money: **a model reads listings and emits STRUCTURED
OUTPUT; deterministic code then decides.** Not agents talking to agents — errors compound
with nothing checking them.

Everything downstream is already built and lane-agnostic: `lib/reaper.py` holds the
sequence, `lib/breakers.py` the limits, `lib/outcomes.py` the return leg, `lib/operating.py`
the mode. A flipper lane supplies five callables (`look`, `screen`, `gates`, `thesis_for`,
`size`) and gets the rest. Read `lib/stocks_reaper.py` as the worked example.

Note: eBay and Amazon have APIs. **Facebook Marketplace and DoneDeal do not.** That is a
real constraint on `look`, not an oversight to engineer around.

Remaining after that: app making, faceless YouTube, Etsy/Craigslist.

## Two function ideas raised and not yet accepted

**Website creation / graphics design** and **copywriting**. Both are a different category
from the seven: they are services sold to clients, so production is the easy half and
finding a customer is the hard half. Both are also the most commoditised AI services that
exist — output quality is not a differentiator.

The version worth building, if either is: **claim-substantiated copy**, where every factual
assertion carries an evidence record and the deliverable includes the audit chain. That aims
at regulated sectors — finance, health, supplements — where an unsubstantiated advertising
claim is a regulator problem rather than a taste problem. It is the one thing the review
board machinery uniquely serves, and `INSUFFICIENT_EVIDENCE` is the selling point: most
tools have no way to say "we looked and this claim is not supported".

Not started. Recorded so the reasoning is not re-derived.

## Open questions — decisions, not tasks

- **No sizing ramp.** A lane with zero settled outcomes sizes identically to one with two
  hundred. Standard practice scales stake with evidence. Ian has been asked for the shape
  and has not specified one; do not invent it.
- **The Obsidian vault.** One-directional, system → markdown files with YAML frontmatter so
  the Dataview plugin renders a live table. Roughly two hours. Writing BACK from Obsidian
  stays out of scope: the ledger needs validation and atomic writes, and a hand-edited
  markdown file has neither.

## Blocked on Ian — not on code

| | what | state |
|---|---|---|
| 1 | **The Odds API key** → `~/.oddsapi/key` | a key was pasted into chat and is burned; must be rotated and placed by hand. The arb lane reports COULD_NOT_LOOK until it exists. Free tier is 500 credits and `reap-arb` runs every 30 min — cut the sports list or lengthen the cadence first. |
| 2 | **Alpaca paper** → `~/.alpaca/{key_id,secret_key,paper}` | the entire stocks lane, including the placing path, has never met a real broker |
| 3 | **A settlement declaration** for the two bookmakers actually used | an evening with their abandonment and non-runner rules. Until then the arb lane correctly stops at INDETERMINATE and prints the exact key it wants. |
| 4 | **QuickNode** | auth token embedded in the URL path, present in several transcripts, **still unrotated** across many sessions. QuickNode's Console API is plan-gated so the connector cannot rotate it. |
| 5 | ~~CourtListener~~ | **not needed.** No connector, no client, no preflight entry — the only references are a docstring and a retry comment. Revoke the token; do not replace it. |

Never accept a credential pasted into chat, and never write one into this repository.

## Where things are

```
README.md               current state, the pipeline diagram, how to run it
CLAUDE.md               the doctrine — read before writing a line
docs/next-work.md       this file
lib/reaper.py           the sequence every lane runs
lib/{arb,stocks,crypto}_reaper.py    the three lanes
lib/breakers.py         ring-fence, position cap, deployed cap, concurrency, kill switch
lib/outcomes.py         what was placed and what came back
lib/operating.py        who is placing — the machine or the owner
lib/placing.py          the only step that cannot be undone
positions.py            record outcomes; --apply feeds the breakers
run.py --reap [lane]    the whole thing
```
