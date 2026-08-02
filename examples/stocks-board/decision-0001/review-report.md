# RBE-001 Review Report

> **ADVISORY DRY RUN:** RBM-001 is RELEASE_CANDIDATE. This report is non-binding and does not permit merge.

## Decision Summary

- Review: `RBM004-MOD-0001`
- Process status: **READY**
- Machine outcome: **FAIL**
- Binding: **false**
- Merge permitted: **false**
- Decision candidate: `DCA-FDA059D57C3BD59681C9492D`
- Frozen snapshot: `sha256:d9aa1c59cbd9325163db252239bc5488b33e3bdbee14d33b0998e1f3fc89edec`

The machine outcome is deterministic but is not itself governance authority.

## Target And Authority

- Target repository: `SEC EDGAR`
- Target artefact: `edgar:0000067347`
- Architecture authority: RBE-001 v1.1.0
- Methodology: `RBM-004` v1.0.0
- Methodology status: **RELEASE_CANDIDATE**
- Profile checksum: `sha256:0485c0ac581dabec94a74e91c21158f6b32cc8249b55b6f170360fbb063fd516`

## Decision Basis

FAIL was selected by RBM-DEC-002 from the frozen finding counts and substantive-evidence assessment.

Rules applied: `RBM-DEC-001`, `RBM-DEC-002`

Reason codes: `RBM-DEC-002`

## Evidence Register

### `EVI-1CD9975333891BC82ECCD4F5`

- Locator: `edgar:0000067347:sg01:total_liabilities`
- SHA-256: `sha256:08d8cbcdb94c4e4eee06e3b6d132ce475216c351b859eea6191b1740e90be6fc`
- Source tier: `T1`
- Description: sg01:total_liabilities for MOD (CIK 0000067347)

### `EVI-2014AC01DBF2EEBC623808A0`

- Locator: `edgar:0000067347:sg02:total_liabilities`
- SHA-256: `sha256:a65a6e4bc1ead280d6331af6d336bca21f8ed1a3db1b3a79521ea4096aef3aec`
- Source tier: `T1`
- Description: sg02:total_liabilities for MOD (CIK 0000067347)

### `EVI-21659D7BEC8F2387A0FE062D`

- Locator: `edgar:0000067347:sg02:net_income`
- SHA-256: `sha256:b9b870f7ae9e152e841023c2e66a36f065b323c2370f4565dee4c0da4c86a1b0`
- Source tier: `T1`
- Description: sg02:net_income for MOD (CIK 0000067347)

### `EVI-358DA7C1711273A7316D5985`

- Locator: `edgar:0000067347:sg01:revenue`
- SHA-256: `sha256:ceba8c1acd40f6b3e2520cf913233aa00595d7f04b11748fb430006a8e7aba88`
- Source tier: `T1`
- Description: sg01:revenue for MOD (CIK 0000067347)

### `EVI-3B68DBCED3EEA537A50588A2`

- Locator: `edgar:0000067347:sg02:long-term_debt`
- SHA-256: `sha256:94dcaaf4f525225122e7d78f300c4488e0b95ca89554edc2bd21f657910b2169`
- Source tier: `T1`
- Description: sg02:long-term_debt for MOD (CIK 0000067347)

### `EVI-54878FDE2A234BF72AA7B95E`

- Locator: `edgar:0000067347:sg03:dilution`
- SHA-256: `sha256:ac3802881b646bbf5c0f3a71dde4b5b76403faa751934fbe61951a446afbf0b4`
- Source tier: `T2`
- Description: sg03:dilution for MOD (CIK 0000067347)

### `EVI-569B0D63576950B5D6DCBF01`

- Locator: `edgar:0000067347:sg05:liquidity`
- SHA-256: `sha256:5043d307d803892c1ab1d98269f68d386d10cda6278ce80b0d2b19a4ad899b8e`
- Source tier: `T2`
- Description: sg05:liquidity for MOD (CIK 0000067347)

### `EVI-5D998D0D68330D6089165566`

- Locator: `edgar:0000067347:sg01:long-term_debt`
- SHA-256: `sha256:bb096197dbaf6874a2b366deb591db3009f22e07c287dadfe0f5f97e0751c2f2`
- Source tier: `T1`
- Description: sg01:long-term_debt for MOD (CIK 0000067347)

### `EVI-64922B69BC525DD6E52CCE7F`

- Locator: `edgar:0000067347:sg02:diluted_shares`
- SHA-256: `sha256:282cd8b712737505be9465aca6af14107319d7c151d34b66420f6600d7e02589`
- Source tier: `T1`
- Description: sg02:diluted_shares for MOD (CIK 0000067347)

### `EVI-78C3D0B39633701E909B0364`

- Locator: `edgar:0000067347:sg01:net_income`
- SHA-256: `sha256:39e4f4d1f601cbf3b7766f442c4677df7a94578f575b87a384aafa61a1f2e0b2`
- Source tier: `T1`
- Description: sg01:net_income for MOD (CIK 0000067347)

### `EVI-992F9BEDF8746DB7F430FAB1`

- Locator: `edgar:0000067347:sg02:tag:long-term_debt`
- SHA-256: `sha256:60fcbc6ab335c8dff9c38010dadf37636bc40084824734cfc64251445ca59405`
- Source tier: `T1`
- Description: sg02:tag:long-term_debt for MOD (CIK 0000067347)

### `EVI-AD4AC9CD18C7632A9AFDA275`

- Locator: `edgar:0000067347:sg01:shares_outstanding`
- SHA-256: `sha256:71858641b477b3f879398090b71ca5c94547547e790fadf39121bc3f2f5ce653`
- Source tier: `T1`
- Description: sg01:shares_outstanding for MOD (CIK 0000067347)

### `EVI-B72C1A21A7A65907B9E6CDFD`

- Locator: `edgar:0000067347:sg01:total_assets`
- SHA-256: `sha256:a41c87a0fcf04dac52c93a542b4101cf5ab2183a253b160883f66e8db7e2bce6`
- Source tier: `T1`
- Description: sg01:total_assets for MOD (CIK 0000067347)

### `EVI-BF37EDB74F4949FA09EBFCA9`

- Locator: `edgar:0000067347:sg02:tag:revenue`
- SHA-256: `sha256:0add829cbc4b64911903e96f0090e258e68d03074ca4dc3d47a946688aabaec7`
- Source tier: `T1`
- Description: sg02:tag:revenue for MOD (CIK 0000067347)

### `EVI-C7678C37A6A4DF9C64E88E13`

- Locator: `edgar:0000067347:sg01:diluted_shares`
- SHA-256: `sha256:603e585a701a03424ba5f2686bfa29a0b22f3934fe1723413614649c33e8b2bf`
- Source tier: `T1`
- Description: sg01:diluted_shares for MOD (CIK 0000067347)

### `EVI-E4E5EAF7AD4C1C5D4DF706A9`

- Locator: `edgar:0000067347:sg04:control`
- SHA-256: `sha256:0553d4ec6386acedd4c61965cd2d97e38283f8f13b0c99c6ff3ab1db0dd00332`
- Source tier: `T2`
- Description: sg04:control for MOD (CIK 0000067347)

### `EVI-F5E19EF3BE91E45EAFF1C420`

- Locator: `edgar:0000067347:sg02:total_assets`
- SHA-256: `sha256:fbcee4eb022cd5f4d7831b00ca6646264223f28b675a8e1087ee0dbcb6783270`
- Source tier: `T1`
- Description: sg02:total_assets for MOD (CIK 0000067347)

### `EVI-FEEA402AE1BF1B35332CD8AD`

- Locator: `edgar:0000067347:sg06:reproduction`
- SHA-256: `sha256:79e0393d70d0dd21ba79600a6e1b5f4694c98f62e477db24343dd86d76d4a1d6`
- Source tier: `T1`
- Description: sg06:reproduction for MOD (CIK 0000067347)

## Reviewer Reports

### `RPT-RBM004-MOD-0001-FVA`

- Assignment: `ASN-2B814FF4CB045B301B218024`
- Summary: Every headline figure is present and cited to an accession number. Two of them are only findable because the tag list is wide, and one describes a different date to the rest.
- Non-binding recommendation: **Corrective**
- Evidence references: `EVI-1CD9975333891BC82ECCD4F5`, `EVI-358DA7C1711273A7316D5985`, `EVI-5D998D0D68330D6089165566`, `EVI-78C3D0B39633701E909B0364`, `EVI-992F9BEDF8746DB7F430FAB1`, `EVI-AD4AC9CD18C7632A9AFDA275`, `EVI-B72C1A21A7A65907B9E6CDFD`, `EVI-C7678C37A6A4DF9C64E88E13`
- Human signature: `SIG-VERIFY-FVA-Ian McGuane-BASIS-standing-authority-2026-08-02-not-individually-read`

### `RPT-RBM004-MOD-0001-MA`

- Assignment: `ASN-3EEFA0A1BB238CD3C540DA2A`
- Summary: The review was conducted under the profile it names, at a tier its evidence supports, with its two unreached gates recorded rather than passed. One procedural weakness: the verification basis is honest and thin.
- Non-binding recommendation: **Monitoring**
- Evidence references: `EVI-569B0D63576950B5D6DCBF01`, `EVI-E4E5EAF7AD4C1C5D4DF706A9`, `EVI-FEEA402AE1BF1B35332CD8AD`
- Human signature: `SIG-VERIFY-MA-Ian McGuane-BASIS-standing-authority-2026-08-02-not-individually-read`

### `RPT-RBM004-MOD-0001-RIA`

- Assignment: `ASN-2E95B23A08D8548138031C56`
- Summary: Twenty reporting spans were filed at more than one value and two concepts changed XBRL tag. One revision is not a correction but a thousandfold unit change.
- Non-binding recommendation: **Corrective**
- Evidence references: `EVI-2014AC01DBF2EEBC623808A0`, `EVI-21659D7BEC8F2387A0FE062D`, `EVI-3B68DBCED3EEA537A50588A2`, `EVI-64922B69BC525DD6E52CCE7F`, `EVI-992F9BEDF8746DB7F430FAB1`, `EVI-BF37EDB74F4949FA09EBFCA9`, `EVI-F5E19EF3BE91E45EAFF1C420`
- Human signature: `SIG-VERIFY-RIA-Ian McGuane-BASIS-standing-authority-2026-08-02-not-individually-read`

### `RPT-RBM004-MOD-0001-RPA`

- Assignment: `ASN-DE30AD8287C2584A216843EA`
- Summary: Every figure is retrievable by anyone with no credential. The retrieval is reproducible only once the namespace is recorded, which it was not until this review produced a false statement about the filer.
- Non-binding recommendation: **Control**
- Evidence references: `EVI-569B0D63576950B5D6DCBF01`, `EVI-AD4AC9CD18C7632A9AFDA275`, `EVI-E4E5EAF7AD4C1C5D4DF706A9`, `EVI-FEEA402AE1BF1B35332CD8AD`
- Human signature: `SIG-VERIFY-RPA-Ian McGuane-BASIS-standing-authority-2026-08-02-not-individually-read`

### `RPT-RBM004-MOD-0001-SDA`

- Assignment: `ASN-E451C01E896BFFBA67D4EFE3`
- Summary: The current share count is reliable. The series it sits at the end of is not continuous, so dilution cannot be measured across the whole history from these filings.
- Non-binding recommendation: **Corrective**
- Evidence references: `EVI-54878FDE2A234BF72AA7B95E`, `EVI-64922B69BC525DD6E52CCE7F`, `EVI-AD4AC9CD18C7632A9AFDA275`, `EVI-C7678C37A6A4DF9C64E88E13`
- Human signature: `SIG-VERIFY-SDA-Ian McGuane-BASIS-standing-authority-2026-08-02-not-individually-read`

### `RPT-RBM004-MOD-0001-SR`

- Assignment: `ASN-86482FED6B314BEA62F4DCD6`
- Summary: The findings are sound and the conclusion they point at will be misread. Every one of them is about the filings' internal consistency; none is about the business.
- Non-binding recommendation: **Control**
- Evidence references: `EVI-21659D7BEC8F2387A0FE062D`, `EVI-E4E5EAF7AD4C1C5D4DF706A9`, `EVI-FEEA402AE1BF1B35332CD8AD`
- Human signature: `SIG-VERIFY-SR-Ian McGuane-BASIS-standing-authority-2026-08-02-not-individually-read`

## Findings

### SEV-2: The reported figure depends on how many tags were asked for

- Finding ID: `SG001-FVA-SG-01`
- Status: **OPEN**
- Category: `SG-01`
- Source report: `RPT-RBM004-MOD-0001-FVA`
- Evidence references: `EVI-5D998D0D68330D6089165566`
- Detail: Long-term debt is reported under LongTermDebtAndCapitalLeaseObligations. An earlier run of this evidence path asked only for LongTermDebtNoncurrent and LongTermDebt and returned a figure ten years stale, presented with the same confidence as a current one. The value now registered, 384,900,000 for the span ending 2026-03-31, is correct because the candidate list happened to be wide enough. That is a property of the query, not of the filing. A thin candidate list produces a confident wrong answer rather than a missing one, and nothing in the output distinguishes the two.

### SEV-2: Twenty spans carry more than one filed value, ten of them in net income alone

- Finding ID: `SG001-RIA-SG-02`
- Status: **OPEN**
- Category: `SG-02`
- Source report: `RPT-RBM004-MOD-0001-RIA`
- Evidence references: `EVI-21659D7BEC8F2387A0FE062D`
- Detail: Net income for 2010-04-01..2011-03-31 was filed at 5,233,000 in the 10-K of 2012-06-14 and at 5,200,000 in the 10-K of 2013-05-31. The quarter ending 2011-06-30 was filed three times at 13,125,000, 12,575,000 and 12,600,000. Total assets at 2011-03-31 moved from 916,939,000 to 917,742,000 between a 10-Q and the following 10-K. None of these is an error in the retrieval; all of them are the company having said two things. A series that silently takes the newest replaces what the company said with what it later said instead, and one that takes the first ignores a correction. Neither has been chosen here.

### SEV-2: Revenue and long-term debt each changed XBRL tag mid-life

- Finding ID: `SG002-RIA-SG-02`
- Status: **OPEN**
- Category: `SG-02`
- Source report: `RPT-RBM004-MOD-0001-RIA`
- Evidence references: `EVI-BF37EDB74F4949FA09EBFCA9`
- Detail: Revenue currently reports under RevenueFromContractWithCustomerExcludingAssessedTax and also carries data under SalesRevenueNet and Revenues. Long-term debt currently reports under LongTermDebtAndCapitalLeaseObligations and also carries data under three others. In both cases the history is split and neither tag alone is the whole series. A reader tracking one tag sees a series that stops without saying it has stopped, which is indistinguishable from a company that stopped reporting. NVIDIA's revenue was four years stale in an earlier run of this connector for exactly this reason.

### SEV-2: One revision is a thousandfold unit change, not a correction of magnitude

- Finding ID: `SG003-RIA-SG-02`
- Status: **OPEN**
- Category: `SG-02`
- Source report: `RPT-RBM004-MOD-0001-RIA`
- Evidence references: `EVI-64922B69BC525DD6E52CCE7F`
- Detail: Diluted shares for 2012-04-01..2012-06-30 were filed at 46,546 in the 10-Q of 2012-08-07 and at 46,500,000 in the 10-Q of 2013-08-01. These are the same quantity expressed in thousands and in units. Treated as a restatement it reads as a 99,900% revision; treated as identical it silently discards the question of which unit the surrounding filings used. Apple filed one fiscal year's share count at 899,213,000, then 899,213, then 6,294,494,000, and the same ambiguity applies. This is not a judgement about Modine: it is a statement that the pre-2013 share series cannot be read without deciding.

### SEV-2: Dilution is not measurable across the full series without choosing a unit

- Finding ID: `SG001-SDA-SG-03`
- Status: **OPEN**
- Category: `SG-03`
- Source report: `RPT-RBM004-MOD-0001-SDA`
- Evidence references: `EVI-64922B69BC525DD6E52CCE7F`
- Detail: Diluted shares stand at 53,800,000 for the year ending 2026-03-31 and shares outstanding at 52,815,785 as of 2026-05-22. Both are sound. The series behind them contains a span filed at both 46,546 and 46,500,000, and two further spans revised. Dilution computed from the earliest filed figure to the latest crosses that discontinuity and would report either a collapse or an expansion of three orders of magnitude depending on which side was taken. Dilution measured from 2013 forward is available; dilution measured across the whole history is not, from these filings alone.

### SEV-2: A wrong-namespace query rendered as a claim about the filer

- Finding ID: `SG001-RPA-SG-06`
- Status: **OPEN**
- Category: `SG-06`
- Source report: `RPT-RBM004-MOD-0001-RPA`
- Evidence references: `EVI-AD4AC9CD18C7632A9AFDA275`
- Detail: EntityCommonStockSharesOutstanding is a cover-page fact and lives in the dei taxonomy. Asked under us-gaap, which was the only namespace the connector knew, EDGAR returned 404 and the tool reported that Modine does not report a share count. Modine reports it in every filing. The output was a statement about which namespace was queried, presented as a statement about the filer, and nothing in it named the namespace so the error was unreadable from the result. This is the same failure as an empty proxy slot reading as 'not a proxy'. The connector now routes a prefixed tag to its own taxonomy and records which one answered.

### SEV-2: A FAIL here will be read as a verdict on the company

- Finding ID: `SG001-SR-SG-06`
- Status: **OPEN**
- Category: `SG-06`
- Source report: `RPT-RBM004-MOD-0001-SR`
- Evidence references: `EVI-21659D7BEC8F2387A0FE062D`
- Detail: This review is heading for FAIL on the strength of six SEV-2 findings. Read individually every one of them is about how the filings can be misread: a tag list that could have been thinner, a units change in 2012, a namespace the connector did not know, two gates never reached. Not one is an assertion that Modine is badly run, badly financed, or overpriced. The board has no view on any of those and cannot form one from what it read. But the outcome vocabulary is PASS, PASS_WITH_FINDINGS, FAIL and INSUFFICIENT_EVIDENCE, and a reader who sees FAIL beside a ticker will take it as a verdict on the ticker. The defect is not in the findings; it is that the artefact under review is a filing set and the outcome will be attached to a company.

### SEV-3: The share count describes 2026-05-22; every other figure describes 2026-03-31

- Finding ID: `SG002-FVA-SG-01`
- Status: **OPEN**
- Category: `SG-01`
- Source report: `RPT-RBM004-MOD-0001-FVA`
- Evidence references: `EVI-AD4AC9CD18C7632A9AFDA275`
- Detail: Shares outstanding is 52,815,785, taken from dei:EntityCommonStockSharesOutstanding, which is a cover-page fact stated as of a date near filing. Revenue, net income, assets, liabilities and debt all describe the fiscal year ending 2026-03-31. Any per-share figure computed across the two measures the fifty-two day gap as well as the business. The figures are individually correct and the composition of any two of them is not.

### SEV-3: Every report was verified on a standing authority, not on a reading

- Finding ID: `SG001-MA-SG-06`
- Status: **OPEN**
- Category: `SG-06`
- Source report: `RPT-RBM004-MOD-0001-MA`
- Evidence references: `EVI-FEEA402AE1BF1B35332CD8AD`
- Detail: All six reports carry human_signature_ref recording verification by Ian McGuane with basis standing-authority-2026-08-02-not-individually-read. That basis is accurate and it is the weakest admissible one. The predecessor crypto review was verified on a summary reading, which was also weak and was stronger than this. The record is not defective — it says exactly what happened, which is the whole purpose of the basis field — but a board whose every report is verified without being read has a human in the loop in name. This is recorded so that the strength of the verification travels with the decision rather than being inferred from the presence of a signature.

### SEV-3: Tier 2 is correctly claimed and Tier 3 correctly refused

- Finding ID: `SG002-MA-SG-06`
- Status: **OPEN**
- Category: `SG-06`
- Source report: `RPT-RBM004-MOD-0001-MA`
- Evidence references: `EVI-569B0D63576950B5D6DCBF01`
- Detail: The initiation claims Tier 2 with four specialists, which meets the tier_2 quorum of four, and states that Tier 3 is not claimed because SG-04 and SG-05 are unreached. Both are correct against the profile as loaded. This is recorded as a finding rather than left implicit because the predecessor crypto review had to be re-run as RBM003-USDC-0002 for claiming a tier its evidence did not support, and the cheapest place to catch that is at initiation. It was caught here at initiation.

### SEV-3: Two of six gates were not reached, and the reason is recorded

- Finding ID: `SG002-RPA-SG-06`
- Status: **OPEN**
- Category: `SG-06`
- Source report: `RPT-RBM004-MOD-0001-RPA`
- Evidence references: `EVI-E4E5EAF7AD4C1C5D4DF706A9`
- Detail: SG-04 and SG-05 are registered NOT_ASSESSED. Control and related-party disclosure is narrative text in the 10-K body and the proxy statement, and this connector reads XBRL only; exit liquidity needs traded volume and depth, and no market data source is configured. Both are statements about coverage. Neither is a finding that the filer has no related-party transactions or that the position is liquid, and a reader who takes silence for absence would conclude both.

### SEV-3: Four of six findings describe the review rather than the subject

- Finding ID: `SG002-SR-SG-06`
- Status: **OPEN**
- Category: `SG-06`
- Source report: `RPT-RBM004-MOD-0001-SR`
- Evidence references: `EVI-FEEA402AE1BF1B35332CD8AD`
- Detail: SG001-FVA, SG001-RPA, SG002-RPA and this one are about the retrieval, the namespace, the coverage and the reading. Only the restatement and unit findings are about what Modine filed. The same imbalance was recorded in the crypto board, where nine of sixteen findings described the review's own limits, and it was left open pending the mandate artifact. The mandate now exists. This review is the second instance and the question should stop being deferred: scope limits and subject defects are different things carrying the same severity scale, and a decision engine that counts them together will FAIL a clean subject that was read narrowly.

## Remediation

No remediation plans were recorded.

## Governance And Publication

- Decision status: **SIGNED**
- Publication: **RECORDED**

## Audit Verification

- Entries verified: 45
- Audit root hash: `sha256:89283fda5afcd171f9d8e97f7abb97b693b196091a2678bd83a01bdd9b7a314c`
- Audit chain valid: **true**

## Limitations

- RBM-001 v2.0.0 remains RELEASE_CANDIDATE and cannot issue binding authority.
- Reviewer recommendations are non-binding and do not determine the machine outcome.
- This report contains only statements derived from the exported structured records.
