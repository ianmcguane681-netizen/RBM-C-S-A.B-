# RBE-001 Review Report

> **ADVISORY DRY RUN:** RBM-001 is RELEASE_CANDIDATE. This report is non-binding and does not permit merge.

## Decision Summary

- Review: `RBM002-GSCF001-0001`
- Process status: **READY**
- Machine outcome: **FAIL**
- Binding: **false**
- Merge permitted: **false**
- Decision candidate: `DCA-3137F384ABAB65C4FFF1EC9B`
- Frozen snapshot: `sha256:a28f843df70bfb5f6de95786b8f90e204120fac551ca1d1b121ba0c0f8de92eb`

The machine outcome is deterministic but is not itself governance authority.

## Target And Authority

- Target repository: `ianmcguane681-netizen/GS-CF001`
- Target artefact: `1048b11`
- Architecture authority: RBE-001 v1.1.0
- Methodology: `RBM-002` v1.0.0
- Methodology status: **RELEASE_CANDIDATE**
- Profile checksum: `sha256:064422edb67638316a470195071a2cf9915509027b1132ebdee039c75d59d8da`

## Decision Basis

FAIL was selected by RBM-DEC-001 from the frozen finding counts and substantive-evidence assessment.

Rules applied: `RBM-DEC-001`

Reason codes: `RBM-DEC-001`

## Evidence Register

### `EVI-04BE8483E23C17AA34582A1F`

- Locator: `/home/user/GS-CF001@1048b11556b62a5ee8431ba04532e9266637abf9:core/ai_governance.py`
- SHA-256: `sha256:b043aafe30d1901884c965f5f669e3a26997160f2c004510ca500c7aa37d1822`
- Source tier: `T2`
- Description: core/ai_governance.py at commit 1048b11556b6

### `EVI-87668345C78903AF9D3C5D2C`

- Locator: `/home/user/GS-CF001@1048b11556b62a5ee8431ba04532e9266637abf9:tools/adjudication_coverage.py`
- SHA-256: `sha256:023c2567711090c24f39d5adb3adb74ea34887f7a5110e424f8a6678ce9573d2`
- Source tier: `T2`
- Description: tools/adjudication_coverage.py at commit 1048b11556b6

### `EVI-9143CC24C64B52964E695F19`

- Locator: `/home/user/GS-CF001@1048b11556b62a5ee8431ba04532e9266637abf9:core/http_retry.py`
- SHA-256: `sha256:60aa0ebb39850ef7bb43ba85b40fabe3de09bbb04252bbea07979a76c07ece34`
- Source tier: `T2`
- Description: core/http_retry.py at commit 1048b11556b6

### `EVI-9E72CD56B9A0E99B04A7C7F2`

- Locator: `/home/user/GS-CF001@1048b11556b62a5ee8431ba04532e9266637abf9:test-run`
- SHA-256: `sha256:f848a8145a6437f9a8bbe0aa718236e1f74a3801338e526c7943132ec3152834`
- Source tier: `T1`
- Description: Recorded test run at commit 1048b11556b6

### `EVI-B1A628C4C422083881A3A5AD`

- Locator: `/home/user/GS-CF001@1048b11556b62a5ee8431ba04532e9266637abf9:core/adjudication.py`
- SHA-256: `sha256:de431ebda8c4255d2e3d4e826ba7910986db2be57301bc1658b6332cc2e54039`
- Source tier: `T2`
- Description: core/adjudication.py at commit 1048b11556b6

### `EVI-E1B2FF72008C4E68C9BDBDF8`

- Locator: `/home/user/GS-CF001@1048b11556b62a5ee8431ba04532e9266637abf9:core/cross_run_analysis.py`
- SHA-256: `sha256:6783d25f7bf84ec84c58111495eefa1bdd171684a923c05720e954dd6532bf09`
- Source tier: `T2`
- Description: core/cross_run_analysis.py at commit 1048b11556b6

### `EVI-E3342429DEBC4A8DB294D753`

- Locator: `/home/user/GS-CF001@1048b11556b62a5ee8431ba04532e9266637abf9:connectors/docket_join.py`
- SHA-256: `sha256:aa9a30c6ce7a6304d481f07c11d84cb867c33f21532d274b3d4d959be6795663`
- Source tier: `T2`
- Description: connectors/docket_join.py at commit 1048b11556b6

### `EVI-E7C02D5E6252CE63229AAA7C`

- Locator: `/home/user/GS-CF001@1048b11556b62a5ee8431ba04532e9266637abf9:connectors/courtlistener.py`
- SHA-256: `sha256:5f1eccd3e648a9b4375e60b67aee39c0862b86f83e7a8e55947b1fdce9f4f603`
- Source tier: `T2`
- Description: connectors/courtlistener.py at commit 1048b11556b6

### `EVI-EC59EB6ADBF6A16542BFDEF7`

- Locator: `/home/user/GS-CF001@1048b11556b62a5ee8431ba04532e9266637abf9:README.md`
- SHA-256: `sha256:ad4afc0d3a1d519d9444265ded327c2f89dce6db71e809ebb323f29f2f22652b`
- Source tier: `T2`
- Description: README.md at commit 1048b11556b6

## Reviewer Reports

### `RPT-RBM002-GSCF001-0001-EFA`

- Assignment: `ASN-5B4A211A19F1D5D1F1AE342F`
- Summary: One stated requirement in this file is detected and then not enforced. Two documented claims in the README have no enforcing code at this commit.
- Non-binding recommendation: **Corrective**
- Evidence references: `EVI-9E72CD56B9A0E99B04A7C7F2`, `EVI-87668345C78903AF9D3C5D2C`, `EVI-9143CC24C64B52964E695F19`, `EVI-E3342429DEBC4A8DB294D753`, `EVI-EC59EB6ADBF6A16542BFDEF7`
- Human signature: `SIG-VERIFY-EFA-Ian McGuane-BASIS-standing-authority-2026-08-02-not-individually-read`

### `RPT-RBM002-GSCF001-0001-GCA`

- Assignment: `ASN-843E22C39D9A18239AE360CA`
- Summary: No status in this artefact is a pinned constant. One refusal condition cannot observe the state it is meant to refuse.
- Non-binding recommendation: **Monitoring**
- Evidence references: `EVI-9E72CD56B9A0E99B04A7C7F2`, `EVI-87668345C78903AF9D3C5D2C`, `EVI-9143CC24C64B52964E695F19`, `EVI-E3342429DEBC4A8DB294D753`, `EVI-EC59EB6ADBF6A16542BFDEF7`
- Human signature: `SIG-VERIFY-GCA-Ian McGuane-BASIS-standing-authority-2026-08-02-not-individually-read`

### `RPT-RBM002-GSCF001-0001-MA`

- Assignment: `ASN-4D728B7A9693E26B80D644E0`
- Summary: The review was procedurally complete. Two seats were omitted with justifications, one of which names a role RBM-002 does not define.
- Non-binding recommendation: **Monitoring**
- Evidence references: `EVI-9E72CD56B9A0E99B04A7C7F2`, `EVI-87668345C78903AF9D3C5D2C`, `EVI-9143CC24C64B52964E695F19`, `EVI-E3342429DEBC4A8DB294D753`, `EVI-EC59EB6ADBF6A16542BFDEF7`
- Human signature: `SIG-VERIFY-MA-Ian McGuane-BASIS-standing-authority-2026-08-02-not-individually-read`

### `RPT-RBM002-GSCF001-0001-MCA`

- Assignment: `ASN-406A6AC4486B8F2EDEBD13F8`
- Summary: The census cannot distinguish a failure to retrieve from a retrieved absence, so its coverage rate is understated by an unknown amount and says so nowhere.
- Non-binding recommendation: **Corrective**
- Evidence references: `EVI-9E72CD56B9A0E99B04A7C7F2`, `EVI-87668345C78903AF9D3C5D2C`, `EVI-9143CC24C64B52964E695F19`, `EVI-E3342429DEBC4A8DB294D753`, `EVI-EC59EB6ADBF6A16542BFDEF7`
- Human signature: `SIG-VERIFY-MCA-Ian McGuane-BASIS-standing-authority-2026-08-02-not-individually-read`

### `RPT-RBM002-GSCF001-0001-SR`

- Assignment: `ASN-7243EEC9F52D0BF5FBDF64B7`
- Summary: Every seat above reviewed the code. Nobody reviewed the artefact the code already published, which carries the defect and is not repaired by fixing the code.
- Non-binding recommendation: **Corrective**
- Evidence references: `EVI-9E72CD56B9A0E99B04A7C7F2`, `EVI-87668345C78903AF9D3C5D2C`, `EVI-9143CC24C64B52964E695F19`, `EVI-E3342429DEBC4A8DB294D753`, `EVI-EC59EB6ADBF6A16542BFDEF7`
- Human signature: `SIG-VERIFY-SR-Ian McGuane-BASIS-standing-authority-2026-08-02-not-individually-read`

### `RPT-RBM002-GSCF001-0001-SVA`

- Assignment: `ASN-531989D505A82001E63CF12E`
- Summary: One sentinel in this artefact can match another sentinel and be treated as an identity.
- Non-binding recommendation: **Corrective**
- Evidence references: `EVI-9E72CD56B9A0E99B04A7C7F2`, `EVI-87668345C78903AF9D3C5D2C`, `EVI-9143CC24C64B52964E695F19`, `EVI-E3342429DEBC4A8DB294D753`, `EVI-EC59EB6ADBF6A16542BFDEF7`
- Human signature: `SIG-VERIFY-SVA-Ian McGuane-BASIS-standing-authority-2026-08-02-not-individually-read`

## Findings

### SEV-1: Rate-limited lookups are stored as archive absences

- Finding ID: `EG001-MCA-EG-02`
- Status: **OPEN**
- Category: `EG-02`
- Source report: `RPT-RBM002-GSCF001-0001-MCA`
- Evidence references: `EVI-9E72CD56B9A0E99B04A7C7F2`
- Detail: connectors/docket_join.py lookup() returns _join_result(False, 'docket lookup failed: HTTP 429') for an exhausted rate limit -- the same shape it returns for 'no RECAP docket matched the reconstructed number'. tools/adjudication_coverage.py main() then builds its resume map from every stored record without inspecting why the record stopped, so the next run skips the rate-limited row as already assessed. The census measures what fraction of decided cases have a complaint in RECAP; a throttled request is not evidence about RECAP, and counting it as one understates coverage by exactly the number of requests the API refused. The failure is silent: nothing in the output file distinguishes the two, and the summary's coverage figure reads as a completed measurement. Confirmed live -- the committed analysis/adjudication_coverage.json at this commit contains one such row of 67, and a longer census run produced eight more.

### SEV-2: The summary refusal cannot fire on the state it describes

- Finding ID: `EG001-GCA-EG-01`
- Status: **OPEN**
- Category: `EG-01`
- Source report: `RPT-RBM002-GSCF001-0001-GCA`
- Evidence references: `EVI-9E72CD56B9A0E99B04A7C7F2`
- Detail: The refusal at the end of main() is computed rather than pinned, which satisfies EG-01's surface test. It fails the substantive one: the requirement is 'do not publish a measurement without a denominator', and the condition 'incomplete and not records' can only observe the total-failure case. The set of inputs that can change this result does not include the partial pool, which is the case the requirement is about. Enumerated per RBS-002 section 4: the inputs are \`incomplete\` (set on any pagination exception) and \`records\` (truthy for any non-empty pool); no input carries how much of the pool was walked, so the guard is structurally unable to distinguish 12 of 430 from 430 of 430. Overlaps MCA-EG-02 by design -- the same defect is a computation fault and a measurement fault, and RBS-002 section 2 directs the seat to raise the boundary case rather than defer it.

### SEV-2: The published measurement is not repaired by repairing the tool

- Finding ID: `EG001-SR-EG-02`
- Status: **OPEN**
- Category: `EG-02`
- Source report: `RPT-RBM002-GSCF001-0001-SR`
- Evidence references: `EVI-9E72CD56B9A0E99B04A7C7F2`
- Detail: MCA, GCA, EFA and SVA all reviewed tools/adjudication_coverage.py and connectors/docket_join.py. None reviewed analysis/adjudication_coverage.json, which is committed at this same commit, is cited in the README as a completed sweep of all 67 occurrence-establishing cases, and contains a row recording 'join failed: docket lookup failed: HTTP 429'. A code fix changes what future runs write. It does not change what this file says, and the README quotes this file. Any remediation that stops at the code leaves a published artefact asserting something the board has just found to be untrue.

### SEV-2: A partially enumerated pool still produces a full summary

- Finding ID: `EG002-MCA-EG-02`
- Status: **OPEN**
- Category: `EG-02`
- Source report: `RPT-RBM002-GSCF001-0001-MCA`
- Evidence references: `EVI-9E72CD56B9A0E99B04A7C7F2`
- Detail: fetch_establishing_records() returns (collected, incomplete) and breaks out of pagination on any exception, so a walk that retrieved 12 of 430 records returns 12 and a reason. main() refuses to write a summary only when 'incomplete and not records' -- that is, only when the pool is entirely empty. A pool that stopped part-way passes the guard and writes pool_size_enumerated equal to the partial count, so a coverage rate is computed over a denominator that is not the population. The guard's own comment says the run 'has no denominator', which is true of the partial case too.

### SEV-2: The strata guard detects a mismatch and proceeds anyway

- Finding ID: `EG001-EFA-EG-03`
- Status: **OPEN**
- Category: `EG-03`
- Source report: `RPT-RBM002-GSCF001-0001-EFA`
- Evidence references: `EVI-9E72CD56B9A0E99B04A7C7F2`
- Detail: tools/adjudication_coverage.py states 'A cache is only reusable for the strata that produced it. Reusing a plaintiff-only pool for a judgment=1,2 run would report a coverage rate over a population that was never walked, and the file gives no hint.' The code below that comment compares cached_judgment to args.judgment, prints 're-enumerating rather than mixing strata', and continues -- re-enumerating a different population and then overwriting the pool cache the existing results were measured against. Detecting a condition and proceeding is not enforcement. The comment describes a guard that does not exist. Note also that cached.get('judgment', '1') supplies a default for caches written before the field existed, so a file that never declared its strata is treated as plaintiff-only on no evidence.

### SEV-2: Two unidentifiable records share one resume key

- Finding ID: `EG001-SVA-EG-05`
- Status: **OPEN**
- Category: `EG-05`
- Source report: `RPT-RBM002-GSCF001-0001-SVA`
- Evidence references: `EVI-9E72CD56B9A0E99B04A7C7F2`
- Detail: _resume_key returns f"{row.get('court') or '?'}/{row.get('docket') or '?'}". The '?' is a sentinel meaning 'this record could not be identified'. Two records that both fail to produce a court and a docket therefore produce the identical key '?/?', and the resume map treats the second as already assessed. The comment above the resume block reasons carefully about docket collisions across districts and then introduces a collision of its own, in the case where the least is known about the records involved. This is the same shape as the defect this repository already found in its mechanism classifier, where two records that both failed to classify matched each other on the fallback value and produced a corroboration PASS.

### SEV-2: The recorded test run could not be reproduced and was substituted

- Finding ID: `EG002-MA-EG-06`
- Status: **OPEN**
- Category: `EG-06`
- Source report: `RPT-RBM002-GSCF001-0001-MA`
- Evidence references: `EVI-9E72CD56B9A0E99B04A7C7F2`
- Detail: This review was first convened in a container that has since been reclaimed, taking its review store with it. Five of six evidence items regenerated with IDENTICAL reference ids, because a source file at a named commit is derivable: the id is a hash over session, locator and content, and all three were reproducible. The sixth was the recorded test run, and it did not regenerate. A test log is a record of a moment rather than a derivable artefact — re-running the suite today produces a different log at a different time, which is a different fact about a different run. The suite was re-run (300 passed) and registered as EVI-9E72CD56B9A0E99B04A7C7F2, and every report's reference to the original was repointed at it. This is a substitution and is recorded as one. It is also EG-06 applied to the review that contains EG-06: the gate about reproducibility was the only evidence in this review that could not be reproduced.

### SEV-3: An omitted seat's justification assigns work to no defined role

- Finding ID: `EG001-MA-EG-03`
- Status: **OPEN**
- Category: `EG-03`
- Source report: `RPT-RBM002-GSCF001-0001-MA`
- Evidence references: `EVI-9E72CD56B9A0E99B04A7C7F2`
- Detail: The initiation record omits RPA with the justification that reproducibility 'is assessed by the board chair against a recorded test run rather than by a seat'. RBM-002 section 4 gives the board chair no audit function -- BC convenes, ratifies and publishes. The justification therefore assigns EG-06 to nobody while reading as though it were covered. The T1 test-run evidence was in fact registered and is sound (276 passed at this commit), so the gate was met; the record of who met it is wrong.

### SEV-3: Resume correctness is asserted in a comment and tested nowhere

- Finding ID: `EG002-EFA-EG-03`
- Status: **OPEN**
- Category: `EG-03`
- Source report: `RPT-RBM002-GSCF001-0001-EFA`
- Evidence references: `EVI-9E72CD56B9A0E99B04A7C7F2`
- Detail: The resume-key comment explains at length why the key must be court-qualified: 'a ~430-record walk across ninety districts would [collide], and the loss would look like completion.' That reasoning is correct and there is no test for it. The repository's test suite at this commit (276 passing) contains no test of _resume_key, of the resume path, or of the summary refusal. A requirement whose only record is a comment cannot survive a refactor by anyone who has not read the comment.

### SEV-3: A missing strata field defaults to a specific strata

- Finding ID: `EG002-SVA-EG-05`
- Status: **OPEN**
- Category: `EG-05`
- Source report: `RPT-RBM002-GSCF001-0001-SVA`
- Evidence references: `EVI-9E72CD56B9A0E99B04A7C7F2`
- Detail: cached.get('judgment', '1') treats the absence of a strata declaration as a declaration of plaintiff-only. Absence is not a value. The committed analysis/adjudication_pool.json at this commit has no judgment field and is in fact plaintiff-only, so the default is correct by luck rather than by record.

### SEV-3: Seats sharing a model are being counted as independent voices

- Finding ID: `EG002-SR-EG-06`
- Status: **OPEN**
- Category: `EG-06`
- Source report: `RPT-RBM002-GSCF001-0001-SR`
- Evidence references: `EVI-9E72CD56B9A0E99B04A7C7F2`
- Detail: Four of six seats share two models (provena-eng-b across GCA and MCA, provena-eng-c across EFA and SVA). The runtime recorded this, which is the control working. The board should nonetheless read GCA-EG-01 and MCA-EG-02 as one voice rather than two corroborating ones -- they concern the same defect and were produced by the same model. Note the same applies to this seat's own relationship to the others: I am not an independent check on a shared upstream error.

### SEV-4: Exit code 2 is reused for two distinct refusals

- Finding ID: `EG002-GCA-EG-01`
- Status: **OPEN**
- Category: `EG-01`
- Source report: `RPT-RBM002-GSCF001-0001-GCA`
- Evidence references: `EVI-9E72CD56B9A0E99B04A7C7F2`
- Detail: main() returns 2 for 'pool not enumerated'. A caller cannot distinguish that from other refusals by exit code alone. Observation only: at this commit there is one such path, so no ambiguity exists yet. Raised because the file is about to grow more refusal paths.

## Remediation

No remediation plans were recorded.

## Governance And Publication

- Decision status: **SIGNED**
- Publication: **RECORDED**

## Audit Verification

- Entries verified: 37
- Audit root hash: `sha256:1ce94331db00fe2a8d6ef06cc9dd1ace1fe9d653a4f7a380329f6e644289f305`
- Audit chain valid: **true**

## Limitations

- RBM-001 v2.0.0 remains RELEASE_CANDIDATE and cannot issue binding authority.
- Reviewer recommendations are non-binding and do not determine the machine outcome.
- This report contains only statements derived from the exported structured records.
