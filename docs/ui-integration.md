# The UI contract

Every command that a person reads can also be read by a program. `--json` is a rendering
of the same run, not a different one — same gates, same modes, same exit codes.

```bash
python status.py --json                  the whole system, including the money lanes
python run.py --reap --json              all three lanes; add a lane name for one
python run.py --reap --json --dry        the same, sending nothing whatever the modes say
python positions.py --json               what is open, what is stale, what is unapplied
python positions.py --apply --json       feed settled outcomes to the breakers
python scan_arb.py <sport> --json        one arb scan, with the quota it cost
```

`scan_arb --books skybet,paddypower` narrows the scan to named books at roughly half the
quota, and is how a book list is tried before it goes into `data/reapers.json`. Compare
`books_requested` against `books` in the output: a name in the first and not the second
was asked for and never answered, and that is the difference between a quiet market and a
narrower look than anybody chose.

Every top-level payload carries `schema_version` from `lib/ui_contract.py`. A field added
is a minor bump; a field removed or repurposed is a major one, because a reader written
against the old name has no way to tell a renamed field from a missing one.

## The one rule a front end has to keep

**Do not coerce a null to a zero.** Every module beneath this contract was written to keep
*not found* and *could not look* apart, and a presentation layer is the last place that
care can be thrown away in a single line.

So a monetary field that nobody could establish is `null`, always beside a status that
says why:

| status | means |
|---|---|
| `NOT_CONFIGURED` | nothing was asked of this. It did not look, so it has not found nothing |
| `UNREADABLE` | something was asked and could not be read. An unknown limit is not a satisfied limit |
| `COULD_NOT_LOOK` | it was asked, it ran, and it never reached its source |
| a real `0.0` | measured, and the answer is nought |

An absent outcome ledger reports `NOT_CONFIGURED` with `unsettled_exposure: null` — not
`0.00` at risk. An unmeasured quota reports `{"status": "UNKNOWN", "remaining": null}` —
not `-1`. A position that has not settled reports `returned: null` and `profit: null` —
not a total loss.

## Reading a reap

`status` on the reap payload is the four-way distinction `describe()` makes in prose, and
the last two are the pair worth getting right: `NOT_CONFIGURED` (nothing was asked of any
lane) and `COULD_NOT_LOOK` (lanes ran and every one failed to reach a source). A caller
that treats the second as a quiet market reads a broken pipeline as a quiet market every
morning, indefinitely.

`placements` is a separate list from `harvests` and must be rendered. It is the only part
of the payload behind which money has already moved, and a screen showing READY harvests
with no placement panel says "nothing has been placed" on a run that placed. Within it,
`needs_a_person: true` on an `UNRESOLVED` placement means **the order may exist** — the
one state where treating "not PLACED" as "not placed" submits the same money twice.

`harvests[].seen.status` is `NO_REGISTER` when no seen register was attached, which is
neither `NEW` nor `UNCHECKED`. A lane on a thirty-minute cadence re-offers the same
standing opportunity every run, and novelty nobody looked up is manufactured novelty.

`harvests[].board_convened` is `false` on everything the reapers produce. These are
working decisions, not reviewed ones — the audit chain is what is lost by running the
gates without convening a board, and every harvest says so rather than letting the two be
confused.

## What a UI must not become a route around

These are human acts, and the guards that enforce them are structural rather than
advisory. Each refuses the prefixes `agent:`, `ai:`, `model:`, `automation:`, `bot:` and
`system:`, and putting a form in front of one does not change who is answering it:

- ratifying or publishing a board decision
- declaring settlement equivalence between two books
- authoring a thesis, or holding a standing authority
- re-arming a tripped breaker
- declaring a FORECAST criterion

A UI may collect a named person's input and pass it through. It may not supply the name,
default it to the signed-in session, or offer a control that completes one of these
without one.

Two more that are facts about the world rather than missing features, and should be
presented as such rather than as disabled buttons awaiting work:

- **The arb lane has no order API.** bet365 and Sky Bet do not take an order from a
  program. The bet slip is the deliverable.
- **The chain lane cannot sign.** `connectors/chain_exec.py` has no key path, no signing
  library and no send method. The exact unsigned transaction is the deliverable.

## Writing

The commands above are the write path; a later HTTP service should call the same Python
functions rather than parse their prose or restate their rules. Two implementations of
"is this lane configured" eventually disagree, and the disagreement is invisible.

Exit codes are part of the contract and are identical in both renderings:

```
0   nothing needs a person
1   something is waiting for one
2   nothing was looked at, or a file could not be read
```
