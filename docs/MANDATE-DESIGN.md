# The mandate artifact — design

**Status:** design only. No code yet.

## What it is for

The board produces verdicts. Nothing today converts a verdict into "this action is
permitted." That gap is the whole reason a review board that cost this much to build
currently earns nothing: it answers questions, and no process consumes the answers.

A mandate is the artifact between them. Given a published decision and a proposed action,
it states whether that decision permits that action, and if not, exactly which condition
failed.

## What it is NOT for

It does not size a position, choose a price, pick a venue, or decide when to act. Those
are trading decisions and the board has no competence in them. A mandate answers one
question — *may this action proceed on the strength of this decision?* — and refuses to be
read as advice about anything else.

## The governing principle

**The default is REFUSED, and permission must be positively established.**

This system has met the same defect in a court archive, an unclassified mechanism, an
empty proxy slot, an absent liquidity venue, an unattempted resample and a rounded
percentage: *not found* rendering as *not there*. In a mandate that defect authorises a
trade. A condition that cannot be evaluated must never satisfy itself by being unreadable.

So there is no boolean anywhere in this design.

```
PERMITTED       every condition positively established
REFUSED         at least one condition positively fails
EXPIRED         conditions held, but the decision's validity window has closed
INDETERMINATE   a condition could not be evaluated at all
```

`INDETERMINATE` is not a soft `PERMITTED`. It is the same refusal with a different reason,
and it is reported separately so a caller can tell "the decision says no" from "I could not
tell what the decision says."

## Shape

```python
mandate(decision_package, proposed_action, *, now, observations=()) -> MandateFinding
```

`rbe_runtime/mandate.py`. **Pure — no network, no clock of its own, no connector imports.**
`rbe_runtime` must not depend on `connectors`; the freshness observation (below) is
computed by the caller and passed in. That keeps the whole thing testable without a chain
and keeps the layering honest.

`MandateFinding` carries one `ConditionResult` per condition, each with its own status and
its own reason. `describe()` renders every condition — established, failed and
unevaluatable alike. It never collapses them into a headline, because the reason a mandate
was refused is the entire value of it.

## The conditions

Each is independent. All must be `ESTABLISHED` for `PERMITTED`.

**1 · Outcome permits.** The decision's outcome must be in the profile's permitting set.
`FAIL` never permits. `INSUFFICIENT_EVIDENCE` never permits — that is the sentinel defect
at decision level, and treating "we could not tell" as "go ahead" is the exact failure this
whole repository exists to catch. `PASS_WITH_FINDINGS` permits only where every blocking
finding carries an accepted remediation.

**2 · Authority suffices.** Read `binding` and `single_authority`.

RBM-003 section 11 already settles this for crypto: *"A review under this profile can never,
by itself, authorise a transaction. Authorisation requires a ratified mandate under a
binding profile, which this is not."* So **RBM-003 as it stands can never produce a
permitting mandate.** That is not a limitation to route around — it is the profile being
honest about its own weight, and the mandate must encode it rather than quietly outrank it.

A `single_authority` decision is the weakest authority the system can express. It should
not gate anything that moves money, and the mandate says so by name rather than by
arithmetic.

**3 · Scrutiny is sufficient and recorded.** How were the seat drafts verified, and on what
basis was the decision ratified? `board verify --basis` records the first on the draft
file. The second is currently **not recorded at all** — see Prerequisites.

A decision whose scrutiny level is unknown is `INDETERMINATE`, never `PERMITTED`. An
unrecorded reading is not a full reading.

**4 · The decision is fresh.** Two different clocks, and conflating them would be a
mistake:

- *Wall clock* — `publication.indicator.expires_at`, already 72 hours. Past it: `EXPIRED`.
- *Artefact drift* — the decision is pinned to a block height (`artefact_sha`). A decision
  about block 25,662,176 says progressively less about any later block.

Drift is the interesting one, and for this subject it is sharp. CAA's finding is that USDC
sits behind an upgradeable proxy whose admin can replace the implementation entirely. So
**every fact the board established holds only while that implementation address is
unchanged.** That is cheaply checkable: one `eth_getStorageAt` against the recorded slot,
compared to the implementation CAA recorded.

The caller performs that read and passes a `DriftObservation`. If the implementation
changed, the decision is void regardless of wall clock. If the observation is absent, the
condition is `INDETERMINATE` — not waived.

Wall-clock freshness is a proxy for drift; drift is the thing that actually matters.

**5 · Not superseded.** `decision.superseded` covers the in-session appeal case.

It does not cover the case in front of us. `RBM003-USDC-0002` replaced `RBM003-USDC-0001`,
and **nothing in the store records that** — `parent_session_id` exists in the schema and is
never written, and `supersede_published_decision` is an appeal mechanism requiring
`APPEAL_REVIEW`, not a cross-review link. A mandate reading decision 0001 today would find
`superseded: False` and be wrong.

Until cross-review supersession exists, this condition returns `INDETERMINATE` whenever
another published decision exists for the same subject at a later artefact height. Better
to refuse for a reason than to permit on a field that cannot know.

**6 · Scope matches.** The proposed action must concern the subject the decision reviewed —
matched on the review's `repository` locator (`ethereum:0xA0b8...`), not on a name. A
decision about USDC permits nothing about USDT, and a decision about a contract permits
nothing about a listed pair on an exchange.

**7 · No unresolved blocking findings.** `unresolved_sev1_count` and
`unresolved_sev2_count` from the indicator. Non-zero refuses, and names the findings.

## Worked example — what it would say today

Against `RBM003-USDC-0002`, for any proposed action:

```
REFUSED
  outcome        FAILED       FAIL is not a permitting outcome
  authority      FAILED       RBM-003 is non-binding; §11 forbids authorisation
  scrutiny       INDETERMINATE ratification basis is not recorded in the store
  freshness      INDETERMINATE no drift observation supplied
  supersession   ESTABLISHED  not superseded
  scope          ESTABLISHED  ethereum:0xA0b8...eB48
  findings       FAILED       4 unresolved SEV-2
```

Three independent refusals and two conditions that cannot be evaluated. The right answer,
and the per-condition breakdown is what makes it useful rather than merely negative.

**The first mandate this system produces will refuse.** That is the correct outcome and
worth stating in advance, so it is not read as the artifact being broken.

## Prerequisites — found while designing this

Three gaps that must close before a mandate can mean anything:

1. **Persist the ratification rationale.** `--rationale` is accepted, required by policy
   for single authority, passed into `save_decision`, and dropped: `decision_ratifications`
   has no column for it. A governance control that validates its input and discards it.
   Needs a column, a migration, and the field in the export.

2. **Record the verification basis in the store.** `--basis` writes to the draft JSON, which
   is a file on disk and not part of the decision package. Condition 3 cannot read it.

3. **Cross-review supersession.** `parent_session_id` exists and nothing writes it. Needed
   for condition 5 to return anything but `INDETERMINATE`.

None is large. All three are the difference between a mandate that reasons about evidence
and one that reasons about absences.

## Build order

1. The three prerequisites, each with its migration and test.
2. `MandateFinding`, `ConditionResult` and the seven conditions — pure, table-driven tests.
3. `DriftObservation`, built by a caller in `connectors/`, never imported by the runtime.
4. `board mandate --decision <path> --action <path>` rendering the condition table.
5. Run it against both USDC decisions and record what it says.

## What this unlocks, and what it does not

With a mandate, a bot or a person has one thing to consult before acting, and a refusal
carries its reason. Without it, three lanes of review produce verdicts nobody consumes.

It still does not make RBM-003 an authorising profile. Getting a `PERMITTED` out of this
system requires a binding methodology and two signatures — deliberately, and that is a
separate decision for a human to make with their eyes open.
