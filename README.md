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

Five ship with the repo, and all are real rather than illustrative:

| Profile | Reviews | Artefact is | Specialists |
|---|---|---|---|
| **RBM-001** | research conclusions | a study bundle | SAA BCA DEA QRA SPA POA |
| **RBM-002** | engineering artefacts | a commit hash | GCA MCA EFA ATA SVA RPA |
| **RBM-003** | on-chain assets | a block height | CVA ADA TKA CAA LQA RPA |
| **RBM-004** | listed equities | a set of filings | FVA RIA SDA CRA MLA RPA |
| **RBM-005** | claimed arbitrage positions | a priced instant | PQA MIA EXA ALA CPA RPA |

Five profiles, one engine, no changes to the decision code between them. That's the claim,
and `tests/test_profile_registry.py` is where it's checked — every registered profile loads
in one process and produces a distinct rule set. The test iterates the registry rather than
a hardcoded list, so a sixth is covered the moment it exists.

Adding one is a registry entry in `controlled_authority/profiles.py` plus a package
directory. The runtime states what it expects to find; a package that disagrees fails to
load rather than redefining what it is.

The claim was tested rather than asserted. Adding RBM-004 and RBM-005 broke three things,
all of them RBM-001 assumptions welded into shared code and invisible while there was only
one profile: the runtime stamping its own schema version onto records, the bundle validator
checking any profile against RBM-001's registry entry, and a specialist pool hardcoded to
`{saa, bca, dea, qra, spa, poa}`. Each now reads from the profile.

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

## The crypto gates, and what building them cost

RBM-003's six gates name failure modes in the domain rather than in this repository. But
each one, on the way to being implemented against live chain state, produced a defect here
first — which is the second column:

```text
CG-01  chain-observable         claims read from dashboards rather than regenerable queries
       verification             -> a provider's archive depth was reported from ONE successful
                                   historical query; re-measured across eight heights, 4 of 8

CG-02  address distinctness     addresses funded from one wallet counted as distinct users
       -> DistinctnessFinding carries no holder count, because a cluster-corrected
          census invites being read as one

CG-03  supply and locks         published tokenomics believed over deployed contract
       -> an earlier draft named lockers from memory; a wrong locker address returns zero
          and renders as "no locks found". The registry now ships EMPTY

CG-04  contract authority       "ownership renounced" beside a live proxy admin
       -> empty EIP-1967 slots read as "not a proxy". The pre-1967 zeppelinos slot was
          populated the whole time

CG-05  liquidity reality        TVL reported as though it were exit depth
       -> v2_pair was defined and never called, so V2-only tokens returned NO_VENUE_FOUND
          with real liquidity sitting there. And pooling quotes across V3 fee tiers made a
          larger trade price cheaper than a smaller one

CG-06  reproducibility          a figure nobody else can regenerate
       -> the reading hash included the block TAG, so a value read via `finalized` and the
          same value re-read at that height disagreed. Every resample returned DIVERGED
```

One defect underlies most of that column: a value meaning *not found* or *unknown* read as
*not there*. Empty proxy slot, absent venue, unattempted resample, 0.0049% rounded to
0.00%. Each gate's connector answers with a third state rather than a negative claim —
`NO_PATTERN_MATCHED`, `NO_VENUE_FOUND`, `NO_LOCK_CONTRACT_IDENTIFIED`, `NOT_ATTEMPTED` —
and a test asserts the wording never collapses it into the flattering reading.

## Running it against something real

Three commands, no review ceremony. They produce facts pinned to a source, and no verdict.

```bash
python check_token.py 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48   # six chain gates
python check_stock.py NVDA                                         # filing gates, no API key
python check_arb.py my-arb.json                                    # is a claimed arb real
```

`check_stock.py` needs nothing but a network connection: SEC EDGAR asks only that a client
identify itself. `check_token.py` needs an Ethereum node URL. `check_arb.py` needs neither —
you type in odds from two screens.

Each of these has caught something on live data that reasoning alone did not:

| | |
|---|---|
| **WETH** | no owner, no pause switch, no admin — and the naive read of an empty return is "ownership renounced" |
| **Apple** | one fiscal year's share count filed at 899,213,000, then 899,213, then 6,294,494,000 |
| **NVIDIA** | revenue four years stale because the company changed XBRL tags mid-life |
| **USDC** | upgradeable behind a proxy whose EIP-1967 slots are empty, so the standard check reports it immutable |
| **Betfair vs bet365** | non-runner settlement diverging by 0.15–0.45 in odds, larger than most arb margins |

## From a verdict to an action

`rbe_runtime/mandate.py` is the piece between the board and anything that moves money. Given
a published decision and a proposed action, it reports whether that decision permits it —
eight conditions, each evaluated and reported separately, and no boolean anywhere.

```text
PERMITTED · REFUSED · EXPIRED · INDETERMINATE
```

The default is REFUSED and permission must be positively established, because the recurring
defect in this repository — *not found* rendering as *not there* — would here authorise a
trade. `INDETERMINATE` is reported apart from `REFUSED` so a caller can tell "the decision
says no" from "I cannot tell what it says".

It has never returned `PERMITTED`. RBM-003 section 11 states that a review under it can
never authorise a transaction, so the authority condition refuses every time. That is the
profile being honest about its weight, and the mandate encodes it rather than outranking it.

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
connectors/           the evidence readers: chain, EDGAR filings, exchange odds
guards/               agent output governance
lib/                  arbitrage maths, adjudication standing, retry policy, term matching
docs/rbe-001/         the architecture package
docs/review-board/      RBM-001    research
docs/engineering-board/ RBM-002    engineering
docs/crypto-board/      RBM-003    crypto
docs/stocks-board/      RBM-004    equities
docs/arb-board/         RBM-005    arbitrage
check_token.py        one command, six chain gates
check_stock.py        one command, the filing gates
check_arb.py          is a claimed arb real, from two screens
trade_sheet.py        board verdict, round-trip cost, and your own target
```

`connectors/` is where the evidence comes from and where most of the defects were found.
`chain*.py` read Ethereum over JSON-RPC; `edgar.py` reads SEC filings and needs no API key;
`betfair.py` and `smarkets.py` read exchange prices; `odds.py` holds the interface and, more
importantly, the answer an unconfigured source gives — a scan that reached two books of five
and reports "no arb" is wrong in the way that costs money.

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
