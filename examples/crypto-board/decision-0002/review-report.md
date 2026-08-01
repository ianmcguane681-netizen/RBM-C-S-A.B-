# RBE-001 Review Report

> **ADVISORY DRY RUN:** RBM-001 is RELEASE_CANDIDATE. This report is non-binding and does not permit merge.

## Decision Summary

- Review: `RBM003-USDC-0002`
- Process status: **READY**
- Machine outcome: **FAIL**
- Binding: **false**
- Merge permitted: **false**
- Decision candidate: `DCA-EB9183BCC150C25702F16AAD`
- Frozen snapshot: `sha256:99724d2cdd26ae3533d7a87cea42babff5caf33a3308faa7970fe042e36cf089`

The machine outcome is deterministic but is not itself governance authority.

## Target And Authority

- Target repository: `ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48`
- Target artefact: `25662176`
- Architecture authority: RBE-001 v1.1.0
- Methodology: `RBM-003` v1.0.0
- Methodology status: **RELEASE_CANDIDATE**
- Profile checksum: `sha256:ac299c5aa2dc3aee224f15dbda0a59cf21c37937298ed66390139f8cf9873cb3`

## Decision Basis

FAIL was selected by RBM-DEC-002 from the frozen finding counts and substantive-evidence assessment.

Rules applied: `RBM-DEC-001`, `RBM-DEC-002`

Reason codes: `RBM-DEC-002`

## Evidence Register

### `EVI-0CB098806DB562503B1408C3`

- Locator: `ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48@25662176:upgradeability`
- SHA-256: `sha256:b91c6181be02d6835b7a5c22dca6a53f05bed461d5ce7f7ebe276b08ee179e86`
- Source tier: `T2`
- Description: upgradeability for 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48 at block 25662176

### `EVI-23CEB7E3AD5C5D3299B231B0`

- Locator: `ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48@25662176:locks`
- SHA-256: `sha256:5c7f6537ad7357d0173e82145c93b0b98139327398e881e79d15bdf8cd5ed5f2`
- Source tier: `T1`
- Description: locks for 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48 at block 25662176

### `EVI-458DD31911B4EB70BC528335`

- Locator: `ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48@25662176:address_distinctness`
- SHA-256: `sha256:6c543f2c185d7b9a065c0c97de54258c7b5c83dbb3efd74b11b9071bc9fecf9e`
- Source tier: `T2`
- Description: address_distinctness for 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48 at block 25662176

### `EVI-50627FC253727D641396BD22`

- Locator: `ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48@25662176:totalSupply`
- SHA-256: `sha256:5fdf33f172f7221d232ae50fec0da0c2f7a68886f818e939f4287961b54edb92`
- Source tier: `T1`
- Description: totalSupply for 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48 at block 25662176

### `EVI-56EFEE4BDD2940298B9C9A1C`

- Locator: `ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48@25662176:liquidity`
- SHA-256: `sha256:796796f17320dd7815f99a64ca31b14cf5e3cf259eb0e10964544e61fb804939`
- Source tier: `T1`
- Description: liquidity for 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48 at block 25662176

### `EVI-7251ECB755BA8B462F971844`

- Locator: `ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48@25662176:lp_composition`
- SHA-256: `sha256:319d754fb84b3e3b2ecef7e8964bd3ba9ae3f83a2dd2dbe7acab00bb2429a3bf`
- Source tier: `T1`
- Description: lp_composition for 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48 at block 25662176

### `EVI-72A87795F70E6FDEBFBA642A`

- Locator: `ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48@25662176:name`
- SHA-256: `sha256:ec5cdc57b71e7a25c143a1d57b2036ac89f07ef4ecb45757bd262247aaa034a3`
- Source tier: `T1`
- Description: name for 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48 at block 25662176

### `EVI-8654949EA26EFD946CFA7372`

- Locator: `ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48@25662176:symbol`
- SHA-256: `sha256:e5449df24ae3a43e75b76c0ace20cb38421c22cba5277fc6e6928bf723a4f22b`
- Source tier: `T1`
- Description: symbol for 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48 at block 25662176

### `EVI-FA2F424BC61FD26539BA3851`

- Locator: `ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48@25662176:decimals`
- SHA-256: `sha256:1b20faab6bd4f0a28e6dccc40387fbb6bc37cf249914e73abb87378079425035`
- Source tier: `T1`
- Description: decimals for 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48 at block 25662176

## Reviewer Reports

### `RPT-RBM003-USDC-0002-ADA`

- Assignment: `ASN-1F861EE1B60D71737E0DCA67`
- Summary: Address activity was walked across a stated 60-block window with no gap. A third of the addresses seen share a first funder, so an address count in this window is not a count of actors.
- Non-binding recommendation: **Monitoring**
- Evidence references: `EVI-0CB098806DB562503B1408C3`, `EVI-23CEB7E3AD5C5D3299B231B0`, `EVI-458DD31911B4EB70BC528335`, `EVI-50627FC253727D641396BD22`, `EVI-56EFEE4BDD2940298B9C9A1C`, `EVI-7251ECB755BA8B462F971844`, `EVI-72A87795F70E6FDEBFBA642A`, `EVI-8654949EA26EFD946CFA7372`, `EVI-FA2F424BC61FD26539BA3851`
- Human signature: `SIG-VERIFY-ADA-Ian McGuane-BASIS-summary-reading`

### `RPT-RBM003-USDC-0002-CAA`

- Assignment: `ASN-181E433584DB9BA3802AD8E1`
- Summary: USDC is upgradeable behind a transparent proxy whose EIP-1967 slots are empty, and mint, pause and blacklist authority sit with named addresses.
- Non-binding recommendation: **Control**
- Evidence references: `EVI-0CB098806DB562503B1408C3`, `EVI-23CEB7E3AD5C5D3299B231B0`, `EVI-458DD31911B4EB70BC528335`, `EVI-50627FC253727D641396BD22`, `EVI-56EFEE4BDD2940298B9C9A1C`, `EVI-7251ECB755BA8B462F971844`, `EVI-72A87795F70E6FDEBFBA642A`, `EVI-8654949EA26EFD946CFA7372`, `EVI-FA2F424BC61FD26539BA3851`
- Human signature: `SIG-VERIFY-CAA-Ian McGuane-BASIS-summary-reading`

### `RPT-RBM003-USDC-0002-CVA`

- Assignment: `ASN-AA5579D9361621E1DFBD7C3F`
- Summary: Supply, symbol, name and decimals reproduce from contract state at the reviewed block. What a unit is worth is not a chain fact and no gate here reaches it.
- Non-binding recommendation: **Monitoring**
- Evidence references: `EVI-0CB098806DB562503B1408C3`, `EVI-23CEB7E3AD5C5D3299B231B0`, `EVI-458DD31911B4EB70BC528335`, `EVI-50627FC253727D641396BD22`, `EVI-56EFEE4BDD2940298B9C9A1C`, `EVI-7251ECB755BA8B462F971844`, `EVI-72A87795F70E6FDEBFBA642A`, `EVI-8654949EA26EFD946CFA7372`, `EVI-FA2F424BC61FD26539BA3851`
- Human signature: `SIG-VERIFY-CVA-Ian McGuane-BASIS-summary-reading`

### `RPT-RBM003-USDC-0002-LQA`

- Assignment: `ASN-7CA556510C11B43AE27D4231`
- Summary: Exit cost was quoted at three sizes into two assets across ten venues. Depth is deep at a million and falls apart at a hundred million, and the two assets disagree by roughly a factor of two about how badly.
- Non-binding recommendation: **Control**
- Evidence references: `EVI-0CB098806DB562503B1408C3`, `EVI-23CEB7E3AD5C5D3299B231B0`, `EVI-458DD31911B4EB70BC528335`, `EVI-50627FC253727D641396BD22`, `EVI-56EFEE4BDD2940298B9C9A1C`, `EVI-7251ECB755BA8B462F971844`, `EVI-72A87795F70E6FDEBFBA642A`, `EVI-8654949EA26EFD946CFA7372`, `EVI-FA2F424BC61FD26539BA3851`
- Human signature: `SIG-VERIFY-LQA-Ian McGuane-BASIS-summary-reading`

### `RPT-RBM003-USDC-0002-MA`

- Assignment: `ASN-FFD4485B8C7B9FED4753A3CB`
- Summary: The tiering defect that this review exists to answer is answered. Two further methodology defects are raised, one inherited from the predecessor and one live here.
- Non-binding recommendation: **Monitoring**
- Evidence references: `EVI-0CB098806DB562503B1408C3`, `EVI-23CEB7E3AD5C5D3299B231B0`, `EVI-458DD31911B4EB70BC528335`, `EVI-50627FC253727D641396BD22`, `EVI-56EFEE4BDD2940298B9C9A1C`, `EVI-7251ECB755BA8B462F971844`, `EVI-72A87795F70E6FDEBFBA642A`, `EVI-8654949EA26EFD946CFA7372`, `EVI-FA2F424BC61FD26539BA3851`
- Human signature: `SIG-VERIFY-MA-Ian McGuane-BASIS-summary-reading`

### `RPT-RBM003-USDC-0002-RPA`

- Assignment: `ASN-13698F5C13420BEAED6551A7`
- Summary: Every reading that can be resampled was resampled and reproduced. That covers four of the nine evidence items; the other five are assessments rather than single readings.
- Non-binding recommendation: **Proceed to next gate**
- Evidence references: `EVI-0CB098806DB562503B1408C3`, `EVI-23CEB7E3AD5C5D3299B231B0`, `EVI-458DD31911B4EB70BC528335`, `EVI-50627FC253727D641396BD22`, `EVI-56EFEE4BDD2940298B9C9A1C`, `EVI-7251ECB755BA8B462F971844`, `EVI-72A87795F70E6FDEBFBA642A`, `EVI-8654949EA26EFD946CFA7372`, `EVI-FA2F424BC61FD26539BA3851`
- Human signature: `SIG-VERIFY-RPA-Ian McGuane-BASIS-summary-reading`

### `RPT-RBM003-USDC-0002-SR`

- Assignment: `ASN-BCFC43CBE2891978850E3F61`
- Summary: Six gates were seated and five answered. All of them are chain facts, and the claim a USDC holder relies on is not a chain fact.
- Non-binding recommendation: **Corrective**
- Evidence references: `EVI-0CB098806DB562503B1408C3`, `EVI-23CEB7E3AD5C5D3299B231B0`, `EVI-458DD31911B4EB70BC528335`, `EVI-50627FC253727D641396BD22`, `EVI-56EFEE4BDD2940298B9C9A1C`, `EVI-7251ECB755BA8B462F971844`, `EVI-72A87795F70E6FDEBFBA642A`, `EVI-8654949EA26EFD946CFA7372`, `EVI-FA2F424BC61FD26539BA3851`
- Human signature: `SIG-VERIFY-SR-Ian McGuane-BASIS-summary-reading`

### `RPT-RBM003-USDC-0002-TKA`

- Assignment: `ASN-C005762C948FD63780245C9B`
- Summary: CG-03 is NOT ASSESSED for this review. The locker registry is empty, so zero lock contracts were searched, and this seat declines to present a non-result as a gate result.
- Non-binding recommendation: **Research**
- Evidence references: `EVI-0CB098806DB562503B1408C3`, `EVI-23CEB7E3AD5C5D3299B231B0`, `EVI-458DD31911B4EB70BC528335`, `EVI-50627FC253727D641396BD22`, `EVI-56EFEE4BDD2940298B9C9A1C`, `EVI-7251ECB755BA8B462F971844`, `EVI-72A87795F70E6FDEBFBA642A`, `EVI-8654949EA26EFD946CFA7372`, `EVI-FA2F424BC61FD26539BA3851`
- Human signature: `SIG-VERIFY-TKA-Ian McGuane-BASIS-summary-reading`

## Findings

### SEV-2: The board verified what is checkable and the risk is elsewhere

- Finding ID: `CG003-SR-CG-01`
- Status: **OPEN**
- Category: `CG-01`
- Source report: `RPT-RBM003-USDC-0002-SR`
- Evidence references: `EVI-50627FC253727D641396BD22`
- Detail: This review is materially stronger than its predecessor: six specialists rather than four, every reading at one block height rather than two, and two gates answered live that had no implementation before. None of that touches the question. Every gate in RBM-003 examines chain state. The claim a USDC holder relies on is that each unit is redeemable for one dollar, and that rests on reserves held by a company, attested by an auditor, under a regulator, none of which is on any chain. A reader seeing a Tier 3 review with six specialists may conclude the asset was assessed. It was not; its principal risk was never in scope, and running the review more thoroughly has not changed that by one inch. This is a limit of the profile, not of the execution.

### SEV-2: USDC is upgradeable and the EIP-1967 slots are empty

- Finding ID: `CG003-CAA-CG-04`
- Status: **OPEN**
- Category: `CG-04`
- Source report: `RPT-RBM003-USDC-0002-CAA`
- Evidence references: `EVI-0CB098806DB562503B1408C3`
- Detail: At block 25662176 the three EIP-1967 slots read empty and implementation() reverts, which together look exactly like a non-upgradeable contract. The pre-EIP-1967 OpenZeppelin slots are populated: implementation 0x43506849d7c04f9138d1a2050bbf3a0c054402dd, admin 0x807a96288a1a408dbc13de2b1d087d10356395d2. The proxy is transparent, so it routes non-admin callers to the implementation and the function probe reverts rather than answering. Any assessment checking only EIP-1967 would report one of the largest tokens in existence as immutable. The admin can replace the implementation entirely, so every behaviour verified by every other gate in this review holds only while that admin chooses not to act.

### SEV-2: Mint, pause and blacklist authority sit with named addresses

- Finding ID: `CG004-CAA-CG-04`
- Status: **OPEN**
- Category: `CG-04`
- Source report: `RPT-RBM003-USDC-0002-CAA`
- Evidence references: `EVI-0CB098806DB562503B1408C3`
- Detail: owner() resolves to 0xfcb19e6a322b27c06842a71e8c725399f049ae3a and masterMinter() to 0xe982615d461dd5cd06575bbea87624fda4e3de17. paused() answers false, which establishes that a pause function exists and is currently off rather than that none exists. admin() and implementation() both revert for this caller, which is the transparent proxy behaving correctly and not an absence of those functions. Together these mean supply, transferability and individual balances are subject to decisions by parties other than the holder. The supply figure this review reproduces is therefore a measurement at a height, not a bound.

### SEV-2: No single depth figure for USDC is correct; the curves disagree by asset

- Finding ID: `CG001-LQA-CG-05`
- Status: **OPEN**
- Category: `CG-05`
- Source report: `RPT-RBM003-USDC-0002-LQA`
- Evidence references: `EVI-56EFEE4BDD2940298B9C9A1C`
- Detail: Best single-venue execution at block 25662176, as a drop from the smallest size quoted: into WETH 0.00% at 10k, 0.35% at 1M, 38.41% at 100M, best route uniswap-v3-100 then v3-500. Into USDT 0.00%, 0.00%, 73.24%, best route uniswap-v3-100 throughout. Two facts follow. First, depth that is flat to 1M collapses by 100M on every route probed. Second, the two quote assets differ by roughly a factor of two at the largest size, so any headline depth or TVL number for USDC is wrong for at least one of them and cannot be corrected without saying which asset it is denominated in. Prices are deliberately not compared across the two: raw amounts in assets of different decimals are not a price comparison, and this profile has no numéraire to convert them.

### SEV-3: The reviewed figure is supply, not backing

- Finding ID: `CG002-CVA-CG-01`
- Status: **OPEN**
- Category: `CG-01`
- Source report: `RPT-RBM003-USDC-0002-CVA`
- Evidence references: `EVI-50627FC253727D641396BD22`
- Detail: totalSupply at block 25662176 is 49,578,553,356,366,347 raw units. decimals is read from the contract as 6, not assumed, giving 49,578,553,356.37 USDC; symbol reads USDC and name reads USD Coin. Every one of these is reproducible by anyone from the recorded query and height. That establishes how many units exist. It does not establish that each is redeemable for one dollar, which is the claim holders actually rely on and which lives entirely in off-chain attestations this profile cannot read. Recorded so that a reproduced supply figure is not taken for a reproduced backing figure.

### SEV-3: The predecessor's evidence spanned two block heights under one artefact version

- Finding ID: `CG003-MA-CG-01`
- Status: **OPEN**
- Category: `CG-01`
- Source report: `RPT-RBM003-USDC-0002-MA`
- Evidence references: `EVI-50627FC253727D641396BD22`
- Detail: RBM003-USDC-0001 declared artefact version 25660396 and registered symbol, name, decimals, totalSupply and upgradeability at that height -- then registered locks, liquidity and lp_composition at 25661826, 1,430 blocks later. Three of its eight evidence items described a state the other five never saw, and nothing in the record said so. The cause was procedural: three gates were run by hand after the evidence command rather than by it. This review pins every one of its nine items to 25662176 and the tooling now resolves the height once, so the defect is fixed rather than avoided. Raised against the predecessor because its decision is being superseded and the reason must be on the record.

### SEV-3: Nearly a third of addresses in the window share a first funder

- Finding ID: `CG001-ADA-CG-02`
- Status: **OPEN**
- Category: `CG-02`
- Source report: `RPT-RBM003-USDC-0002-ADA`
- Evidence references: `EVI-458DD31911B4EB70BC528335`
- Detail: Over blocks 25662117-25662176, 6,432 transfers involved 5,854 distinct addresses. 342 groups totalling 1,772 of those addresses share a first funder within the window -- 30.3% of everything seen. The largest group is 207 addresses funded by 0x00009d17b7b809e38f30892cff11650763b80000. Whether any group is one actor running many wallets or one exchange serving many customers is NOT determined by this evidence, and the first-funder-v1 method cannot distinguish them. The consequence is narrow and firm: any user, holder or active-address count drawn from this window overstates distinct actors by an amount this gate has bounded but not resolved. No such count appears anywhere in this review, and none may be added later on this evidence.

### SEV-3: A twelve-minute window is carrying a claim about a multi-year token

- Finding ID: `CG005-SR-CG-02`
- Status: **OPEN**
- Category: `CG-02`
- Source report: `RPT-RBM003-USDC-0002-SR`
- Evidence references: `EVI-458DD31911B4EB70BC528335`
- Detail: ADA walked 60 blocks and reported honestly that the finding describes those blocks and nothing outside them. The sceptical question is what the window is then doing in a Tier 3 review of USDC. Twelve minutes of transfers is a reasonable sample for detecting that clustering exists -- and it detected it, at 30.3% -- but it cannot support any statement about USDC's user base, concentration over time, or whether that funder is an exchange. The gate is answered. The subject is barely touched, and the decision should not let the first fact conceal the second.

### SEV-3: CG-03 is recorded as not assessed, not as answered

- Finding ID: `CG002-TKA-CG-03`
- Status: **OPEN**
- Category: `CG-03`
- Source report: `RPT-RBM003-USDC-0002-TKA`
- Evidence references: `EVI-23CEB7E3AD5C5D3299B231B0`
- Detail: The locks probe returned NO_LOCK_CONTRACT_IDENTIFIED and its own description states the registry is EMPTY and zero known lockers were searched. Burn addresses were probed and hold 53,911,272,789 units, 0.0001% of supply, which cannot return to circulation. No vesting or lock contract was searched for: top-holder enumeration is not available from JSON-RPC, and the registry ships empty because populating it from recollection would produce zero balances that render as 'no locks found'. The predecessor review left this as a reported gate result. This seat records it as NOT ASSESSED instead. For a centrally-issued stablecoin with no vesting schedule a locker search has little to find, but 'little to find' is a judgement about the subject and not a measurement, and the gate measured nothing.

### SEV-3: A Tier 3 review is complete in seats and short one gate

- Finding ID: `CG004-MA-CG-03`
- Status: **OPEN**
- Category: `CG-03`
- Source report: `RPT-RBM003-USDC-0002-MA`
- Evidence references: `EVI-23CEB7E3AD5C5D3299B231B0`
- Detail: All six specialist seats reported, which satisfies the Tier 3 quorum. But TKA recorded CG-03 as NOT ASSESSED with evidence_sufficiency INSUFFICIENT, because the locker registry is empty and zero lock contracts were searched. That is the correct call and this seat endorses it: a populated registry assembled from recollection would have produced a flattering non-result instead. The methodology point is that seat count and gate coverage are different things, and a Tier 3 badge asserts the first while a reader will hear the second. Five of six gates were answered on this artefact.

### SEV-3: What CG-05 did not reach: DAI, aggregators, and every V3 position

- Finding ID: `CG002-LQA-CG-05`
- Status: **OPEN**
- Category: `CG-05`
- Source report: `RPT-RBM003-USDC-0002-LQA`
- Evidence references: `EVI-7251ECB755BA8B462F971844`
- Detail: The quote set locked with this review's evidence was WETH and USDT. DAI was not in the default set at the time of the lock and was not probed; neither was any venue outside Uniswap V2 and V3, nor any aggregator that would split an order across several. LP composition was read for the V2 USDC/WETH pair 0xb4e16d0168e52d35cacd2c6185b44281ec28c9dc: LP supply 71,431,360,536,931,727, burned 0.0001%, locked 0%, project-held 0%, reported separately and never summed. Uniswap V3 positions are NFTs held by a position manager rather than fungible LP tokens, so they are neither counted nor excluded -- and since the best route at every size above was a V3 pool, the composition figures describe a venue that carried none of the quoted volume. The exit curve is therefore a single-route lower bound on available execution, not an estimate of what a real seller would pay.

### SEV-3: The exit figures are single-route and will be read as exit cost

- Finding ID: `CG004-SR-CG-05`
- Status: **OPEN**
- Category: `CG-05`
- Source report: `RPT-RBM003-USDC-0002-SR`
- Evidence references: `EVI-56EFEE4BDD2940298B9C9A1C`
- Detail: LQA quoted two assets rather than the predecessor's one, which is the improvement that finding asked for, and it immediately produced a two-fold disagreement between them at 100M. But every quote is one pool. A seller of that size splits across venues, assets and time, and would not pay 38% or 73%. The figures establish that no single route absorbs 100M without severe cost. They do not establish what leaving costs, and the two will be confused by any reader who meets the number without the sentence beside it.

### SEV-3: Reproducibility covers four of nine evidence items, not the review

- Finding ID: `CG003-RPA-CG-06`
- Status: **OPEN**
- Category: `CG-06`
- Source report: `RPT-RBM003-USDC-0002-RPA`
- Evidence references: `EVI-458DD31911B4EB70BC528335`
- Detail: Five of the nine registered items -- upgradeability, locks, liquidity, lp_composition and address_distinctness -- are assessments built from many reads, not single readings, and the resample path does not take them. They carry a block height and a described method, which makes them repeatable by someone re-running the connector, but not verified-reproduced by this gate. The distinction matters because CG-06 is the gate most likely to pass for the wrong reason: 4/4 is a true statement about a quarter of the evidence and would be a false statement about the review. The predecessor review reported 4/4 without this bound.

### SEV-4: The window is twelve minutes of a token that has existed for years

- Finding ID: `CG002-ADA-CG-02`
- Status: **OPEN**
- Category: `CG-02`
- Source report: `RPT-RBM003-USDC-0002-ADA`
- Evidence references: `EVI-458DD31911B4EB70BC528335`
- Detail: 60 blocks were walked in 10 ranges of 6, the provider's log cap, and covered_ranges shows the walk contiguous with no gap. That is roughly twelve minutes. The finding describes those blocks and no period outside them. Observation rather than defect: the bound is stated in the evidence itself and is a property of walking logs at a six-block cap, not an error. Recorded so the decision does not read as a characterisation of USDC's user base.

### SEV-4: The Tier 3 quorum is met and the predecessor's tiering finding is answered

- Finding ID: `CG002-MA-CG-04`
- Status: **OPEN**
- Category: `CG-04`
- Source report: `RPT-RBM003-USDC-0002-MA`
- Evidence references: `EVI-0CB098806DB562503B1408C3`
- Detail: RBM003-USDC-0001 was opened at Tier 2 and its MA seat found the subject required Tier 3, because RBM-003 section 8 makes anything behind an upgradeable proxy Tier 3 by construction and CAA established upgradeability. This review is seated at Tier 3 with all six specialists -- CVA, ADA, TKA, CAA, LQA, RPA -- and omitted_roles is empty. The two roles waived previously, ADA and LQA, were waived because their gates had no implementation; both are implemented and both answered here. The quorum requirement is met rather than waived. Observation, recorded so the supersession has a stated basis.

### SEV-4: Four of four resampled readings reproduced

- Finding ID: `CG002-RPA-CG-06`
- Status: **OPEN**
- Category: `CG-06`
- Source report: `RPT-RBM003-USDC-0002-RPA`
- Evidence references: `EVI-50627FC253727D641396BD22`
- Detail: symbol, name, decimals and totalSupply were re-run at block 25662176 through an archive-capable provider: four reproduced, zero diverged, zero unattempted. Each carries chain, block height, contract, query and content hash, so any third party can repeat them. Observation only; no defect asserted.

## Remediation

No remediation plans were recorded.

## Governance And Publication

- Decision status: **SIGNED**
- Publication: **RECORDED**

## Audit Verification

- Entries verified: 45
- Audit root hash: `sha256:4f8f47c9b2c702f9b902bc7722f170ed025b15a6e073fda2cd10c9b686480bce`
- Audit chain valid: **true**

## Limitations

- RBM-001 v2.0.0 remains RELEASE_CANDIDATE and cannot issue binding authority.
- Reviewer recommendations are non-binding and do not determine the machine outcome.
- This report contains only statements derived from the exported structured records.
