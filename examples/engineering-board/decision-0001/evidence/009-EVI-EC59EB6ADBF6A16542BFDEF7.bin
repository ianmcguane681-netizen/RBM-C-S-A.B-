# GS-CF001

Golden Study - Consumer Finance 001.

This repository is a research proof system for Provena, an Evidence Operating System powered by AI.

It is not a product, dashboard, demo, or analytics app. The Evidence OS is the system of record. AI may assist analysis later, but evidence and deterministic Proof Gates remain the decision authority.

## Research Question

> Is there enough verified, repeated operational pain in U.S. consumer financial account servicing and complaint resolution to justify building one or more reusable workflow components?

## Initial Scope

Only `GS-CF001-C Credit Reporting Disputes` is implemented.

The remaining studies are definitions only:

- `GS-CF001-A` Mortgage Servicing
- `GS-CF001-B` Bank Account Servicing
- `GS-CF001-D` Debt Collection Communication
- `GS-CF001-E` Consumer Loan Servicing
- `GS-CF001-F` Payment & Transaction Disputes

## Methodology

CFPB complaint records are discovery material only. A complaint never automatically becomes a finding or opportunity.

Pipeline:

```text
Discovery
-> Source Record
-> Normalisation
-> Evidence Candidate
-> Verification within source
-> CFPB-limited Finding
-> Opportunity Assessment
-> Proof Gates
-> Verdict
```

Every stage must preserve traceability. If a stage cannot justify itself with evidence, the study reports why and stops short of a positive conclusion.

## Evidence Authority

Governing rule:

```text
AI may propose.
Evidence must prove.
Proof Gates must decide.
```

AI outputs, if introduced later, must be stored as analysis artifacts. They are never source evidence and cannot override deterministic gates.

## Evidence Ceiling

CFPB data alone can produce CFPB-supported, CFPB-limited findings.

CFPB data alone can never produce `BUILD CANDIDATE`.

Deterministic ceiling:

```text
IF independent source family count < 2
THEN maximum verdict = CONTINUE RESEARCH
```

Multiple CFPB complaint records remain one source family.

## Current Sources

Two independent source families are integrated:

- CFPB Consumer Complaint Database — `CFPB complaints`
- CourtListener federal court records (RECAP) — `Federal court records`

The CFPB connector separates the CFPB source from access methods:

- Official CFPB Search API adapter
- Official CFPB bulk download adapter
- Local official CFPB snapshot adapter

No scraping and no third-party mirrors are used.

### Federal court records

Federal dockets are a genuinely separate source family: different parties, a
different forum, and legal consequences attached. Admission is deterministic on
the statutory cause recorded by the court itself — a docket is mapped to this
study only where the claim arises under the Fair Credit Reporting Act
(15 U.S.C. 1681), never by keyword matching a case caption.

The evidential limits are deliberately narrow:

```text
A filed complaint is an allegation, not a finding of fact.
A settlement or dismissal is not an admission of liability.
```

Dockets therefore corroborate that an alleged mechanism recurs outside the CFPB,
and satisfy the independence requirement. They do not establish that any alleged
failure occurred. Docket metadata carries no consumer narrative, and a case
caption is never mined as though it were a first-hand account.

With both families present the deterministic evidence ceiling lifts:

```text
independent source family count >= 2
=> maximum verdict is no longer capped at CONTINUE RESEARCH
```

The verdict itself remains gated on the remaining proof gates, which continue to
require solution-maturity, commercial and counter-evidence research that is not
yet integrated.

## Evidentiary Standing

Independence and proof are separate questions, and the study tracks them on
separate axes:

```text
source family        does this share an origin with evidence already held?
evidentiary standing is this an allegation, or has a forum decided it?
```

Adding forums moves the first axis. Only a decision moves the second. Ten
independent complaint databases would still be ten allegations.

`core/adjudication.py` holds the rule. A record reaches `ADJUDICATED` standing
only when a forum resolved the merits, and it establishes occurrence only when
that resolution went against the respondent. Everything the classifier cannot
resolve from explicit structured values is `UNDETERMINED`, which never establishes
occurrence — because posture is routinely misread:

```text
denying a motion to dismiss   -> the court ASSUMED the allegations were true
denying summary judgment      -> the facts are genuinely DISPUTED
"affirmed" on appeal          -> relative to a judgment below; no direction alone
a settlement                  -> not an admission
```

`PG-09` (Independent Corroboration) requires an adjudicated finding of occurrence
on a mechanism *another* source family independently alleges. `PG-13`
(Counter-Evidence) requires a disposition that went the other way — complaints and
filings are submitted by claimants, so neither can ever produce counter-evidence,
and a source that can only confirm the hypothesis is not a test of it.

Both gates were previously pinned to `FAIL`.

### The adjudicated source

`connectors/fjc_idb.py` reads the Federal Judicial Center's Integrated Database —
the judiciary's own statistical record of every federal civil case. It codes what
opinion prose does not:

```text
disposition   how the case ended   (consent, verdict, settled, default, ...)
judgment      who it went for      (1 plaintiff, 2 defendant, 3 both, 4 unknown)
```

Admission is statutory and deterministic, matching the RECAP connector: the FJC
records the statute as title and section, so FCRA is title 15, section 1681.

Of 17,204 FCRA cases, 67 establish occurrence and 3 contradict it. The exclusions
matter more than the inclusions:

```text
7,683 settled          a settlement is not an admission
   32 default          a forfeiture, not a weighed finding
  363 pre-trial win    for the defendant, one code covers both Rule 12(b)(6)
                       and Rule 56 — not separable, so it proves nothing
```

The IDB is deliberately **not** a new source family. These are the same courts
RECAP already covers, so it raises standing without touching the independent family
count — counting it as a third forum would double-count one dispute.

Requires `COURTLISTENER_API_TOKEN`. Without it the connector emits an access
diagnostic rather than an empty result, so an unconfigured environment never looks
like an absence of adjudications.

```bash
python -m core.pipeline --sources cfpb,court,fjc --limit 8
```

See `analysis/source_evaluation_adjudicated_findings.md` for the four sources that
were probed and rejected, and for the false PASS the first live three-source run
produced before the unclassified-mechanism guard was added.

## What This Study Currently Claims

Stated plainly, because the difference matters and is easy to blur:

```text
CLAIMED     The mechanism is ALLEGED across two independent source families,
            and ADJUDICATED against a respondent in one case.

NOT CLAIMED  That the mechanism occurs market-wide.
```

`PG-09` requires adjudicated corroboration spanning at least three distinct federal
districts before the stronger claim is available. That bar comes from the
remediation plan accepted in review `RBE-GSCF001-0007`, after the board's sceptical
seat refused to let a single California judgment carry a market-wide operational
claim. It is enforced as `CORROBORATING_DISTRICTS_REQUIRED` in
`proof_gates/evaluator.py`, not merely written down here — the finding that started
this whole thread was a requirement that existed only as prose.

Current position: **one district**. A full sweep of all 67 occurrence-establishing
FCRA cases found exactly one reaching the study's mechanism, because RECAP holds a
complaint for 1 in 67. PG-09 reports `WEAK` with the shortfall named rather than a
bare failure.

The adjudicated sample is **archive-selected**: which cases are reachable depends on
who chose to upload documents to RECAP, not on which cases were decided. That
limitation is recorded in the FJC source reliability assessment and travels into
every report and proof bundle, because it cannot be corrected by further retrieval.

## Incumbent Pricing

`market/pricing.py` answers what vendors *charge*, which is a different question
from what buyers *pay*:

```text
what does a vendor charge?   published, retrievable, documentary
what does a buyer pay?       negotiated, discounted, only obtainable from a person
```

Those differ by a factor of two or more once discount, implementation and staff
time are counted, so this lane links to `G7_COMPETITIVE_VIABILITY` and
`C8_MARKET_COMPETITION` only. It is structurally barred from the buyer gates.

What it refuses to do is the point. Five vendors were probed on 2026-07-27. All
five publish pricing, and **none** carries structured pricing markup. One page
alone held twenty distinct dollar amounts:

```text
$1        trial
$179      monthly plan
$143.20   annual-discounted equivalent
$15,427   marketing earnings claim
```

No rule separates those, so the connector records that pricing is published, hashes
the page, and refuses to say what the price is. A figure enters only from
schema.org markup or from a human who read the page and transcribed it against the
recorded hash.

```bash
python -m market.pricing_cli observe
python -m market.pricing_cli transcribe --vendor "..." --price 179.00 --unit "USD/month" --by you
python -m market.pricing_cli status --export data/exports/market_competitors.json
```

Whether a vendor publishes at all is itself market information: it separates a
self-serve market from an enterprise-negotiated one without anyone naming a figure.

Pricing URLs are confirmed against each vendor's own sitemap rather than guessed.
The first version assumed `/pricing` for everyone and reported "three of five
publish" — which was really "three of five use the path I guessed". ScoreCEO
publishes at `/plans`, DisputeSuite at `/how-to-buy-pricing/`. A URL that a
vendor's sitemap does not declare is recorded as unconfirmed.

`PG-11` and `PG-12` were pinned `FAIL` constants and now compute. PG-11 separates
identification from assessment, exactly as G7 does: naming an incumbent is not
assessing one, so a pricing observation alone leaves it `WEAK`. PG-12 reads buyer
evidence and ignores pricing entirely, because a list price shows a market exists
and never that anyone would switch. Both arrive through their own parameters, so
neither can reach the independent source family count or lift the evidence
ceiling.

## Market and Competition Lane

`market/` answers a different question from the study: who already operates in
this market, at what scale, and where is their primary disclosure. It exists to
feed competitive and economic assessment (SV Engine `C8_MARKET_COMPETITION`,
`G7_COMPETITIVE_VIABILITY`), not to prove that consumer harm occurred.

It is sealed off from the evidence study by construction:

```text
MarketEvidence is not VerifiedEvidence.
It carries no source_family, so it can never reach the proof gates
or the independent source family count.
```

Every record is classed `E5_COMPETITIVE_MARKET` and carries
`counts_toward_source_independence: false` explicitly, so the constraint is
legible in the artifact and not only in the code that produced it.

Current source: SEC EDGAR submissions and XBRL company facts. Registrants are
verified against the SIC code they file under rather than an assumption about who
they are — a CIK that turns out not to be a credit reporting agency is reported as
such. Annual figures are filtered by period length, because a 10-K also carries
quarterly breakdowns, and restatements of the same period collapse to the most
recently filed value.

EDGAR full-text search was evaluated and rejected: a phrase search for
"Fair Credit Reporting Act" across 10-K filings returns thousands of unrelated
registrants, so it cannot support a deterministic admission rule.

Experian is absent by necessity — it is LSE-listed and does not file with the SEC,
so no EDGAR evidence exists for it.

## Reports and Artifacts

Each run writes file artifacts only:

- Raw source records or access failure diagnostics
- Source reliability assessment
- Normalised evidence candidates
- Verification artifacts
- Findings
- Opportunity assessments
- Proof Gate results
- Audit trail / evidence state transitions
- Markdown report
- JSON report
- Run manifest with checksums

Reports must be traceable to structured artifacts and methodology rules.

## Run Tests

```powershell
python -m pytest -q
```

## Run Credit Reporting Proof

```powershell
python -m core.pipeline --limit 3
```

The run writes raw, processed, and report artifacts under `data/`.

If CFPB access is blocked by the execution environment, the run writes an access diagnostic and stops short of normalisation instead of creating placeholder evidence.
