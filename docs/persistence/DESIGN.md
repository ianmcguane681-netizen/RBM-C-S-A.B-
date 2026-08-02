# Moving the store off the container

*Design. Assessment of a proposal, and what changes.*

## The call is right

`data/review_board.sqlite3` dies when this container is reclaimed. It currently holds two
published USDC decisions, two more sitting at `GOVERNANCE_VALIDATION`, 26 evidence
references, 22 findings and a 72-entry audit chain. The exported bundles are committed; the
live store is not, and it cannot be — `*.sqlite3` is gitignored, and committing a binary
database on every write would be worse than losing it.

`data/monitor-ledger.json` and `data/seen-register.json` have the same problem and it bites
harder, because both are built entirely on remembering. A monitor with no memory reports
`FIRST_SEEN` forever and looks like it is working. A seen register with no memory surfaces
its whole backlog as new.

So: yes. Postgres behind Supabase, GitHub stays the source of code, the database becomes the
source of operational state. That is the biggest structural gain available and it is free.

Three amendments.

---

## Amendment 1 — the proposed schema has no board in it

The proposal lists nine tables: `opportunities`, `executions`, `bookmakers`, `markets`,
`prices`, `bankroll_history`, `alerts`, `settings`, `connectors`.

Every one of them is worth having. Together they are a betting bot's schema with an audit
trail bolted on, and they contain no reviews, no findings, no evidence, no decisions, no
ratifications and no audit chain — which is to say, none of the seventeen tables that exist
today and none of the part of this project that is distinctive.

If Supabase becomes "the operational backbone" on that schema, the governance layer stays
in a SQLite file that dies with the container while the betting data lives forever. That is
exactly backwards: the operational data is regenerable by scanning again, and a published
decision with its audit chain is not regenerable at all.

**The review store migrates first. Operational tables are additive on top.**

## Amendment 2 — immutability has to be rebuilt, not assumed

The current store enforces its audit chain with SQLite triggers:

```sql
CREATE TRIGGER review_packages_no_update
BEFORE UPDATE ON review_packages BEGIN SELECT RAISE(ABORT, 'review_packages are immutable'); END;
```

Six tables carry that pair. It is why a published decision cannot be quietly edited, and it
is the entire reason the chain is worth verifying.

Postgres does this better than SQLite — `REVOKE UPDATE, DELETE` on a role is stronger than a
trigger, because a trigger can be dropped by whoever can write. But it only happens if it is
written. Lift the schema across with default grants and every guarantee is gone, silently,
with the data looking identical.

**And there is a new exposure that did not exist before.** A local SQLite file is reachable
by whoever has the container. A Supabase project is reachable by whoever has a key, and this
repository is public. If row-level security is left permissive, or a service key ever
reaches a tracked file, a published decision becomes editable by anyone. A record that can
be rewritten is not an audit chain; it is a document that resembles one, which is worse than
having none because it is trusted.

So the migration carries, explicitly:

- `REVOKE UPDATE, DELETE` on every append-only table, from every role including `anon` and
  `authenticated`
- RLS enabled on every table, denying by default
- writes only through a service role that never appears in the repository
- the `anon` key read-only, and only on the tables a dashboard needs

## Amendment 3 — `settings.thresholds` is where the score comes back

The proposal's `settings` table holds "scan intervals, thresholds, enabled sports".

Intervals and enabled sports are fine. **Thresholds need splitting**, because two different
things are hiding under one word:

- **Limits** — maximum stake, freshness in seconds, risk percentage per asset, minimum
  return over round-trip cost. Each is a single named quantity compared against a single
  named measurement. Keep all of them.
- **A surfacing threshold** — "only opportunities above N get surfaced". This one requires
  something to be scored, and scoring is what `lib/candidates.py` was built two commits ago
  to refuse. A position that is fatally mismatched on settlement and fine on six other
  dimensions clears any sane threshold.

Only limits go in the table. There is no score column and no threshold to compare one
against.

---

## What the proposal gets right that is worth naming

**A `prices` table upgrades the arbitrage reproducibility gate.** AG-06 currently records,
honestly, that prices cannot be re-observed — the market has moved and the venues do not
expose the historical book, so only the arithmetic reproduces. Once snapshots are stored,
that stops being true in the way that matters: the price becomes retrievable evidence with a
venue, a side, a size and a timestamp, exactly like a block height. The SR seat on
`RBM005-WORKED-0001` raised the perishability of prices as a SEV-3; this closes it.

**A `connectors` health table is `preflight.py` promoted to a record.** Right now readiness
is computed on demand and forgotten. Stored, it answers a question nobody can currently ask:
*was that source reachable at the moment that scan ran?* A scan that found no arb because
two books were down is a different fact from one that found no arb.

**An `opportunities` table is `lib/seen.py` done properly.** The JSON register was the right
shape for a file; a table is the right shape for the thing.

**`alerts` is genuinely important and easy to skip.** Every notification sent, recorded. It
is the only way to answer "have I already told them this" across restarts, and it is the
audit trail for a system that will eventually act.

---

## What this is not

The proposal calls the project **RBM-ARB** and models an arbitrage system.

Arbitrage is one of three lanes and the least developed. RBM-003 crypto has two published
decisions; RBM-004 stocks has one at governance validation; RBM-005 arbitrage has one, over
a worked example chosen because it fails. A schema and a control centre built around betting
would fit the smallest third of the project and would have to be rebuilt when the other two
arrived.

The tables are lane-neutral where they can be. `prices` holds a venue, an instrument, a
side, a size and a timestamp whether the instrument is a horse, a share or a token.
`executions` and `bankroll_history` are the same shape for all three. Only `bookmakers` and
`markets` are betting-specific, and they generalise to `venues` and `instruments` at no cost.

## The AI/human boundary must travel with the data

Every report in the store carries `ai_assistance {used, human_verified}` and a
`human_signature_ref` recording *how* the material was read — currently
`standing-authority-2026-08-02-not-individually-read` on twelve of them, which is accurate
and is the weakest admissible basis.

Those columns are not decoration and they are the first thing a schema redesign drops,
because they look like metadata. A schema that stores an agent's output and a human's
decision in the same shape with nothing distinguishing them has thrown away the property
this entire repository exists to hold. They migrate, with their constraints.

---

## Migration order

1. **Review store**, schema derived from the live SQLite rather than hand-copied. Hand-copying
   is how RBM-004 and RBM-005 shipped with `"RBM-003"` welded into their schemas, and the
   fix there was to derive from the profile. Same discipline: `tools/pg_schema.py` reads the
   real schema and emits the DDL.
2. **Immutability and RLS**, in the same migration, never a follow-up. A window in which the
   tables exist and the guards do not is a window in which the chain can be broken.
3. **Move the ledger and the seen register** to tables. Both are small, both are pure gain.
4. **Operational tables** — `venues`, `instruments`, `prices`, `opportunities`, `executions`,
   `bankroll_history`, `alerts`, `settings`, `connector_health`.
5. **Read-only dashboard** last, against the `anon` role, on views rather than tables.

Steps 1 to 3 are the ones that stop losing things. Steps 4 and 5 are the ones that make it
look impressive, and doing them first is how the audit chain ends up still living in a file
that dies.
