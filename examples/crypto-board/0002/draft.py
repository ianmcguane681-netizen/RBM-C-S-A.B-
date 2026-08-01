"""Draft the eight seat reports for RBM003-USDC-0002.

Every figure here is copied from evidence registered at block 25,662,176 and nowhere else.
Drafts only: `human_verified` is false in all of them, and stays false until a named human
runs `board verify --by`.
"""
import json
from pathlib import Path

OUT = Path("examples/crypto-board/0002")
OUT.mkdir(parents=True, exist_ok=True)

REVIEW = "RBM003-USDC-0002"
BLOCK = "25662176"
DATE = "2026-08-01T20:30:00Z"

E = {
    "upgradeability": "EVI-0CB098806DB562503B1408C3",
    "locks": "EVI-23CEB7E3AD5C5D3299B231B0",
    "distinctness": "EVI-458DD31911B4EB70BC528335",
    "totalSupply": "EVI-50627FC253727D641396BD22",
    "liquidity": "EVI-56EFEE4BDD2940298B9C9A1C",
    "lp_composition": "EVI-7251ECB755BA8B462F971844",
    "name": "EVI-72A87795F70E6FDEBFBA642A",
    "symbol": "EVI-8654949EA26EFD946CFA7372",
    "decimals": "EVI-FA2F424BC61FD26539BA3851",
}
ALL_EVIDENCE = sorted(E.values())

SPEC = {
    "MA": ("RBS-001", "1.0.0"), "CVA": ("RBS-002", "1.0.0"), "ADA": ("RBS-003", "1.0.0"),
    "TKA": ("RBS-004", "1.0.0"), "CAA": ("RBS-005", "1.0.0"), "LQA": ("RBS-006", "1.0.0"),
    "RPA": ("RBS-007", "1.0.0"), "SR": ("RBS-008", "1.0.0"),
}


def finding(fid, role, gate, severity, title, detail, evidence, tier, remediation):
    return {
        "schema_version": "1.0.0", "finding_id": fid, "review_id": REVIEW,
        "reviewer": f"agent:{role.lower()}", "reviewer_role": role,
        "artefact_version": BLOCK, "date_raised": DATE, "severity": severity,
        "spec_reference": f"{SPEC[role][0]} section 7 ({gate})",
        "title": title, "detail": detail,
        "evidence_tier": tier, "evidence_reference": evidence,
        "ai_assistance": {"used": True, "description": "agent seat review",
                          "human_verified": False},
        "status": "OPEN", "remediation_requirement": remediation,
        "target_resolution_date": "2026-09-15", "closure": None,
    }


def report(role, summary, recommendation, findings, sufficiency="SUFFICIENT", missing=()):
    spec, version = SPEC[role]
    payload = {
        "reviewer_role": role, "summary": summary, "recommendation": recommendation,
        "evidence_reference_ids": ALL_EVIDENCE,
        "finding_categories": {
            f["finding_id"]: f["spec_reference"].split("(")[1].rstrip(")") for f in findings
        },
        "findings": findings,
        "report": {
            "schema_version": "1.0.0", "report_id": f"RPT-{REVIEW}-{role}",
            "review_id": REVIEW, "reviewer": f"agent:{role.lower()}", "reviewer_role": role,
            "reviewer_spec_id": spec, "reviewer_spec_version": version,
            "artefact_sha": BLOCK,
            "finding_ids": [f["finding_id"] for f in findings],
            "evidence_sufficiency": sufficiency, "missing_evidence": list(missing),
            "ai_assistance": {"used": True, "human_verified": False,
                              "method": f"provena-chain-b/{role}-002"},
            "human_signature_ref": f"SIG-PENDING-{role}",
        },
    }
    (OUT / f"report-{role}.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(f"  {role:4} {len(findings)} finding(s)  [{sufficiency}]")


# ---------------------------------------------------------------- CVA, CG-01
report(
    "CVA",
    "Supply, symbol, name and decimals reproduce from contract state at the reviewed "
    "block. What a unit is worth is not a chain fact and no gate here reaches it.",
    "Monitoring",
    [finding(
        "CG001-CVA-CG-01", "CVA", "CG-01", "SEV-3",
        "The reviewed figure is supply, not backing",
        "totalSupply at block 25662176 is 49,578,553,356,366,347 raw units. decimals is "
        "read from the contract as 6, not assumed, giving 49,578,553,356.37 USDC; symbol "
        "reads USDC and name reads USD Coin. Every one of these is reproducible by anyone "
        "from the recorded query and height. That establishes how many units exist. It "
        "does not establish that each is redeemable for one dollar, which is the claim "
        "holders actually rely on and which lives entirely in off-chain attestations this "
        "profile cannot read. Recorded so that a reproduced supply figure is not taken for "
        "a reproduced backing figure.",
        E["totalSupply"], "T1",
        "State in the decision that CG-01 verified supply and that backing was out of scope.",
    )],
)

# ---------------------------------------------------------------- ADA, CG-02
report(
    "ADA",
    "Address activity was walked across a stated 60-block window with no gap. A third of "
    "the addresses seen share a first funder, so an address count in this window is not a "
    "count of actors.",
    "Monitoring",
    [
        finding(
            "CG001-ADA-CG-02", "ADA", "CG-02", "SEV-3",
            "Nearly a third of addresses in the window share a first funder",
            "Over blocks 25662117-25662176, 6,432 transfers involved 5,854 distinct "
            "addresses. 342 groups totalling 1,772 of those addresses share a first funder "
            "within the window -- 30.3% of everything seen. The largest group is 207 "
            "addresses funded by 0x00009d17b7b809e38f30892cff11650763b80000. Whether any "
            "group is one actor running many wallets or one exchange serving many customers "
            "is NOT determined by this evidence, and the first-funder-v1 method cannot "
            "distinguish them. The consequence is narrow and firm: any user, holder or "
            "active-address count drawn from this window overstates distinct actors by an "
            "amount this gate has bounded but not resolved. No such count appears anywhere "
            "in this review, and none may be added later on this evidence.",
            E["distinctness"], "T2",
            "Any figure described as users, holders or actives must either exclude these "
            "clusters or carry the cluster share beside it. Resolving whether a cluster is "
            "one actor requires evidence this gate does not produce.",
        ),
        finding(
            "CG002-ADA-CG-02", "ADA", "CG-02", "SEV-4",
            "The window is twelve minutes of a token that has existed for years",
            "60 blocks were walked in 10 ranges of 6, the provider's log cap, and "
            "covered_ranges shows the walk contiguous with no gap. That is roughly twelve "
            "minutes. The finding describes those blocks and no period outside them. "
            "Observation rather than defect: the bound is stated in the evidence itself "
            "and is a property of walking logs at a six-block cap, not an error. Recorded "
            "so the decision does not read as a characterisation of USDC's user base.",
            E["distinctness"], "T2",
            "No remediation. The window is stated in the evidence and must remain stated "
            "in anything quoting it.",
        ),
    ],
)

# ---------------------------------------------------------------- TKA, CG-03
report(
    "TKA",
    "CG-03 is NOT ASSESSED for this review. The locker registry is empty, so zero lock "
    "contracts were searched, and this seat declines to present a non-result as a gate "
    "result.",
    "Reject",
    [finding(
        "CG001-TKA-CG-03", "TKA", "CG-03", "SEV-3",
        "CG-03 is recorded as not assessed, not as answered",
        "The locks probe returned NO_LOCK_CONTRACT_IDENTIFIED and its own description "
        "states the registry is EMPTY and zero known lockers were searched. Burn addresses "
        "were probed and hold 53,911,272,789 units, 0.0001% of supply, which cannot return "
        "to circulation. No vesting or lock contract was searched for: top-holder "
        "enumeration is not available from JSON-RPC, and the registry ships empty because "
        "populating it from recollection would produce zero balances that render as 'no "
        "locks found'. The predecessor review left this as a reported gate result. This "
        "seat records it as NOT ASSESSED instead. For a centrally-issued stablecoin with no "
        "vesting schedule a locker search has little to find, but 'little to find' is a "
        "judgement about the subject and not a measurement, and the gate measured nothing.",
        E["locks"], "T1",
        "Record CG-03 as not assessed in the decision. Do not populate the registry to make "
        "the gate appear answered; a verified locker address is the only thing that changes "
        "this, and none was available.",
    )],
    sufficiency="INSUFFICIENT",
    missing=["Verified lock contract addresses, or top-holder enumeration via an indexer"],
)

# ---------------------------------------------------------------- CAA, CG-04
report(
    "CAA",
    "USDC is upgradeable behind a transparent proxy whose EIP-1967 slots are empty, and "
    "mint, pause and blacklist authority sit with named addresses.",
    "Reject",
    [
        finding(
            "CG001-CAA-CG-04", "CAA", "CG-04", "SEV-2",
            "USDC is upgradeable and the EIP-1967 slots are empty",
            "At block 25662176 the three EIP-1967 slots read empty and implementation() "
            "reverts, which together look exactly like a non-upgradeable contract. The "
            "pre-EIP-1967 OpenZeppelin slots are populated: implementation "
            "0x43506849d7c04f9138d1a2050bbf3a0c054402dd, admin "
            "0x807a96288a1a408dbc13de2b1d087d10356395d2. The proxy is transparent, so it "
            "routes non-admin callers to the implementation and the function probe reverts "
            "rather than answering. Any assessment checking only EIP-1967 would report one "
            "of the largest tokens in existence as immutable. The admin can replace the "
            "implementation entirely, so every behaviour verified by every other gate in "
            "this review holds only while that admin chooses not to act.",
            E["upgradeability"], "T2",
            "Record upgradeability, the admin address, and that a holder's guarantees "
            "survive only as long as the admin chooses not to replace the implementation.",
        ),
        finding(
            "CG002-CAA-CG-04", "CAA", "CG-04", "SEV-2",
            "Mint, pause and blacklist authority sit with named addresses",
            "owner() resolves to 0xfcb19e6a322b27c06842a71e8c725399f049ae3a and "
            "masterMinter() to 0xe982615d461dd5cd06575bbea87624fda4e3de17. paused() answers "
            "false, which establishes that a pause function exists and is currently off "
            "rather than that none exists. admin() and implementation() both revert for "
            "this caller, which is the transparent proxy behaving correctly and not an "
            "absence of those functions. Together these mean supply, transferability and "
            "individual balances are subject to decisions by parties other than the holder. "
            "The supply figure this review reproduces is therefore a measurement at a "
            "height, not a bound.",
            E["upgradeability"], "T2",
            "Enumerate every privileged function with its controlling address and, where "
            "multisig, its threshold. Absent that, no claim of trustlessness can be made.",
        ),
    ],
)

# ---------------------------------------------------------------- LQA, CG-05
report(
    "LQA",
    "Exit cost was quoted at three sizes into two assets across ten venues. Depth is deep "
    "at a million and falls apart at a hundred million, and the two assets disagree by "
    "roughly a factor of two about how badly.",
    "Reject",
    [
        finding(
            "CG001-LQA-CG-05", "LQA", "CG-05", "SEV-2",
            "No single depth figure for USDC is correct; the curves disagree by asset",
            "Best single-venue execution at block 25662176, as a drop from the smallest "
            "size quoted: into WETH 0.00% at 10k, 0.35% at 1M, 38.41% at 100M, best route "
            "uniswap-v3-100 then v3-500. Into USDT 0.00%, 0.00%, 73.24%, best route "
            "uniswap-v3-100 throughout. Two facts follow. First, depth that is flat to 1M "
            "collapses by 100M on every route probed. Second, the two quote assets differ "
            "by roughly a factor of two at the largest size, so any headline depth or TVL "
            "number for USDC is wrong for at least one of them and cannot be corrected "
            "without saying which asset it is denominated in. Prices are deliberately not "
            "compared across the two: raw amounts in assets of different decimals are not a "
            "price comparison, and this profile has no numéraire to convert them.",
            E["liquidity"], "T1",
            "Any depth or liquidity figure must state the quote asset and the size it was "
            "measured at. A single number without both is not a depth figure.",
        ),
        finding(
            "CG002-LQA-CG-05", "LQA", "CG-05", "SEV-3",
            "What CG-05 did not reach: DAI, aggregators, and every V3 position",
            "The quote set locked with this review's evidence was WETH and USDT. DAI was "
            "not in the default set at the time of the lock and was not probed; neither "
            "was any venue outside Uniswap V2 and V3, nor any aggregator that would split "
            "an order across several. LP composition was read for the V2 USDC/WETH pair "
            "0xb4e16d0168e52d35cacd2c6185b44281ec28c9dc: LP supply 71,431,360,536,931,727, "
            "burned 0.0001%, locked 0%, project-held 0%, reported separately and never "
            "summed. Uniswap V3 positions are NFTs held by a position manager rather than "
            "fungible LP tokens, so they are neither counted nor excluded -- and since the "
            "best route at every size above was a V3 pool, the composition figures describe "
            "a venue that carried none of the quoted volume. The exit curve is therefore a "
            "single-route lower bound on available execution, not an estimate of what a "
            "real seller would pay.",
            E["lp_composition"], "T1",
            "State in the decision that exit cost is single-route and that V3 composition "
            "is unreached. A realistic exit estimate needs order splitting across venues "
            "and assets, which this gate does not perform.",
        ),
    ],
)

# ---------------------------------------------------------------- RPA, CG-06
report(
    "RPA",
    "Every reading that can be resampled was resampled and reproduced. That covers four of "
    "the nine evidence items; the other five are assessments rather than single readings.",
    "Accept",
    [
        finding(
            "CG001-RPA-CG-06", "RPA", "CG-06", "SEV-4",
            "Four of four resampled readings reproduced",
            "symbol, name, decimals and totalSupply were re-run at block 25662176 through "
            "an archive-capable provider: four reproduced, zero diverged, zero unattempted. "
            "Each carries chain, block height, contract, query and content hash, so any "
            "third party can repeat them. Observation only; no defect asserted.",
            E["totalSupply"], "T1",
            "No remediation required.",
        ),
        finding(
            "CG002-RPA-CG-06", "RPA", "CG-06", "SEV-3",
            "Reproducibility covers four of nine evidence items, not the review",
            "Five of the nine registered items -- upgradeability, locks, liquidity, "
            "lp_composition and address_distinctness -- are assessments built from many "
            "reads, not single readings, and the resample path does not take them. They "
            "carry a block height and a described method, which makes them repeatable by "
            "someone re-running the connector, but not verified-reproduced by this gate. "
            "The distinction matters because CG-06 is the gate most likely to pass for the "
            "wrong reason: 4/4 is a true statement about a quarter of the evidence and "
            "would be a false statement about the review. The predecessor review reported "
            "4/4 without this bound.",
            E["distinctness"], "T2",
            "Either extend resampling to re-run assessment findings and compare their "
            "described output, or state on every CG-06 result which items it covered.",
        ),
    ],
)

# ---------------------------------------------------------------- SR
report(
    "SR",
    "Six gates were seated and five answered. All of them are chain facts, and the claim a "
    "USDC holder relies on is not a chain fact.",
    "Reject",
    [
        finding(
            "CG001-SR-CG-01", "SR", "CG-01", "SEV-2",
            "The board verified what is checkable and the risk is elsewhere",
            "This review is materially stronger than its predecessor: six specialists "
            "rather than four, every reading at one block height rather than two, and two "
            "gates answered live that had no implementation before. None of that touches "
            "the question. Every gate in RBM-003 examines chain state. The claim a USDC "
            "holder relies on is that each unit is redeemable for one dollar, and that "
            "rests on reserves held by a company, attested by an auditor, under a "
            "regulator, none of which is on any chain. A reader seeing a Tier 3 review with "
            "six specialists may conclude the asset was assessed. It was not; its principal "
            "risk was never in scope, and running the review more thoroughly has not "
            "changed that by one inch. This is a limit of the profile, not of the execution.",
            E["totalSupply"], "T1",
            "RBM-003 must state in its scope section that it assesses on-chain claims only, "
            "and any decision on a fiat-backed token must carry that limit on its face.",
        ),
        finding(
            "CG002-SR-CG-05", "SR", "CG-05", "SEV-3",
            "The exit figures are single-route and will be read as exit cost",
            "LQA quoted two assets rather than the predecessor's one, which is the "
            "improvement that finding asked for, and it immediately produced a two-fold "
            "disagreement between them at 100M. But every quote is one pool. A seller of "
            "that size splits across venues, assets and time, and would not pay 38% or 73%. "
            "The figures establish that no single route absorbs 100M without severe cost. "
            "They do not establish what leaving costs, and the two will be confused by any "
            "reader who meets the number without the sentence beside it.",
            E["liquidity"], "T1",
            "Label the curve single-route wherever it appears. Estimating a real exit needs "
            "order splitting this profile does not implement.",
        ),
        finding(
            "CG003-SR-CG-02", "SR", "CG-02", "SEV-3",
            "A twelve-minute window is carrying a claim about a multi-year token",
            "ADA walked 60 blocks and reported honestly that the finding describes those "
            "blocks and nothing outside them. The sceptical question is what the window is "
            "then doing in a Tier 3 review of USDC. Twelve minutes of transfers is a "
            "reasonable sample for detecting that clustering exists -- and it detected it, "
            "at 30.3% -- but it cannot support any statement about USDC's user base, "
            "concentration over time, or whether that funder is an exchange. The gate is "
            "answered. The subject is barely touched, and the decision should not let the "
            "first fact conceal the second.",
            E["distinctness"], "T2",
            "State the window on the face of any CG-02 result. A characterisation of the "
            "holder base needs an indexer and a period measured in months.",
        ),
    ],
)

# ---------------------------------------------------------------- MA
report(
    "MA",
    "The tiering defect that this review exists to answer is answered. Two further "
    "methodology defects are raised, one inherited from the predecessor and one live here.",
    "Monitoring",
    [
        finding(
            "CG001-MA-CG-04", "MA", "CG-04", "SEV-4",
            "The Tier 3 quorum is met and the predecessor's tiering finding is answered",
            "RBM003-USDC-0001 was opened at Tier 2 and its MA seat found the subject "
            "required Tier 3, because RBM-003 section 8 makes anything behind an upgradeable "
            "proxy Tier 3 by construction and CAA established upgradeability. This review is "
            "seated at Tier 3 with all six specialists -- CVA, ADA, TKA, CAA, LQA, RPA -- "
            "and omitted_roles is empty. The two roles waived previously, ADA and LQA, were "
            "waived because their gates had no implementation; both are implemented and "
            "both answered here. The quorum requirement is met rather than waived. "
            "Observation, recorded so the supersession has a stated basis.",
            E["upgradeability"], "T2",
            "No remediation. This finding records that the predecessor's SEV-2 is "
            "discharged by this review rather than closed by assertion.",
        ),
        finding(
            "CG002-MA-CG-01", "MA", "CG-01", "SEV-3",
            "The predecessor's evidence spanned two block heights under one artefact version",
            "RBM003-USDC-0001 declared artefact version 25660396 and registered symbol, "
            "name, decimals, totalSupply and upgradeability at that height -- then "
            "registered locks, liquidity and lp_composition at 25661826, 1,430 blocks "
            "later. Three of its eight evidence items described a state the other five "
            "never saw, and nothing in the record said so. The cause was procedural: three "
            "gates were run by hand after the evidence command rather than by it. This "
            "review pins every one of its nine items to 25662176 and the tooling now "
            "resolves the height once, so the defect is fixed rather than avoided. Raised "
            "against the predecessor because its decision is being superseded and the "
            "reason must be on the record.",
            E["totalSupply"], "T1",
            "The superseding decision must record that RBM003-USDC-0001 carried a split "
            "evidence height, so that anyone reading the earlier decision finds the reason "
            "it was replaced.",
        ),
        finding(
            "CG003-MA-CG-03", "MA", "CG-03", "SEV-3",
            "A Tier 3 review is complete in seats and short one gate",
            "All six specialist seats reported, which satisfies the Tier 3 quorum. But TKA "
            "recorded CG-03 as NOT ASSESSED with evidence_sufficiency INSUFFICIENT, because "
            "the locker registry is empty and zero lock contracts were searched. That is the "
            "correct call and this seat endorses it: a populated registry assembled from "
            "recollection would have produced a flattering non-result instead. The "
            "methodology point is that seat count and gate coverage are different things, "
            "and a Tier 3 badge asserts the first while a reader will hear the second. Five "
            "of six gates were answered on this artefact.",
            E["locks"], "T1",
            "The decision must state that CG-03 was not assessed. RBM-003 should say "
            "whether a tier can be claimed with a gate unassessed, which it currently does "
            "not address.",
        ),
    ],
)

print(f"\nWritten to {OUT}/")
