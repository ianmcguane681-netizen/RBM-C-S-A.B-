# evidence-board

A review board engine. You give it an artefact, a methodology profile, and a set of
reviewer seats; it runs a governed review and returns a decision that can be audited
afterwards by someone who wasn't there.

It is not an AI assistant, a scoring model, or a recommendation engine. Its defining
property is that **it refuses to conclude more than the evidence carries**, and the
refusal is structural rather than a matter of prompting.

```text
AI may propose.
Evidence must prove.
Deterministic rules must decide.
```

## What it actually does

```text
convene  →  register evidence  →  lock it  →  independent review
         →  challenge  →  consolidate  →  decide  →  ratify  →  publish
```

Every transition is checked against a state machine, every artefact is hashed, and the
audit chain is verifiable after the fact. A review that skipped a step reports
`PROCEDURALLY_INCOMPLETE` and produces no outcome at all — not a weaker outcome.

Outcomes are fixed by the architecture and a profile cannot change them:

```text
PASS · PASS_WITH_FINDINGS · FAIL · INSUFFICIENT_EVIDENCE
```

`INSUFFICIENT_EVIDENCE` is the one that matters. Most review tools have no way to say
"we looked and we still don't know", so they say something else instead.

## Methodology profiles

A profile declares the seats, the specialist pool, the gate list, and what evidence is
admissible. It cannot declare its own outcome vocabulary, lifecycle, or decision
precedence — a profile that could redefine `FAIL` would be marking its own homework.

Two ship with the repo, and both are real rather than illustrative:

| Profile | Reviews | Specialists |
|---|---|---|
| **RBM-001** | research conclusions, where evidence is scarce and curated by others | SAA BCA DEA QRA SPA POA |
| **RBM-002** | engineering artefacts at a named commit, where evidence is cheap | GCA MCA EFA ATA SVA RPA |
| **RBM-003** | on-chain assets and the claims made about them, at a named block height | CVA ADA TKA CAA LQA RPA |

Three profiles, one engine, no changes to the decision code between them. That's the
claim, and `tests/test_profile_registry.py` is where it's checked — every registered
profile loads in one process and produces a distinct rule set. The test iterates the
registry rather than a hardcoded list, so a fourth is covered the moment it exists.

Adding a third is a registry entry in `controlled_authority/profiles.py` plus a package
directory. The runtime states what it expects to find; a package that disagrees fails to
load rather than redefining what it is.

## The engineering gates, and where they came from

RBM-002's six gates are not a checklist. Every one is a defect **this codebase produced
and shipped**, which is the only reason to trust the list:

```text
EG-01  gate computation          four proof gates returned FAIL as a hardcoded literal
EG-02  measurement completeness  a summary written over zero retrieved records
EG-03  enforcement fidelity      a three-district threshold documented, enforced nowhere
EG-04  attestation integrity     a demo run recorded a human as having checked its own output
EG-05  sentinel handling         two unclassified records matched each other, producing a PASS
EG-06  reproducibility           test counts quoted from memory rather than from a run
```

EG-02 has recurred more than any other, and its output is indistinguishable from a
correct result. If you read one thing here, read that gate.

## Agent seats

Seats may be held by agents. They are advisory, always:

- an agent may **review**; it may never ratify or publish
- an AI-assisted report is an **unsigned draft** until a named human verifies it
- `board verify --by <name>` is a separate command run by that person, and it refuses
  every automation prefix — `agent:`, `ai:`, `model:`, `automation:`
- a refused verification leaves the draft unverified rather than writing anyway
- seats sharing a model are **recorded as sharing a model**, because two seats on one
  model are correlated reviewers and a board that didn't say so would be reporting more
  independence than it had

That last set exists because the separation was broken here once: a demonstration run
recorded a named human as having transcribed a value the automation itself had read, and
committed it. The guard and the violation were authored minutes apart, by the same
author. Hence a command, not a field.

## Quick start

```bash
pip install -r requirements.txt
python -m pytest -q

python -m board.cli --profile RBM-002 seats --seats examples/engineering-board/seats.json
python -m board.cli --profile RBM-002 open --initiation examples/engineering-board/initiation.json
python -m board.cli --profile RBM-002 commit-evidence --review <id> \
    --repo /path/to/repo --commit <sha> --path src/thing.py --actor you
python -m board.cli --profile RBM-002 verify --report examples/engineering-board/report-MCA.json --by you
```

`board status --review <id>` will always tell you what it's waiting on.

## Layout

```text
rbe_runtime/          lifecycle, decision engine, repository, validation
controlled_authority/ controlled-package validation and the profile registry
board/                CLI front door, agent seats, challenge sheets
guards/               agent output governance
lib/                  adjudication standing, retry policy, domain packs, term matching
docs/rbe-001/         the architecture package
docs/review-board/    RBM-001
docs/engineering-board/ RBM-002
docs/crypto-board/    RBM-003
```

`lib/adjudication.py` is worth knowing about independently. It separates two axes that
are constantly conflated: **how many independent sources allege this**, and **has any
forum actually decided it**. Adding sources moves the first. Only a decision moves the
second. Ten independent databases of allegations are still ten allegations.

## Provenance, stated plainly

This was extracted from a consumer-finance research study that ran three full board
reviews under RBM-001 and returned **CONTINUE RESEARCH** every time — the machinery
refused to let the study claim more than it had shown.

That's the strongest thing anyone can say about a governance tool: its own first verdict
was "not proven", and it held. The study is archived; the engine is here.

## Licence

Not yet chosen.
