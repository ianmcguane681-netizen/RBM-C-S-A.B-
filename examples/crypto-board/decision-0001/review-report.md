# RBE-001 Review Report

> **ADVISORY DRY RUN:** RBM-001 is RELEASE_CANDIDATE. This report is non-binding and does not permit merge.

## Decision Summary

- Review: `RBM003-USDC-0001`
- Process status: **READY**
- Machine outcome: **FAIL**
- Binding: **false**
- Merge permitted: **false**
- Decision candidate: `DCA-764C804B304B4FD305A6DA48`
- Frozen snapshot: `sha256:7c32fbbad82cd6565d6154931b933ff1b9ac28396ef957c20a6b402ccff8dfb2`

The machine outcome is deterministic but is not itself governance authority.

## Target And Authority

- Target repository: `ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48`
- Target artefact: `25660396`
- Architecture authority: RBE-001 v1.1.0
- Methodology: `RBM-003` v1.0.0
- Methodology status: **RELEASE_CANDIDATE**
- Profile checksum: `sha256:ac299c5aa2dc3aee224f15dbda0a59cf21c37937298ed66390139f8cf9873cb3`

## Decision Basis

FAIL was selected by RBM-DEC-002 from the frozen finding counts and substantive-evidence assessment.

Rules applied: `RBM-DEC-001`, `RBM-DEC-002`

Reason codes: `RBM-DEC-002`

## Evidence Register

### `EVI-1A62BD858EE244F8BA8894AF`

- Locator: `ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48@25660396:upgradeability`
- SHA-256: `sha256:25943b0cd3dca9d7a7bd241da969ef04fde083736d4791a991d9e0f42ae1b84e`
- Source tier: `T2`
- Description: Upgradeability probe for 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48

### `EVI-262CF180A650DDDDBF751717`

- Locator: `ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48@25660396:decimals`
- SHA-256: `sha256:1b20faab6bd4f0a28e6dccc40387fbb6bc37cf249914e73abb87378079425035`
- Source tier: `T1`
- Description: decimals for 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48 at block 25660396

### `EVI-2CA339F44E62779AE9200D4A`

- Locator: `ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48@25661826:liquidity`
- SHA-256: `sha256:1a934b73993384ddcbc8be1f623093a03b30a212ea1593621b92783e633602f2`
- Source tier: `T1`
- Description: liquidity finding for 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48

### `EVI-4449B28DD6D615239F5E3671`

- Locator: `ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48@25661826:lp_composition`
- SHA-256: `sha256:7033ab24734102a4e4f6c1c2f8103678f3b50755e947e4ebe58eaaf97ee5c276`
- Source tier: `T1`
- Description: lp_composition finding for 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48

### `EVI-8148ECCFE37CBFFB9BFC87A6`

- Locator: `ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48@25660396:symbol`
- SHA-256: `sha256:e5449df24ae3a43e75b76c0ace20cb38421c22cba5277fc6e6928bf723a4f22b`
- Source tier: `T1`
- Description: symbol for 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48 at block 25660396

### `EVI-8BBF0CA463D9CB18D59B9F42`

- Locator: `ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48@25660396:totalSupply`
- SHA-256: `sha256:a46473ae1d16034f76cd56ab64c0097899d56c7fb343b6166d106c49c8f8b6cc`
- Source tier: `T1`
- Description: totalSupply for 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48 at block 25660396

### `EVI-9EAF8C339454C52653CF8672`

- Locator: `ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48@25660396:name`
- SHA-256: `sha256:ec5cdc57b71e7a25c143a1d57b2036ac89f07ef4ecb45757bd262247aaa034a3`
- Source tier: `T1`
- Description: name for 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48 at block 25660396

### `EVI-C3A7EABEBA55DC868D79F91A`

- Locator: `ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48@25661826:locks`
- SHA-256: `sha256:6c042a01ac517574872d00edca240dd25ff88ac70902186db184e47f55f3c8db`
- Source tier: `T1`
- Description: locks finding for 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48

## Reviewer Reports

### `RPT-RBM003-USDC-0001-CAA`

- Assignment: `ASN-498140D5C7BB0E42F93D7B4E`
- Summary: The contract is upgradeable, mintable, pausable and can blacklist. Every one of those is held by an address that is not the token holder.
- Non-binding recommendation: **Corrective**
- Evidence references: `EVI-1A62BD858EE244F8BA8894AF`, `EVI-262CF180A650DDDDBF751717`, `EVI-2CA339F44E62779AE9200D4A`, `EVI-4449B28DD6D615239F5E3671`, `EVI-8148ECCFE37CBFFB9BFC87A6`, `EVI-8BBF0CA463D9CB18D59B9F42`, `EVI-9EAF8C339454C52653CF8672`, `EVI-C3A7EABEBA55DC868D79F91A`
- Human signature: `SIG-VERIFY-CAA-Ian McGuane`

### `RPT-RBM003-USDC-0001-CVA`

- Assignment: `ASN-7AB00FA61E1FCE31A9512179`
- Summary: Supply reproduces exactly from contract state at the reviewed block. What that supply is worth is not a chain fact and no gate here reaches it.
- Non-binding recommendation: **Monitoring**
- Evidence references: `EVI-1A62BD858EE244F8BA8894AF`, `EVI-262CF180A650DDDDBF751717`, `EVI-2CA339F44E62779AE9200D4A`, `EVI-4449B28DD6D615239F5E3671`, `EVI-8148ECCFE37CBFFB9BFC87A6`, `EVI-8BBF0CA463D9CB18D59B9F42`, `EVI-9EAF8C339454C52653CF8672`, `EVI-C3A7EABEBA55DC868D79F91A`
- Human signature: `SIG-VERIFY-CVA-Ian McGuane`

### `RPT-RBM003-USDC-0001-MA`

- Assignment: `ASN-6FA7EE220955E0A6DE7A1D06`
- Summary: The review was procedurally sound but is under-tiered for what it found.
- Non-binding recommendation: **Corrective**
- Evidence references: `EVI-1A62BD858EE244F8BA8894AF`, `EVI-262CF180A650DDDDBF751717`, `EVI-2CA339F44E62779AE9200D4A`, `EVI-4449B28DD6D615239F5E3671`, `EVI-8148ECCFE37CBFFB9BFC87A6`, `EVI-8BBF0CA463D9CB18D59B9F42`, `EVI-9EAF8C339454C52653CF8672`, `EVI-C3A7EABEBA55DC868D79F91A`
- Human signature: `SIG-VERIFY-MA-Ian McGuane`

### `RPT-RBM003-USDC-0001-RPA`

- Assignment: `ASN-7AA1EAAF876C0C90B0C713D5`
- Summary: Every figure in this review reproduces from its recorded block height.
- Non-binding recommendation: **Proceed to next gate**
- Evidence references: `EVI-1A62BD858EE244F8BA8894AF`, `EVI-262CF180A650DDDDBF751717`, `EVI-2CA339F44E62779AE9200D4A`, `EVI-4449B28DD6D615239F5E3671`, `EVI-8148ECCFE37CBFFB9BFC87A6`, `EVI-8BBF0CA463D9CB18D59B9F42`, `EVI-9EAF8C339454C52653CF8672`, `EVI-C3A7EABEBA55DC868D79F91A`
- Human signature: `SIG-VERIFY-RPA-Ian McGuane`

### `RPT-RBM003-USDC-0001-SR`

- Assignment: `ASN-E758AF3E26DC77950BB3FA04`
- Summary: Every gate that could run, ran. The thing that would actually cost a holder money is not reachable by any of them.
- Non-binding recommendation: **Corrective**
- Evidence references: `EVI-1A62BD858EE244F8BA8894AF`, `EVI-262CF180A650DDDDBF751717`, `EVI-2CA339F44E62779AE9200D4A`, `EVI-4449B28DD6D615239F5E3671`, `EVI-8148ECCFE37CBFFB9BFC87A6`, `EVI-8BBF0CA463D9CB18D59B9F42`, `EVI-9EAF8C339454C52653CF8672`, `EVI-C3A7EABEBA55DC868D79F91A`
- Human signature: `SIG-VERIFY-SR-Ian McGuane`

### `RPT-RBM003-USDC-0001-TKA`

- Assignment: `ASN-DCC46EEA204BF32D28430704`
- Summary: The lock gate could not be meaningfully executed. Nothing about locked supply is established either way.
- Non-binding recommendation: **Research**
- Evidence references: `EVI-1A62BD858EE244F8BA8894AF`, `EVI-262CF180A650DDDDBF751717`, `EVI-2CA339F44E62779AE9200D4A`, `EVI-4449B28DD6D615239F5E3671`, `EVI-8148ECCFE37CBFFB9BFC87A6`, `EVI-8BBF0CA463D9CB18D59B9F42`, `EVI-9EAF8C339454C52653CF8672`, `EVI-C3A7EABEBA55DC868D79F91A`
- Human signature: `SIG-VERIFY-TKA-Ian McGuane`

## Findings

### SEV-2: The board verified what is checkable and the risk is elsewhere

- Finding ID: `CG001-SR-CG-01`
- Status: **OPEN**
- Category: `CG-01`
- Source report: `RPT-RBM003-USDC-0001-SR`
- Evidence references: `EVI-1A62BD858EE244F8BA8894AF`
- Detail: Six gates examined supply, authority, locks, depth, distinctness and reproducibility. Every one is a chain fact. The claim a USDC holder relies on is that each unit is redeemable for one dollar, and that rests on reserves held by a company, attested by an auditor, under a regulator -- none of which is on any chain. A reader seeing six gates answered may conclude the asset was assessed. It was not; its principal risk was never in scope. This is a limit of the profile, not of the execution.

### SEV-2: USDC is upgradeable and the EIP-1967 slots are empty

- Finding ID: `CG001-CAA-CG-04`
- Status: **OPEN**
- Category: `CG-04`
- Source report: `RPT-RBM003-USDC-0001-CAA`
- Evidence references: `EVI-1A62BD858EE244F8BA8894AF`
- Detail: The three EIP-1967 slots read empty and implementation() reverts, which together look exactly like a non-upgradeable contract. The pre-EIP-1967 OpenZeppelin slots are populated: implementation 0x43506849d7c04f9138d1a2050bbf3a0c054402dd, admin 0x807a96288a1a408dbc13de2b1d087d10356395d2. The proxy is transparent, so it routes non-admin callers to the implementation and the function probe reverts rather than answering. Any assessment checking only EIP-1967 would report one of the largest tokens in existence as immutable.

### SEV-2: An upgradeable proxy was reviewed at Tier 2

- Finding ID: `CG001-MA-CG-04`
- Status: **OPEN**
- Category: `CG-04`
- Source report: `RPT-RBM003-USDC-0001-MA`
- Evidence references: `EVI-1A62BD858EE244F8BA8894AF`
- Detail: The initiation set Tier 2 with the rationale that upgradeability was unknown and that the MA seat should raise the tiering if CAA established it. CAA has established it. RBM-003 section 8 makes anything with an upgradeable proxy Tier 3 by construction, requiring six specialists; this review seated four, with ADA and LQA omitted because their gates had no implementation at initiation. The review is therefore procedurally insufficient for its own subject, and the decision must not read as a Tier 3 result.

### SEV-2: Mint, pause and blacklist authority sit with named addresses

- Finding ID: `CG002-CAA-CG-04`
- Status: **OPEN**
- Category: `CG-04`
- Source report: `RPT-RBM003-USDC-0001-CAA`
- Evidence references: `EVI-1A62BD858EE244F8BA8894AF`
- Detail: owner() resolves to 0xfcb19e6a322b27c06842a71e8c725399f049ae3a and masterMinter() to 0xe982615d461dd5cd06575bbea87624fda4e3de17. paused() answers false, which establishes that a pause function exists and is currently off rather than that none exists. Together these mean supply, transferability and individual balances are all subject to decisions by parties other than the holder.

### SEV-3: The reviewed figure is supply, not backing

- Finding ID: `CG001-CVA-CG-01`
- Status: **OPEN**
- Category: `CG-01`
- Source report: `RPT-RBM003-USDC-0001-CVA`
- Evidence references: `EVI-1A62BD858EE244F8BA8894AF`
- Detail: totalSupply reproduces at block 25660396 as 49,534,577,197 USDC with decimals read from the contract as 6, not assumed. That establishes how many units exist. It does not establish that each is redeemable for one dollar, which is the claim anyone actually relies on and which lives entirely in off-chain attestations this profile cannot read. Recorded so that a reader does not take a reproduced supply figure as a reproduced backing figure.

### SEV-3: CG-03 ran against an empty locker registry

- Finding ID: `CG001-TKA-CG-03`
- Status: **OPEN**
- Category: `CG-03`
- Source report: `RPT-RBM003-USDC-0001-TKA`
- Evidence references: `EVI-1A62BD858EE244F8BA8894AF`
- Detail: The finding returned NO_LOCK_CONTRACT_IDENTIFIED, and its own description states the registry is empty and zero known lockers were searched. Burn addresses were probed and hold 53,911,272,789 units (0.0001% of supply). No vesting or lock contract was searched for, because top-holder enumeration is not available from JSON-RPC and the registry carries no verified addresses. This is a correctly reported non-result and must not be read as evidence that supply is unlocked.

### SEV-3: Exit depth was measured against one quote asset

- Finding ID: `CG002-SR-CG-05`
- Status: **OPEN**
- Category: `CG-05`
- Source report: `RPT-RBM003-USDC-0001-SR`
- Evidence references: `EVI-1A62BD858EE244F8BA8894AF`
- Detail: CG-05 quoted USDC into WETH only: 0.00%, 0.33% and 39.84% worse at 10k, 1M and 100M. The 39.84% figure is a single-venue route, not a realistic exit, because a seller of that size would split across venues and quote assets. The curve establishes that depth falls away sharply and does not establish what a real exit would cost.

### SEV-4: Four of four sampled readings reproduced

- Finding ID: `CG001-RPA-CG-06`
- Status: **OPEN**
- Category: `CG-06`
- Source report: `RPT-RBM003-USDC-0001-RPA`
- Evidence references: `EVI-1A62BD858EE244F8BA8894AF`
- Detail: Resampled at block 25660396 through an archive-capable provider: four reproduced, zero diverged, zero unattempted. Each reading carries chain, block height, contract, query and hash. Observation only; no defect asserted. Noted because CG-06 is the gate most likely to pass for the wrong reason, and this one was attempted in full rather than sampled thinly.

## Remediation

No remediation plans were recorded.

## Governance And Publication

- Decision status: **SIGNED**
- Publication: **RECORDED**

## Audit Verification

- Entries verified: 35
- Audit root hash: `sha256:1be7e06de21cbbcc0b570800795aa6ab13a6055e034a2e707119033c0a9cf9f0`
- Audit chain valid: **true**

## Limitations

- RBM-001 v2.0.0 remains RELEASE_CANDIDATE and cannot issue binding authority.
- Reviewer recommendations are non-binding and do not determine the machine outcome.
- This report contains only statements derived from the exported structured records.
