# Engineering Review Board (RBM-002)

The second methodology profile to run on the RBE-001 architecture. RBM-001 governs
research conclusions; this one governs the code that produces them.

## Why it is separate

RBM-001's hardest constraint is that its evidence is curated by someone else. A federal
court archive holds a complaint for about one case in sixty-seven, and no amount of
diligence changes the number. Its gates are therefore mostly about restraint.

Engineering has no analogue. Tests pass or fail, a commit hash is a fact, builds
reproduce. Better evidence permits sharper gates, and a profile written for scarce
evidence would waste that.

## The six gates

Each one is a defect class this system actually produced. That provenance is the reason
to trust the list — every one of them shipped, and every one read as correct until
something forced a second look.

```
EG-01  gate computation         a status that cannot change is not a gate
EG-02  measurement completeness no summary over an unenumerated denominator
EG-03  enforcement fidelity     a requirement in prose enforces nothing
EG-04  attestation integrity    nobody attests to their own output
EG-05  sentinel handling        "unknown" is not a value
EG-06  reproducibility          quoted results are claims, not measurements
```

EG-02 is the one to watch. It has recurred more than any other, and its output is
indistinguishable from a correct result.

## Board

`BC` chair (human, always), `MA` methodology, six specialists — `GCA` `MCA` `EFA` `ATA`
`SVA` `RPA` — and `SR` sceptical, blind to the proposed outcome.

Agent seats are permitted for everything except the chair, and are advisory: an agent
may review and may never ratify or publish.

## Status

RELEASE CANDIDATE. Non-binding, no human approval record, cannot permit a merge. Every
decision produced under it is advisory and recorded as such until the activation
requirements in `PROFILE.json` are met.

## Files

```
PROFILE.json                        identity, quorum, gates, decision precedence
MANIFEST.json                       hashes of every controlled file
ENGINEERING-REVIEW-METHODOLOGY.md   the methodology
specs/RBS-001..008                  one reviewer specification per seat
schemas/tpl-*.schema.json           record templates at v1.0.0
```

The profile is registered in `controlled_authority/profiles.py`. The runtime knows it
by that entry and not by finding this directory — a package cannot declare its own
identity, or it would always agree with itself.

## Running a review under it

```bash
python -m board.cli initiate --profile RBM-002 ...
```

The lifecycle, outcome vocabulary, severity scale and decision precedence are RBE-001's
and are shared with RBM-001 unchanged, so a decision means the same thing under either.
