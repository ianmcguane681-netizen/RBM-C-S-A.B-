# RBE-001 Review Report

> **ADVISORY DRY RUN:** RBM-001 is RELEASE_CANDIDATE. This report is non-binding and does not permit merge.

## Decision Summary

- Review: `RBM005-WORKED-0001`
- Process status: **READY**
- Machine outcome: **FAIL**
- Binding: **false**
- Merge permitted: **false**
- Decision candidate: `DCA-168F4251839F5C9FB7F9CF47`
- Frozen snapshot: `sha256:2c57cdfb38204110cc0ff61fe28f78713a9cdab3194e2e939b2b8536c36647ad`

The machine outcome is deterministic but is not itself governance authority.

## Target And Authority

- Target repository: `typed from source screens`
- Target artefact: `odds:worked-example:2026-08-02T12:00:00Z`
- Architecture authority: RBE-001 v1.1.0
- Methodology: `RBM-005` v1.0.0
- Methodology status: **RELEASE_CANDIDATE**
- Profile checksum: `sha256:3484f3e9daf0b71d53ce684f37c0eae64e82ccc3fc20ac641440c703f8886857`

## Decision Basis

FAIL was selected by RBM-DEC-001 from the frozen finding counts and substantive-evidence assessment.

Rules applied: `RBM-DEC-001`

Reason codes: `RBM-DEC-001`

## Evidence Register

### `EVI-1B44C833051E7AA63FA7B1EA`

- Locator: `odds:Match Odds: Team A v Team B (worked example, not live prices):ag01:leg1`
- SHA-256: `sha256:edec187ff50053e77f6c1d64e0a7978ba07084863903d8f7c45be5b306d100e6`
- Source tier: `T1`
- Description: ag01:leg1 for Match Odds: Team A v Team B (worked example, not live prices)

### `EVI-1D2C4C0B7D0BAD4876621262`

- Locator: `odds:Match Odds: Team A v Team B (worked example, not live prices):ag01:leg0`
- SHA-256: `sha256:6c5b4189c40962cc6722ede768d517dfd1d2d58c26122826f01d312b06211cb2`
- Source tier: `T1`
- Description: ag01:leg0 for Match Odds: Team A v Team B (worked example, not live prices)

### `EVI-1FAAEB84ABB73E5D458AE823`

- Locator: `odds:Match Odds: Team A v Team B (worked example, not live prices):ag04:evaluation`
- SHA-256: `sha256:383b3bcc65bb3a1f67de32754c8bb1cd24fa136f9012ff08a0db63d7a6d58d09`
- Source tier: `T1`
- Description: ag04:evaluation for Match Odds: Team A v Team B (worked example, not live prices)

### `EVI-2758038F3238C724C49AC2DE`

- Locator: `odds:Match Odds: Team A v Team B (worked example, not live prices):ag03:observation_window`
- SHA-256: `sha256:e1038eff8bc629d064060c423c8bec701fd7369c1c802ab217b27bb0cd531e93`
- Source tier: `T1`
- Description: ag03:observation_window for Match Odds: Team A v Team B (worked example, not live prices)

### `EVI-42A4FD1E577FF694FFC79325`

- Locator: `odds:Match Odds: Team A v Team B (worked example, not live prices):ag06:reproduction`
- SHA-256: `sha256:1a67089924b65792979e9d4b36de69ef411e6242d0587e4e66180313b864737c`
- Source tier: `T2`
- Description: ag06:reproduction for Match Odds: Team A v Team B (worked example, not live prices)

### `EVI-434D3F278AC6365A23539259`

- Locator: `odds:Match Odds: Team A v Team B (worked example, not live prices):ag02:rules0`
- SHA-256: `sha256:bc86df5cbfceff9471407d30ca8aa0fc72694f2b94d363237b694245e07f46b1`
- Source tier: `T1`
- Description: ag02:rules0 for Match Odds: Team A v Team B (worked example, not live prices)

### `EVI-C217E3FBBFEDD80B9E316913`

- Locator: `odds:Match Odds: Team A v Team B (worked example, not live prices):ag02:rules1`
- SHA-256: `sha256:9e53775b1da750b9b059c9c2e17af052eeb17155691d92b7279499b57a70c5cc`
- Source tier: `T1`
- Description: ag02:rules1 for Match Odds: Team A v Team B (worked example, not live prices)

### `EVI-DF7E0E0BEC9315A00C43029C`

- Locator: `odds:Match Odds: Team A v Team B (worked example, not live prices):ag05:coverage`
- SHA-256: `sha256:926209ebac74d7cac86250ac14fa2e261cdc27ec17f3efbbfd945296521ffa8e`
- Source tier: `T1`
- Description: ag05:coverage for Match Odds: Team A v Team B (worked example, not live prices)

## Reviewer Reports

### `RPT-RBM005-WORKED-0001-ALA`

- Assignment: `ASN-AEF2313F7124D4471D1CD23B`
- Summary: At these prices the combined implied probability is under 100%, and that is not sufficient. The maths returns SETTLEMENT_MISMATCH before it returns a stake split.
- Non-binding recommendation: **No-build / stop**
- Evidence references: `EVI-1FAAEB84ABB73E5D458AE823`, `EVI-2758038F3238C724C49AC2DE`
- Human signature: `SIG-VERIFY-ALA-Ian McGuane-BASIS-standing-authority-2026-08-02-not-individually-read`

### `RPT-RBM005-WORKED-0001-CPA`

- Assignment: `ASN-636FCC7A03974985450CD295`
- Summary: No source answered. The scan reached nought of five books, so nothing here establishes that these were the best available prices.
- Non-binding recommendation: **Corrective**
- Evidence references: `EVI-DF7E0E0BEC9315A00C43029C`
- Human signature: `SIG-VERIFY-CPA-Ian McGuane-BASIS-standing-authority-2026-08-02-not-individually-read`

### `RPT-RBM005-WORKED-0001-MA`

- Assignment: `ASN-B3F1DBF4ECF5B3C17AD05AB6`
- Summary: Conducted under the profile named, at the tier claimed, with both omitted seats justified against gates that genuinely had no evidence to read.
- Non-binding recommendation: **Monitoring**
- Evidence references: `EVI-42A4FD1E577FF694FFC79325`, `EVI-DF7E0E0BEC9315A00C43029C`
- Human signature: `SIG-VERIFY-MA-Ian McGuane-BASIS-standing-authority-2026-08-02-not-individually-read`

### `RPT-RBM005-WORKED-0001-MIA`

- Assignment: `ASN-D745FE4B76F03A3171B72F55`
- Summary: The two legs do not settle under the same rules. On an abandoned match one voids and the other stands. This is not an arbitrage.
- Non-binding recommendation: **No-build / stop**
- Evidence references: `EVI-1FAAEB84ABB73E5D458AE823`, `EVI-434D3F278AC6365A23539259`, `EVI-C217E3FBBFEDD80B9E316913`
- Human signature: `SIG-VERIFY-MIA-Ian McGuane-BASIS-standing-authority-2026-08-02-not-individually-read`

### `RPT-RBM005-WORKED-0001-PQA`

- Assignment: `ASN-ABD3D5315D1A4E0AE7E7AB46`
- Summary: Both prices carry venue, selection, size and timestamp. Neither was verified against the venue, because no venue is configured.
- Non-binding recommendation: **Corrective**
- Evidence references: `EVI-1B44C833051E7AA63FA7B1EA`, `EVI-1D2C4C0B7D0BAD4876621262`, `EVI-2758038F3238C724C49AC2DE`
- Human signature: `SIG-VERIFY-PQA-Ian McGuane-BASIS-standing-authority-2026-08-02-not-individually-read`

### `RPT-RBM005-WORKED-0001-SR`

- Assignment: `ASN-F6EE59C39441D79DF8C7248A`
- Summary: The board reached the right conclusion by the right gate, and the position it examined was constructed to be caught. That is a test of the gates, not of the market.
- Non-binding recommendation: **Control**
- Evidence references: `EVI-1FAAEB84ABB73E5D458AE823`, `EVI-42A4FD1E577FF694FFC79325`, `EVI-DF7E0E0BEC9315A00C43029C`
- Human signature: `SIG-VERIFY-SR-Ian McGuane-BASIS-standing-authority-2026-08-02-not-individually-read`

## Findings

### SEV-1: On abandonment one leg voids and the other stands

- Finding ID: `AG001-MIA-AG-02`
- Status: **OPEN**
- Category: `AG-02`
- Source report: `RPT-RBM005-WORKED-0001-MIA`
- Evidence references: `EVI-434D3F278AC6365A23539259`
- Detail: Betfair: 'If the match is abandoned before completion, all bets will be void unless the market has already been unconditionally determined.' Some Bookmaker: 'If a match is abandoned, bets stand if the fixture is replayed within 48 hours.' Under an abandonment followed by a replay inside 48 hours, the exchange leg returns its stake and settles nothing while the bookmaker leg runs to the replayed result. The position is then a single unhedged bet on Team B at 2.10 for the full bookmaker stake. The prices are correct, the arithmetic across them is correct, and the two legs are not the same event. A lock computed across differing settlement rules is a bet wearing an arb's arithmetic, and it is the central failure this profile exists to catch.

### SEV-2: Both prices were typed, and neither can be checked against its source

- Finding ID: `AG001-PQA-AG-01`
- Status: **OPEN**
- Category: `AG-01`
- Source report: `RPT-RBM005-WORKED-0001-PQA`
- Evidence references: `EVI-1D2C4C0B7D0BAD4876621262`
- Detail: Betfair Exchange 2.16 on Team A and Some Bookmaker 2.10 on Team B were entered by hand from screens. Each carries venue, selection, decimal odds, maximum stake, commission and an observation timestamp, which is the full identity a price needs. What none of them carries is a retrieval: no odds source is configured, so no leg was read from the venue that quoted it and a transcription error would be indistinguishable from a real price. The arithmetic downstream is exact about numbers whose provenance is a human's eyes.

### SEV-2: A positive margin was computed and correctly refused

- Finding ID: `AG001-ALA-AG-04`
- Status: **OPEN**
- Category: `AG-04`
- Source report: `RPT-RBM005-WORKED-0001-ALA`
- Evidence references: `EVI-1FAAEB84ABB73E5D458AE823`
- Detail: Net of the exchange's 2% commission the two legs imply under 100% combined, which on arithmetic alone reads as a lock. The engine returned SETTLEMENT_MISMATCH rather than a stake split, because the settlement check runs before the maths and refuses to size a position whose legs are not the same event. This is recorded as a finding rather than passed over because the margin is the number an operator would have seen first, and it was real. The gate that stopped it was the one reading prose, not the one reading numbers.

### SEV-2: Coverage is nought of five and no better price has been excluded

- Finding ID: `AG001-CPA-AG-05`
- Status: **OPEN**
- Category: `AG-05`
- Source report: `RPT-RBM005-WORKED-0001-CPA`
- Evidence references: `EVI-DF7E0E0BEC9315A00C43029C`
- Detail: Betfair, Smarkets, Matchbook, Paddy Power and Bet365 are the declared universe. None is configured, so none answered. The two prices under review were typed from two screens and may or may not be the best available; this review cannot say. A scan that reaches no source and reports no better price has established absence of evidence, and the failure mode is that it reads as evidence of absence. That sentence — 'no arb found' from nought of five — is the one that costs money in this domain, and it is why coverage is registered as evidence rather than mentioned.

### SEV-2: The subject was chosen to fail, so false positives are untested

- Finding ID: `AG001-SR-AG-06`
- Status: **OPEN**
- Category: `AG-06`
- Source report: `RPT-RBM005-WORKED-0001-SR`
- Evidence references: `EVI-1FAAEB84ABB73E5D458AE823`
- Detail: The initiation says plainly that this position's legs settle under materially different abandonment rules and that it was chosen for that reason. The board duly found it. That establishes the settlement gate fires when a mismatch is present; it establishes nothing about false positives — whether these gates would refuse a position that was genuinely sound, or pass one that was subtly not. A profile validated only against a subject built to fail it has been tested in one direction.

### SEV-3: The maximum stakes differ by a factor of twenty

- Finding ID: `AG002-PQA-AG-01`
- Status: **OPEN**
- Category: `AG-01`
- Source report: `RPT-RBM005-WORKED-0001-PQA`
- Evidence references: `EVI-1B44C833051E7AA63FA7B1EA`
- Detail: The exchange leg offers 5,000 and the bookmaker leg 250. Any position is bounded by the smaller, so the effective size of this claimed arb is set entirely by the bookmaker and the exchange depth is decoration. A return quoted without the binding size implies the larger.

### SEV-3: The worst case is the whole of the larger stake, not the margin

- Finding ID: `AG002-ALA-AG-04`
- Status: **OPEN**
- Category: `AG-04`
- Source report: `RPT-RBM005-WORKED-0001-ALA`
- Evidence references: `EVI-1FAAEB84ABB73E5D458AE823`
- Detail: If one leg voids and the other loses, the exposure is the entire stake on the surviving leg. A two-percent edge and a one-hundred-percent downside are not comparable quantities, and quoting the first without the second is the arithmetic that makes small edges look worth taking.

### SEV-3: Both omitted seats were omitted for want of evidence, not for convenience

- Finding ID: `AG001-MA-AG-06`
- Status: **OPEN**
- Category: `AG-06`
- Source report: `RPT-RBM005-WORKED-0001-MA`
- Evidence references: `EVI-42A4FD1E577FF694FFC79325`
- Detail: EXA was omitted because nothing was placed and no fill attempted, so there is no execution to audit. RPA was omitted because AG-06 is registered as evidence stating the reproducibility position in full. Both justifications are recorded in the initiation and both are sound: a seat with no evidence to read produces a report that looks like an assessment, which is worse than a recorded omission. Tier 2 with four specialists meets the tier_2 quorum.

### SEV-3: Every report was verified on a standing authority, not on a reading

- Finding ID: `AG002-MA-AG-06`
- Status: **OPEN**
- Category: `AG-06`
- Source report: `RPT-RBM005-WORKED-0001-MA`
- Evidence references: `EVI-DF7E0E0BEC9315A00C43029C`
- Detail: As with RBM004-MOD-0001, all six reports record verification by Ian McGuane with basis standing-authority-2026-08-02-not-individually-read. The basis is accurate and it is the weakest admissible one. Recorded here so the strength of the verification travels with the decision rather than being inferred from the presence of a signature.

### SEV-3: Prices are perishable and this decision has no stated expiry

- Finding ID: `AG002-SR-AG-06`
- Status: **OPEN**
- Category: `AG-06`
- Source report: `RPT-RBM005-WORKED-0001-SR`
- Evidence references: `EVI-42A4FD1E577FF694FFC79325`
- Detail: AG-06 records honestly that prices cannot be re-observed and that only the arithmetic reproduces. It does not follow that the decision is timeless: it is the opposite. The odds behind it were live for seconds. A decision over a block height stays true about that height forever; a decision over a price stops describing anything almost immediately, and nothing in this record says when it expired.

## Remediation

No remediation plans were recorded.

## Governance And Publication

- Decision status: **SIGNED**
- Publication: **RECORDED**

## Audit Verification

- Entries verified: 35
- Audit root hash: `sha256:e7f4ee37fb6f7fb4e0ad64982d171ab0935f9b042dbfbda9fb504b5349d2fa1d`
- Audit chain valid: **true**

## Limitations

- RBM-001 v2.0.0 remains RELEASE_CANDIDATE and cannot issue binding authority.
- Reviewer recommendations are non-binding and do not determine the machine outcome.
- This report contains only statements derived from the exported structured records.
