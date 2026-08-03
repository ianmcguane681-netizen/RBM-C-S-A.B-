# Working in this repository

Read this first. It is the accumulated doctrine, and most of it was learned by getting
something wrong in a way that cost time or would have cost money.

## The one idea everything else follows from

**A value meaning *not found* or *unknown* must never render as *not there*.**

That single defect has appeared here in at least ten places: an EDGAR 404 from the wrong
taxonomy printing as "this company does not report a share count"; an empty portfolio book
emitting `0.0`; a vanished ledger reporting FIRST_SEEN; a timed-out order submit; a scan
that reached two books of five reporting "no arb"; a breaker reading an unsettled position
as zero profit.

So **every module has a third state**, and the naming is deliberate:

```
NOTHING_FOUND   vs  COULD_NOT_LOOK
PRICED          vs  UNPRICED  vs  STALE
FRESH / INTACT  vs  LOST      vs  UNREADABLE
SETTLED         vs  OPEN      vs  VOID  vs  UNKNOWN
PASSED          vs  REFUSED   vs  INDETERMINATE
```

When in doubt, add a third state rather than pick a default. If you find yourself writing
`or 0.0`, `or []`, or `except: pass`, stop — that is almost always this bug.

**Corollary: fail toward stopping.** An unreadable limit is not a satisfied limit. An
unknown outcome is not a zero. Where an error could go either way, choose the direction
that halts trading rather than the one that continues it.

## What must never be automated

Some judgements are a named human's, and the guard is structural rather than advisory.
Every one of these refuses the prefixes `agent:`, `ai:`, `model:`, `automation:`, `bot:`,
`system:`:

- **ratifying or publishing** a board decision (`board verify --by <name>`)
- **declaring settlement equivalence** between two books (`lib/arb.EquivalenceDeclaration`)
- **authoring a thesis** or holding a standing authority (`lib/thesis`, `lib/arb_reaper`)
- **re-arming a tripped breaker** (`lib/breakers.reset`)
- **declaring a FORECAST criterion** (`lib/stocks_reaper.Criterion`)

Do not route around these, do not add a `force=True`, and do not sign or attest as the user
without an explicit instruction naming them. If a task seems to require it, say so instead.

## Style

- **Comments explain *why*.** Several record the specific bug that motivated the line — keep
  that habit; it is why the code is readable a month later.
- **Test names state a property**, and the file docstring argues why the property matters.
  `test_a_void_does_not_end_a_losing_run`, not `test_void`.
- **A refusal names what a person can go and do about it.** "INDETERMINATE" alone trains a
  reader to skim; "no declaration covers `Sky Bet|bet365`" gets acted on.
- Prose in docstrings, not bullet soup. Long lines wrap at 90.
- Frozen `@dataclass(frozen=True, slots=True)` for value types.

## Layout

```
rbe_runtime/  board/  controlled_authority/   the review board engine (the original project)
connectors/   evidence readers: chain, EDGAR, odds, Alpaca, and the two execution adapters
lib/          the money side: reapers, breakers, sizing, thesis, outcomes, arb maths
docs/         methodology profiles RBM-001..005, and docs/next-work.md
```

**`docs/next-work.md` is the live checkpoint** — current state, the open gaps in priority
order, and what is deliberately absent. Read it before planning anything.

## Commands

```bash
python -m pytest -q          # must stay green; ~1000 tests
python run.py --reap         # all three lanes, to a sized instruction and no further
python run.py                # the orchestrator: what is due, what is held
python preflight.py          # what each lane needs before it can read anything
```

## Two lanes of work, one repo

The **review board** convenes seats, locks evidence, and publishes auditable decisions. It
can veto and can never authorise.

The **reapers** (`lib/*_reaper.py`) run the same gates without convening a board, for one
person spending their own money. They stop at `READY` — a sized, permitted instruction —
and place nothing. The audit chain is what is lost, and every harvest says so rather than
letting a working decision be mistaken for a reviewed one.

**The chain lane cannot sign, and that is not a setting.** `connectors/chain_exec.py` has no
key path, no signing library and no send method. Do not add one.

**Bookmakers have no betting API.** bet365 and Sky Bet will not take an order from a program.
The bet slip *is* the deliverable — this is not a missing adapter.

## Secrets

`data/*.json` holding subjects, stakes or watchlists is gitignored **because this repository
is public**: the seen register, the outcome ledger, the reaper config, the portfolio. The
`.receipt.json` files beside them are committed — they carry counts and dates, never
subjects. Credentials live in `~/.oddsapi/`, `~/.alpaca/`, `~/.betfair/`, mode 600. Never
put one in a file in this repo, and never ask the user to paste one into chat.

## Standing authority

Ian McGuane granted standing authority for engineering decisions on 2026-08-02, and
separately authorised board ratifications (each ratification rationale records that seats
and signature were not independent). He has approved autonomous decision-making for the
money lanes since the system is deployed in-house rather than sold. `autonomous_execution`
still defaults to `False`, and the chain lane refuses it outright.

Make routine calls yourself and say what you decided. Raise a concern once if you have one,
then build the thing as asked.
