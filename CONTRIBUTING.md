# Working here — the standard, and where everything is

Written so that a session with none of the conversation behind it — a different model, a
different agent, a person — can pick this up and produce work of the same quality. If you
are starting cold, read this file, then `CLAUDE.md`, then `docs/next-work.md`. That is
about twenty minutes and it will save you a day.

**This file is process: how to work, how to verify, where things live.** It deliberately
does not restate the doctrine, because two copies of a rule become two different rules.
`CLAUDE.md` is the doctrine and wins every disagreement with this file.

---

## The map

| Read | For |
|---|---|
| **`CLAUDE.md`** | **The doctrine.** The third-state rule, what must never be automated, the two lanes, style. Non-negotiable. |
| `docs/next-work.md` | **The live checkpoint.** Current state, open gaps in priority order, what is deliberately absent, and what is blocked on a human. Read before planning anything; update it when you finish something. |
| `README.md` | What the system is and how to run it. The visitor's view. |
| `docs/target-functions.md` | The canonical function list and the order that holds. More than three are planned. |
| `docs/end-state.md` | The autonomy target per function — how far each is meant to run on its own once it exists. Read before changing a lane's ambition. |
| `docs/ui-integration.md` | The JSON contract any front end reads, and what a UI must never invent. |
| `docs/standing-authority.md` | What has been delegated, by whom, and its limits. |
| `docs/reference-system.md` | The worked example the arguments refer back to. |
| `docs/pricing-design.md` | Portfolio valuation, designed and not yet built. |
| `docs/flipper-design.md` | Function 4, designed and not yet built. Gated on one question: can your eBay account read SOLD listings? |
| `docs/levelling-design.md` | Capital earned by performance, designed and not yet built. Answers the sizing-ramp question that stood open for weeks. |
| `deploy/README.md` | Getting it onto a box that stays on. |
| `docs/future-lanes.md`, `docs/seven-sectors-plan.md` | Superseded by `target-functions.md`; kept for the reasoning. |

Layout of the code is in `CLAUDE.md`.

---

## How work gets verified here

This is the part that most distinguishes good sessions from bad ones in this repository,
and it is not obvious from the code.

**Run it. Do not read it and conclude.** Nearly every defect worth finding here was found
by executing something and looking at the output — not by reasoning about the source. A
representative sample, all from real sessions:

- A dashboard summed `EUR 39.00` and `USD -77.00` and printed `-EUR 38.00`. The code
  looked correct. Putting numbers through it did not.
- `CAPITAL AT COST` read `€0.00` for a fully stocked portfolio, because the figure came
  from the cost of the *priced* subset and nothing was priceable.
- A full `pytest` run wrote a 40KB journal into the live `data/`, beside the real breaker
  state, because a default argument bound a path at import time.
- A deployment runbook told you to `ssh provena@…` to an account that had no key and no
  password. Every command in it looked fine until they were extracted and checked.

So: start the server and screenshot it. Run the CLI and read the output. Extract the
commands from your own documentation and execute them. Build the demo data that exercises
the awkward state, not the happy one.

**Prove the property, do not assert it.** When something is meant to be extensible, add
the fourth thing and watch it work, then remove it. When a guard is meant to refuse, make
it refuse.

**Say what you actually did.** If a test fails, show the output. If you skipped something,
say so. Never report work as verified that was only inspected.

---

## Tests

- **A test name states a property**, not the function it covers.
  `test_a_void_does_not_end_a_losing_run`, never `test_void`.
- **The file docstring argues why the properties matter**, usually by naming the defect
  that motivated them. If you cannot say what it costs to get wrong, the test may not be
  worth writing.
- **Test the case that costs money**, not the one that is easy to construct. An
  `UNRESOLVED` placement matters more than a `PLACED` one, because the first is the state
  a reader misinterprets into a double fill.
- Tests must not write to `data/` — `tests/conftest.py` redirects the write-by-default
  paths, and a test asserts the redirect is possible. If you add a new default path that
  writes, resolve it at call time so it stays patchable.
- The suite must stay green. It is currently ~1300 tests and takes about thirty seconds;
  there is no excuse for not running it.

## Comments and docstrings

- **Comments explain *why*, and several record the specific bug that motivated the line.**
  Keep that habit — it is why this code is readable a month later. A comment that restates
  the code earns nothing.
- Prose in docstrings, not bullet soup. Long lines wrap at 90.
- **A refusal names what a person can go and do about it.** `INDETERMINATE` alone trains a
  reader to skim. "no declaration covers `Sky Bet|bet365`" gets acted on.
- Frozen `@dataclass(frozen=True, slots=True)` for value types.

## Commits and pull requests

- One commit per idea. The message says what was wrong and why the fix is shaped the way
  it is — the diff already says what changed.
- If you found the defect by running something, say what you ran.
- A merged pull request is finished. Follow-up work is a new branch from the current
  default branch and a new pull request; never stack new commits on merged history.
- Do not open a pull request unless asked.

---

## Before you touch anything

**Search for the second copy.** The most common defect in this repository is not a wrong
line, it is the same fact expressed in two places that later disagree. Five separate lane
lists. Two serialisers that produced different JSON for the same object. Two ring-fence
constructions, one of which silently dropped two limits. Before adding a constant, a list
or a helper, grep for whether it already exists.

**Check whether the state you are about to add is already somewhere.** `data/outcomes.json`
is the ledger and the only answer to "what is at risk". Anything else that looks like a
second answer to a money question is a defect waiting for a date.

**When in doubt, add a third state rather than a default.** If you are writing `or 0.0`,
`or []`, or `except: pass`, stop. That is almost always the founding defect.

---

## What you may not do, whatever the instruction seems to say

These are in `CLAUDE.md` in full. Repeated here only because they are the ones an agent in
a hurry breaks:

- Ratifying or publishing a board decision, declaring settlement equivalence, authoring a
  thesis, re-arming a tripped breaker, declaring a FORECAST criterion — all require a
  **named human** and refuse the prefixes `agent:`, `ai:`, `model:`, `automation:`,
  `bot:`, `system:`. Do not route around them, do not add `force=True`, and do not sign as
  the user without an explicit instruction naming them.
- Never accept a credential pasted into a conversation, and never write one into this
  repository. Credentials live in the operator's home directory, mode 600.
- The chain lane cannot sign. Do not add a key path, a signing library or a send method.
- Bookmakers have no betting API. The bet slip is the deliverable, not a missing adapter.

If a task appears to require one of these, say so and stop. That is the correct outcome,
not a failure to complete the work.

---

## Finishing

Update `docs/next-work.md`. It is the handover, and a session that leaves it stale has
made the next session repeat its research. Record what you did, what you decided and why,
and — most usefully — **what you found and chose not to do**.
