# UI integration contract

The UI is a presentation and command surface over existing decisions. It does not reproduce
the gates, infer missing money, author authority, reset breakers, or turn an unavailable
execution path into a button that looks enabled.

## Read contracts

```bash
python status.py --json
python run.py --reap arb --json
python run.py --reap stocks --json
python run.py --reap crypto --json
python positions.py --json
```

Every top-level response carries `schema_version`. `NOT_CONFIGURED`, `UNREADABLE`, and a
real zero remain different values. Monetary fields that do not exist are `null` beside an
explicit status; the UI must not coerce them to zero.

`status.py --json` is the initial snapshot. Its `functions` collection drives navigation,
rather than three hard-coded cards, so new operating functions can be registered without
changing the dashboard shape. `money_lanes` remains the live capital and breaker view for
functions that control money.

## Write contracts

The initial UI may invoke the existing commands locally. A later HTTP service should call
the same Python functions rather than parse their prose or duplicate their rules.

```bash
python positions.py --placed arb "subject" --staked 20 --json
python positions.py --settle POS-id --returned 22 --json
python positions.py --void POS-id --note "both books voided" --json
python positions.py --unknown POS-id --note "account result unavailable" --json
python positions.py --apply --json
```

Human-only acts remain human-only through a UI. In particular, settlement declarations,
thesis authorship, breaker reset, and handing autonomous placement back require the same
named-person inputs and structural guards as their command-line equivalents.

## Execution truth by function

| function | reaper | execution exposed to UI |
|---|---|---|
| arb | available | exact human bet slip; ordinary bookmakers have no supported API |
| stocks | available | Alpaca adapter exists; READY-to-Instruction bridge remains unwired |
| crypto | available | exact unsigned transaction; no signing or send path |
| SRE | reserved | research only; no active testing until authorised scope exists |

The stocks limitation is intentionally visible as `ALPACA_ADAPTER_UNWIRED`. The UI must not
show an enabled placement control until the bridge records successful, rejected, partial,
and unknown paper orders in the outcome ledger.

The SRE slot reserves the next function without pretending it is built. Before active
security testing, a person must record the authorised targets, excluded assets, rate limits,
safe-harbour terms, disclosure channel, and bounty programme rules. Passive programme and
scope discovery can then be added first; scanning comes only after scope enforcement exists.
