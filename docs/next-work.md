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
