"""A front door for the review board.

The runtime has been complete and tested for a while, and no review had ever been
run through it, because sitting on the board meant writing Python. The existing
`rbe_runtime` CLI only inspects reviews after the fact - version, validate,
verify, export. Nothing convened one.

These commands convene one: open a review, staff it with agent seats, register the
material under review, take the seats' reports, show the challenge sheets, and
ratify and publish. Every command prints what is needed next, so the workflow is
discoverable rather than memorised.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from board.challenges import (
    SEVERITY_EFFECT,
    ChallengeSheet,
    NoChallenge,
    render_review,
    summarise,
)
from board.seats import (
    AgentSeat,
    board_health,
    require_independent_seats,
    shared_model_note,
)
from rbe_runtime.authority import AuthorityBundle
from rbe_runtime.errors import RBEError
from rbe_runtime.service import RBERuntime

DEFAULT_DB = Path("data/review_board.sqlite3")


def _runtime(args: argparse.Namespace) -> RBERuntime:
    """Open the review store under the named methodology profile.

    The profile is a per-invocation choice rather than a stored one, so every command
    in a review must name the same profile. That is deliberate: a review half-conducted
    under research rules and half under engineering rules would be neither, and
    silently defaulting the second half is exactly how that happens.
    """

    profile_id = getattr(args, "profile", None)
    authority = AuthorityBundle.load(profile_id=profile_id) if profile_id else None
    return RBERuntime(args.database, authority=authority)


def _load(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _print_next(step: str) -> None:
    print(f"\nNext: {step}")


def cmd_seats(args: argparse.Namespace) -> int:
    """Show the configured agent seats and check they are independent."""

    seats = [
        AgentSeat(
            role=item["role"],
            model=item["model"],
            instruction_version=item["instruction_version"],
            name=item.get("name", ""),
        )
        for item in _load(args.seats)
    ]
    require_independent_seats(seats)
    print(f"{len(seats)} agent seat(s), independence checks passed:\n")
    for seat in seats:
        blind = "  [blind to proposed outcome]" if seat.is_blind else ""
        print(f"  {seat.role:5} {seat.actor:22} {seat.method()}{blind}")
    note = shared_model_note(seats)
    if note:
        print(f"\n  Recorded: {note}")
    _print_next("board open --initiation <file> to convene the review")
    return 0


def cmd_open(args: argparse.Namespace) -> int:
    """Convene a review from an initiation record."""

    runtime = _runtime(args)
    initiation = _load(args.initiation)
    runtime.initiate_review(
        initiation, actor=initiation["board_chair"], idempotency_key=f"open-{initiation['review_id']}"
    )
    print(f"Review {initiation['review_id']} opened in {runtime.repository.get_session(initiation['review_id']).status}.")
    for assignment in runtime.repository.list_assignments(initiation["review_id"]):
        print(f"  seat {assignment.reviewer_role:5} -> {assignment.reviewer_actor}")
    _print_next("board evidence --bundle <proof bundle> to register what is under review")
    return 0


def cmd_evidence(args: argparse.Namespace) -> int:
    """Register a Golden Study proof bundle as the material under review."""

    from study_bridge import StudyBundle, ingest_study_bundle

    runtime = _runtime(args)
    bundle = StudyBundle.load(args.bundle)
    result = ingest_study_bundle(runtime, args.review, bundle, actor=args.actor)
    print(f"Registered {len(result.reference_ids)} file(s) from {bundle.study_id} run {bundle.run_id}.")
    print(f"  bundle root hash: {bundle.bundle_root_hash}")
    print(f"  code commit:      {bundle.code_commit_hash}")
    _print_next("board advance --to EVIDENCE_LOCKED, then ASSIGNMENT")
    return 0


def cmd_commit_evidence(args: argparse.Namespace) -> int:
    """Register source files at a named commit as the material under review.

    An engineering review's artefact is a `GIT_COMMIT`, which is where engineering
    review is easier than research review rather than harder: the thing under review is
    exactly identified, immutable, and independently retrievable by anyone with the
    repository.

    Files are read with `git show <commit>:<path>` rather than from the working tree.
    Reviewing the checkout would review whatever happened to be on disk, and the commit
    named in the record would be decoration.
    """

    import subprocess

    runtime = _runtime(args)
    repo = Path(args.repo).resolve()

    def _git(*command: str) -> bytes:
        result = subprocess.run(
            ["git", "-C", str(repo), *command], capture_output=True, check=False
        )
        if result.returncode != 0:
            raise RBEError(
                "RBE_EVIDENCE_INCOMPLETE",
                f"git {' '.join(command)} failed: {result.stderr.decode().strip()}",
                "RBE-ES-ORC-007",
            )
        return result.stdout

    resolved = _git("rev-parse", args.commit).decode().strip()
    print(f"Artefact commit {resolved}")

    registered = 0
    for path in args.path:
        content = _git("show", f"{resolved}:{path}")
        runtime.register_evidence(
            args.review,
            locator=f"{args.repo}@{resolved}:{path}",
            content=content,
            description=f"{path} at commit {resolved[:12]}",
            source_tier="T2",
            provenance={
                "kind": "GIT_COMMIT",
                "repository": args.repo,
                "commit": resolved,
                "path": path,
                "retrieved_by": "git show",
            },
            actor=args.actor,
            idempotency_key=f"commit-{resolved[:12]}-{path}",
        )
        registered += 1
        print(f"  T2  {path} ({len(content)} bytes)")

    if args.test_log:
        log = Path(args.test_log).read_bytes()
        runtime.register_evidence(
            args.review,
            locator=f"{args.repo}@{resolved}:test-run",
            content=log,
            description=f"Recorded test run at commit {resolved[:12]}",
            source_tier="T1",
            # T1 because it is a command and its output, not a description of one.
            # EG-06 exists because a quoted test count is a claim, not a measurement.
            provenance={
                "kind": "TEST_RUN",
                "repository": args.repo,
                "commit": resolved,
                "command": args.test_command or "unrecorded",
            },
            actor=args.actor,
            idempotency_key=f"commit-{resolved[:12]}-testrun",
        )
        registered += 1
        print(f"  T1  test run ({len(log)} bytes)")

    print(f"\nRegistered {registered} item(s) of evidence.")
    _print_next("board advance --to EVIDENCE_LOCKED, then ASSIGNMENT")
    return 0


# Exit sizes for CG-05, in WHOLE TOKENS, scaled at runtime by the decimals read from the
# contract. Four orders of magnitude, because a single quote cannot distinguish a deep pool
# from a shallow one that happens to price small trades well, and that distinction is the
# entire question the gate asks.
#
# Whole tokens rather than a currency amount: converting to dollars needs a price this
# profile has no oracle for, and inventing one is the same overreach as comparing raw
# amounts across quote assets. The basis is stated in the evidence provenance.
EXIT_SIZES_IN_TOKENS = (10_000, 1_000_000, 100_000_000)


def cmd_chain_evidence(args: argparse.Namespace) -> int:
    """Register chain state as evidence, pinned to a finalized block height.

    The chain analogue of `commit-evidence`. A contract at a block height is the same
    class of artefact as a commit: immutable, independently retrievable, and verifiable by
    anyone who was not present when it was read.

    Reads at `finalized` rather than `latest`, so evidence cannot be reorged out from
    under a record already made.

    **Every reading pins to one height.** The first crypto review registered identity and
    upgradeability at block 25,660,396 and locks, liquidity and composition at 25,661,826 --
    1,430 blocks later -- while declaring a single artefact version. Half the evidence
    described a state the other half never saw, and nothing in the record said so. The
    height is resolved once here and passed to every probe.

    All six gates are registered from this one command. Three of them used to be run by
    hand afterwards, which is how the split above happened in the first place.
    """

    from connectors.chain import ChainClient, best_for
    from connectors import chain_queries as queries
    from connectors.chain_clustering import METHOD, address_distinctness
    from connectors.chain_liquidity import QUOTE_TOKENS, exit_cost, pool_ownership, v2_pair
    from connectors.chain_locks import BURN_ADDRESSES, lock_finding

    runtime = _runtime(args)
    client = ChainClient(best_for("state"))
    address = args.contract

    block = args.block or int(
        client.read("eth_getBlockByNumber", ["finalized", False]).value["number"], 16
    )
    at = {"block_number": block}

    print(f"Reading {address} on {client.provider.chain} via {client.provider.name}")
    print(f"Every reading pinned to block {block:,}")

    def _register(label: str, reading, tier: str) -> None:
        runtime.register_evidence(
            args.review,
            locator=f"{client.provider.chain}:{address}@{reading.block_number}:{label}",
            content=str(reading.value).encode("utf-8"),
            description=f"{label} for {address} at block {reading.block_number}",
            source_tier=tier,
            provenance={**reading.provenance(), "contract": address, "reading": label},
            actor=args.actor,
            idempotency_key=f"chain-{reading.block_number}-{address}-{label}",
        )
        print(f"  T1  {label:<14} block {reading.block_number}  {reading.content_sha256[:16]}")

    def _register_finding(label: str, finding, tier: str, provenance: dict[str, Any]) -> None:
        """Register an assessment rather than a single reading.

        Its status is recorded verbatim in the provenance. `NO_PATTERN_MATCHED`,
        `NO_VENUE_FOUND` and `NO_LOCK_CONTRACT_IDENTIFIED` must reach the reviewer as
        themselves and never be softened into the negative claim they resemble.
        """

        runtime.register_evidence(
            args.review,
            locator=f"{client.provider.chain}:{address}@{block}:{label}",
            content=finding.describe().encode("utf-8"),
            description=f"{label} for {address} at block {block}",
            source_tier=tier,
            provenance={
                "kind": "CHAIN_STATE", "chain": client.provider.chain,
                "block_number": block, "contract": address, "reading": label,
                **provenance,
            },
            actor=args.actor,
            idempotency_key=f"chain-{block}-{address}-{label}",
        )
        print(f"  {tier}  {label:<14} {provenance.get('status', '')}")

    identity = queries.token_identity(client, address, **at)
    for label, reading in identity.items():
        _register(label, reading, "T1")
    _register("totalSupply", queries.total_supply(client, address, **at), "T1")

    # Read, never assumed. A token with 18 decimals quoted at sizes computed for 6 would
    # be probed a million times too small, and would report flawless depth.
    decimals = int(str(identity["decimals"].value), 16)

    # CG-04
    proxy = queries.proxy_finding(client, address, **at)
    _register_finding("upgradeability", proxy, "T2", {
        "status": proxy.status,
        "matched_patterns": sorted(proxy.slots),
        "unreachable_probes": list(proxy.unreachable),
        "conventions_probed": len(queries.PROXY_SLOTS),
    })
    print(f"      {proxy.describe()}")

    holders = queries.authority_holders(client, address, **at)
    paused = queries.is_paused(client, address, **at)
    print(f"  --  authority       {holders}")
    print(f"  --  paused          {paused}")

    # CG-03
    locks = lock_finding(client, address, **at)
    _register_finding("locks", locks, "T1", {
        "status": locks.status,
        "registry_size": locks.registry_size,
        "addresses_searched": list(locks.searched),
        "burned_supply": locks.burned_supply,
        "locked_supply": locks.locked_supply,
    })

    # CG-05. Sizes span four orders of magnitude because one quote cannot tell a deep pool
    # from a shallow one that prices small trades well, and that is the whole question.
    sizes = tuple(n * 10**decimals for n in EXIT_SIZES_IN_TOKENS)
    liquidity = exit_cost(client, address, sizes, **at)
    _register_finding("liquidity", liquidity, "T1", {
        "status": liquidity.status,
        "sizes_in_whole_tokens": list(EXIT_SIZES_IN_TOKENS),
        "decimals": decimals,
        "venues_probed": list(liquidity.venues_probed),
        "quote_assets": list(liquidity.quote_assets),
        "unreachable": list(liquidity.unreachable),
    })

    # Composition needs a pool, not a token: `pool_ownership` reads the pair's own ERC-20.
    # Which pair is a choice, so it is recorded rather than left implied.
    pair = v2_pair(client, address, QUOTE_TOKENS["WETH"], **at)
    if pair:
        composition = pool_ownership(client, pair, burn_addresses=BURN_ADDRESSES, **at)
        _register_finding("lp_composition", composition, "T1", {
            "status": "ASSESSED",
            "pair": pair,
            "quote_asset": "WETH",
            "lp_total_supply": composition.lp_total_supply,
            "covers_v3": composition.covers_v3,
        })
    else:
        # No V2 pair is not "no liquidity"; V3 holds positions as NFTs this cannot read.
        print("  --  lp_composition  NO_V2_PAIR (V3 positions are NFTs and unreachable here)")

    # CG-02. A window, never an unbounded history: the finding is about the blocks walked
    # and says so, and `covered_ranges` proves the walk had no gap the log cap opened.
    window_from = max(0, block - max(1, args.log_window) + 1)
    logs_client = ChainClient(best_for("logs"))
    distinctness = address_distinctness(logs_client, address, window_from, block)
    _register_finding("address_distinctness", distinctness, "T2", {
        "status": "ASSESSED",
        "method": METHOD,
        "from_block": window_from,
        "to_block": block,
        "covered_ranges": [list(r) for r in distinctness.covered_ranges],
        "transfers_seen": distinctness.transfers_seen,
        "addresses_seen": len(distinctness.addresses_seen),
        "clusters": len(distinctness.clusters),
    })

    _print_next("board advance --to EVIDENCE_LOCKED, then ASSIGNMENT")
    return 0


def cmd_advance(args: argparse.Namespace) -> int:
    """Move the review to its next lifecycle state."""

    runtime = _runtime(args)
    metadata = _load(args.metadata) if args.metadata else None
    runtime.advance(
        args.review,
        args.to,
        actor=args.actor,
        idempotency_key=args.key or f"advance-{args.review}-{args.to}",
        metadata=metadata,
    )
    print(f"{args.review} is now {runtime.repository.get_session(args.review).status}.")
    return 0


def cmd_accept(args: argparse.Namespace) -> int:
    """Accept seats and declare independence, so the review can begin."""

    runtime = _runtime(args)
    for assignment in runtime.repository.list_assignments(args.review):
        runtime.respond_to_assignment(
            args.review,
            assignment.assignment_id,
            actor=assignment.reviewer_actor,
            has_material_conflict=False,
            conflict_basis=None,
            human_signature_ref=f"{args.signature}-{assignment.reviewer_role}",
            idempotency_key=f"accept-{args.review}-{assignment.reviewer_role}",
        )
        print(f"  {assignment.reviewer_role:5} accepted, no material conflict")
    _print_next("board advance --to INDEPENDENT_REVIEW")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    """Submit one seat's report, with any challenge sheets it raised."""

    runtime = _runtime(args)
    payload = _load(args.report)
    assignments = {
        item.reviewer_role: item for item in runtime.repository.list_assignments(args.review)
    }
    assignment = assignments[payload["reviewer_role"]]
    runtime.submit_report(
        args.review,
        assignment.assignment_id,
        raw_report=payload["report"],
        raw_findings=tuple(payload.get("findings", ())),
        finding_categories=payload.get("finding_categories", {}),
        summary=payload["summary"],
        recommendation=payload["recommendation"],
        evidence_reference_ids=tuple(payload["evidence_reference_ids"]),
        actor=assignment.reviewer_actor,
        idempotency_key=f"report-{args.review}-{payload['reviewer_role']}",
    )
    count = len(payload.get("findings", ()))
    print(f"  {payload['reviewer_role']:5} reported: {count} challenge(s)")
    return 0


# Severities that cannot be satisfied by doing nothing. Kept beside the renderer
# because it is a presentation rule: the profile decides what blocks, this decides
# how an unfilled field reads.
_REMEDIATION_REQUIRED = frozenset({"SEV-1", "SEV-2"})


def _fix_line(finding) -> str:
    """What the sheet shows when a finding names no remediation.

    Absent used to render as "No remediation required." at every severity, so a
    SEV-2 read "needs a fix or an accepted remediation plan" on its Impact line and
    "No remediation required." two lines below. On a blocking finding those are
    opposite claims, and the sheet showed the wrong one -- a reader skimming a
    rejection would take it as already handled.

    Absent means nobody wrote one down. At a blocking severity that is a gap in the
    finding, and the sheet now says so.
    """

    stated = str(finding.raw_record.get("remediation_requirement") or "").strip()
    if stated:
        return stated
    if finding.severity in _REMEDIATION_REQUIRED:
        return "NOT SPECIFIED - this severity requires a remediation plan."
    return "No remediation required."


def cmd_remediate(args: argparse.Namespace) -> int:
    """Answer a blocking finding with a remediation plan.

    The board could raise SEV-1 and SEV-2 findings and the front door offered no
    way to respond to one, so answering a blocker meant writing Python -- the exact
    situation this CLI exists to remove. Review 0006 made it visible: two blocking
    findings, both rendering NOT SPECIFIED, and no command to fill them in.

    The runtime's constraints are surfaced here rather than left to be discovered
    through a refusal. Only the Methodology Auditor may submit, and only while the
    review is still in CHALLENGE or CONSOLIDATION -- once a decision candidate is
    frozen the inputs cannot move, which is what stops a plan being written to fit
    a verdict already computed.
    """

    runtime = _runtime(args)
    payload = _load(args.plan)
    initiation = runtime.repository.get_initiation(args.review)
    auditor = initiation["methodology_auditor"]
    try:
        result = runtime.submit_remediation_plan(
            args.review,
            payload,
            actor=auditor,
            idempotency_key=f"remediate-{args.review}-{payload.get('document_id', 'plan')}",
        )
    except RBEError as error:
        print(f"Refused [{error.code}]: {error}")
        if error.details:
            print(f"  {json.dumps(error.details)}")
        if error.code == "RBE_REMEDIATION_SUBMISSION_NOT_OPEN":
            print("  Plans are accepted in CHALLENGE or CONSOLIDATION, before a decision is prepared.")
        if error.code == "RBE_REMEDIATION_ACTOR_MISMATCH":
            print(f"  Only the Methodology Auditor ({auditor}) may submit a plan.")
        return 1
    accepted = result.get("items", result) if isinstance(result, dict) else result
    print(f"Remediation plan recorded for {args.review} by {auditor}.")
    for item in payload.get("items", ()):  # echo what was answered, worst first
        print(f"  {item['finding_id']:<18} -> {item['planned_changes'][:56]}")
    _print_next("board challenges to see the sheets, then board decide")
    return 0


def cmd_supersede(args: argparse.Namespace) -> int:
    """Record that this review's decision replaces an earlier review's.

    Distinct from the appeal path, which replaces a decision inside one session. This is
    the cross-review case: a second review of the same subject, at a higher tier or on
    fresher evidence, standing in place of the first.

    Nothing recorded this before, so a reader of the earlier decision found it current.
    """

    runtime = _runtime(args)
    result = runtime.link_review_supersession(
        args.review,
        supersedes_session_id=args.supersedes,
        actor=args.actor,
        idempotency_key=args.key or f"supersede-{args.review}-{args.supersedes}",
    )
    print(f"{args.review} now supersedes {args.supersedes}.")
    print(f"  superseded decision  {result['superseded_decision_id']}  -> SUPERSEDED")
    print(f"  successor decision   {result['successor_decision_id']}")
    print("  The earlier decision stays readable; only its status changed.")
    return 0


def cmd_mandate(args: argparse.Namespace) -> int:
    """Ask whether a published decision permits a proposed action.

    Reads an exported decision bundle rather than the live store, because a mandate should
    be answerable by anyone holding the bundle -- including someone who was not present
    when the review ran, which is the whole point of exporting it.
    """

    from rbe_runtime.mandate import PERMITTED, DriftObservation, ProposedAction, evaluate

    root = Path(args.bundle)
    package = json.loads((root / "decision.json").read_text(encoding="utf-8"))
    session = json.loads((root / "session.json").read_text(encoding="utf-8"))
    reports_doc = json.loads((root / "reports.json").read_text(encoding="utf-8"))
    reports = reports_doc.get("reports", reports_doc) if isinstance(reports_doc, dict) else reports_doc

    drift = None
    if args.implementation:
        recorded = args.recorded_implementation or args.implementation
        drift = DriftObservation(args.block, args.implementation, recorded)

    finding = evaluate(
        package,
        ProposedAction(args.subject, args.action),
        now=args.now,
        session=session,
        reports=reports if isinstance(reports, list) else [],
        drift=drift,
    )
    print(finding.describe())
    # Exit code, not just text: a caller wiring this into anything needs a signal that
    # cannot be misread, and only PERMITTED is success.
    return 0 if finding.status == PERMITTED else 3


def cmd_verify(args: argparse.Namespace) -> int:
    """Record that a named human read an agent seat's draft and verified it.

    The runtime refuses an AI-assisted report until `human_verified` is true. That is
    the control, not an obstacle: an agent seat produces an unsigned draft, and a draft
    becomes reviewable material only when a person takes responsibility for it.

    So this is a separate command run by that person, rather than a field the drafting
    process fills in for itself. The distinction is the whole of EG-04, and this
    repository has already broken it once -- a demonstration run recorded a named human
    as the transcriber of a figure the automation had read, and committed it.

    This command writes only to the draft file. Nothing is submitted to the review
    store here, so verifying is reversible until the report is filed.

    `--basis` records *how* the verifier read the material. Without it every signature
    looks alike, so a person who read a summary and a person who read sixteen findings in
    full leave identical records -- which is the same defect this command exists to
    prevent, aimed at the human instead of the agent. A weaker basis honestly recorded is
    worth more than a strong one implied.
    """

    from rbe_runtime.profile import is_agent_actor

    if is_agent_actor(args.by):
        raise RBEError(
            "RBE_AI_REPORT_UNVERIFIED",
            "An agent cannot verify agent-drafted material; that is not a second pair of eyes",
            "RBE-ES-FUT-002",
            {"by": args.by},
        )

    path = Path(args.report)
    payload = json.loads(path.read_text(encoding="utf-8"))
    role = payload["reviewer_role"]
    basis = str(getattr(args, "basis", "") or "").strip()

    print(f"Verifying {role} draft as {args.by}:")
    print(f"  summary: {payload['summary']}")
    for item in payload.get("findings", ()):
        print(f"  {item['severity']:6} {item['finding_id']:16} {item['title']}")
    if not payload.get("findings"):
        print("  (no findings)")
    if basis:
        print(f"  basis:   {basis}")

    # The report schema sets additionalProperties false, so the basis travels inside
    # ai_assistance -- an unconstrained object -- and in the signature reference, which is
    # what any rendering of the record actually shows a reader.
    signature = f"SIG-VERIFY-{role}-{args.by}"
    if basis:
        signature = f"{signature}-BASIS-{basis}"

    payload["report"]["ai_assistance"]["human_verified"] = True
    if basis:
        payload["report"]["ai_assistance"]["human_verification_basis"] = basis
    payload["report"]["human_signature_ref"] = signature
    # Report level only. `tpl-fnd` sets additionalProperties false on a finding's
    # ai_assistance, and rightly so: the basis describes one act of verification, not each
    # finding it covered. Writing it per-finding made every report unfileable.
    for item in payload.get("findings", ()):
        item["ai_assistance"]["human_verified"] = True
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"\nRecorded: {args.by} verified {len(payload.get('findings', ()))} finding(s) for {role}.")
    _print_next(f"board report --review <id> --report {args.report}")
    return 0


def cmd_challenges(args: argparse.Namespace) -> int:
    """Show what the board found, worst first."""

    runtime = _runtime(args)
    findings = runtime.repository.list_findings(args.review)
    assignments = {
        item.assignment_id: item for item in runtime.repository.list_assignments(args.review)
    }
    reports = {item.report_id: item for item in runtime.repository.list_reports(args.review)}
    sheets: list[ChallengeSheet] = []
    per_seat: dict[str, int] = {item.reviewer_role: 0 for item in assignments.values()}
    for finding in findings:
        report = reports.get(finding.source_report_id)
        role = assignments[report.assignment_id].reviewer_role if report else "?"
        per_seat[role] = per_seat.get(role, 0) + 1
        # Impact states what the severity means for the decision. Echoing the
        # detail back here would fill the sheet with the same sentence twice.
        sheets.append(
            ChallengeSheet(
                seat=role,
                severity=finding.severity,
                target=finding.title,
                problem=finding.description,
                impact=SEVERITY_EFFECT.get(finding.severity, "recorded"),
                fix=_fix_line(finding),
                evidence_ids=finding.evidence_reference_ids,
            )
        )
    silent = [
        NoChallenge(seat=role, checked="Assigned scope")
        for role, count in sorted(per_seat.items())
        if count == 0
    ]
    print(render_review(sheets, silent))
    print("\n" + "-" * 72)
    print(json.dumps(summarise(sheets), indent=2))
    print(json.dumps(board_health(per_seat), indent=2))
    return 0


def cmd_decide(args: argparse.Namespace) -> int:
    """Compute the machine decision candidate from the frozen findings."""

    runtime = _runtime(args)
    result = runtime.prepare_decision_candidate(
        args.review, actor=args.actor, idempotency_key=f"candidate-{args.review}"
    )
    evaluation = result["evaluation"]
    # An idempotent replay returns the evaluation as plain JSON rather than the
    # dataclass, so read it the same way in both cases.
    get = evaluation.get if isinstance(evaluation, dict) else lambda k: getattr(evaluation, k)
    print(f"process status: {get('process_status')}")
    print(f"outcome:        {get('outcome')}")
    print(f"reason:         {get('explanation')}")
    _print_next("board advance --to GOVERNANCE_VALIDATION, then board ratify")
    return 0


def cmd_ratify(args: argparse.Namespace) -> int:
    """Sign the decision. Human authority, never an agent.

    With --validator this is ordinary four-eyes ratification. With
    --single-authority the Board Chair signs alone, which the profile permits only
    while non-binding and which is recorded permanently on the decision.
    """

    runtime = _runtime(args)
    if args.single_authority and args.validator:
        print("Refused: choose either --validator or --single-authority, not both.")
        return 2
    if not args.single_authority and not args.validator:
        print(
            "Refused: ratification needs --validator <name> --validator-signature <ref>,\n"
            "or --single-authority if you are signing alone."
        )
        return 2
    result = runtime.ratify_decision(
        args.review,
        actor=args.actor,
        board_chair_signature_ref=args.signature,
        governance_validator=args.validator,
        governance_validation_ref=args.validator_signature,
        idempotency_key=f"ratify-{args.review}",
        single_authority_rationale=args.rationale,
    )
    if result.get("single_authority"):
        print(f"Decision {result['decision_id']} signed by {args.actor} alone.")
        print("  single authority: true  <-- recorded permanently on this decision")
        print("  the four-eyes control was not satisfied; a two-signature decision")
        print("  can supersede this one later without losing it.")
    else:
        print(f"Decision {result['decision_id']} signed by {args.actor} and {args.validator}.")
    print(f"  outcome:         {result['evaluation']['outcome'] if isinstance(result.get('evaluation'), dict) else ''}")
    print(f"  binding:         {result['binding']}")
    print(f"  merge permitted: {result['merge_permitted']}")
    _print_next("board advance --to DECIDED, then board publish")
    return 0


def cmd_publish(args: argparse.Namespace) -> int:
    """Publish the decision under a separate publication authority."""

    runtime = _runtime(args)
    result = runtime.publish_decision(
        args.review, actor=args.actor, idempotency_key=f"publish-{args.review}"
    )
    print(f"Published {result['publication_id']} by {args.actor}.")
    _print_next("board advance --to PUBLISHED, then rbe-runtime export")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Where the review is, and what it is waiting on."""

    runtime = _runtime(args)
    session = runtime.repository.get_session(args.review)
    readiness = runtime.assess_readiness(args.review)
    print(f"{args.review}: {session.status}")
    print(f"  process status: {readiness.process_status}")
    if readiness.unmet_prerequisites:
        print("  waiting on:")
        for item in readiness.unmet_prerequisites:
            print(f"    - {item}")
    if readiness.process_blockers:
        print("  blocked by:")
        for item in readiness.process_blockers:
            print(f"    - {item}")
    audit = runtime.repository.verify_audit(args.review)
    print(f"  audit chain:    {'valid' if audit['valid'] else 'INVALID'} ({audit['entries_verified']} entries)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="board", description="Convene and run a Review Board session."
    )
    parser.add_argument("--database", default=str(DEFAULT_DB), help="Review store path")
    parser.add_argument(
        "--profile",
        default=None,
        help="Methodology profile id, e.g. RBM-001 (research) or RBM-002 (engineering). "
             "Defaults to the research board. An unregistered id is refused rather "
             "than defaulted.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    seats = sub.add_parser("seats", help="Show agent seats and check independence")
    seats.add_argument("--seats", required=True)
    seats.set_defaults(func=cmd_seats)

    opened = sub.add_parser("open", help="Convene a review")
    opened.add_argument("--initiation", required=True)
    opened.set_defaults(func=cmd_open)

    evidence = sub.add_parser("evidence", help="Register a study proof bundle")
    evidence.add_argument("--review", required=True)
    evidence.add_argument("--bundle", required=True)
    evidence.add_argument("--actor", required=True)
    evidence.set_defaults(func=cmd_evidence)

    commit = sub.add_parser(
        "commit-evidence", help="Register source at a named commit (engineering review)"
    )
    commit.add_argument("--review", required=True)
    commit.add_argument("--repo", required=True, help="Path to the repository")
    commit.add_argument("--commit", required=True, help="Commit-ish under review")
    commit.add_argument("--path", required=True, nargs="+", help="Files to register")
    commit.add_argument("--test-log", default=None, help="Recorded test output (T1)")
    commit.add_argument("--test-command", default=None)
    commit.add_argument("--actor", required=True)
    commit.set_defaults(func=cmd_commit_evidence)

    chain = sub.add_parser(
        "chain-evidence", help="Register chain state at a finalized block (crypto review)"
    )
    chain.add_argument("--review", required=True)
    chain.add_argument("--contract", required=True, help="Contract address to read")
    chain.add_argument("--actor", required=True)
    chain.add_argument(
        "--block", type=int, default=0,
        help="Pin every reading to this height. Default: whatever is finalized now.",
    )
    chain.add_argument(
        "--log-window", type=int, default=60,
        help="Blocks of Transfer history for CG-02, ending at the pinned block.",
    )
    chain.set_defaults(func=cmd_chain_evidence)

    advance = sub.add_parser("advance", help="Move to the next lifecycle state")
    advance.add_argument("--review", required=True)
    advance.add_argument("--to", required=True)
    advance.add_argument("--actor", required=True)
    advance.add_argument("--metadata")
    advance.add_argument("--key")
    advance.set_defaults(func=cmd_advance)

    accept = sub.add_parser("accept", help="Accept seats and declare independence")
    accept.add_argument("--review", required=True)
    accept.add_argument("--signature", default="SIG")
    accept.set_defaults(func=cmd_accept)

    report = sub.add_parser("report", help="Submit one seat's report")
    report.add_argument("--review", required=True)
    report.add_argument("--report", required=True)
    report.set_defaults(func=cmd_report)

    supersede = sub.add_parser(
        "supersede", help="Record that this review replaces an earlier one"
    )
    supersede.add_argument("--review", required=True, help="The superseding review")
    supersede.add_argument("--supersedes", required=True, help="The review being replaced")
    supersede.add_argument("--actor", required=True, help="Board Chair of the superseding review")
    supersede.add_argument("--key", default="")
    supersede.set_defaults(func=cmd_supersede)

    mandate = sub.add_parser(
        "mandate", help="Ask whether a decision permits a proposed action"
    )
    mandate.add_argument("--bundle", required=True, help="Exported decision directory")
    mandate.add_argument("--subject", required=True, help="Locator the action concerns")
    mandate.add_argument("--action", default="", help="What is proposed")
    mandate.add_argument("--now", required=True, help="RFC3339 timestamp to evaluate against")
    mandate.add_argument("--block", type=int, default=0, help="Block the drift check was read at")
    mandate.add_argument("--implementation", default="", help="Implementation observed now")
    mandate.add_argument(
        "--recorded-implementation", default="",
        help="Implementation the review recorded. Omit only when it equals the observed one.",
    )
    mandate.set_defaults(func=cmd_mandate)

    verify = sub.add_parser(
        "verify", help="Record that a named human verified an agent seat's draft"
    )
    verify.add_argument("--report", required=True)
    verify.add_argument("--by", required=True, help="The human verifying. Never an agent.")
    verify.add_argument(
        "--basis", default="",
        help="How the material was read, e.g. full-text or summary-reading. Recorded so "
             "two different readings do not leave identical signatures.",
    )
    verify.set_defaults(func=cmd_verify)

    challenges = sub.add_parser("challenges", help="Show challenge sheets")
    challenges.add_argument("--review", required=True)
    challenges.set_defaults(func=cmd_challenges)

    decide = sub.add_parser("decide", help="Compute the decision candidate")
    decide.add_argument("--review", required=True)
    decide.add_argument("--actor", required=True)
    decide.set_defaults(func=cmd_decide)

    ratify = sub.add_parser("ratify", help="Sign the decision")
    ratify.add_argument("--review", required=True)
    ratify.add_argument("--actor", required=True)
    ratify.add_argument("--signature", required=True)
    ratify.add_argument("--validator", help="Governance validator (four-eyes ratification)")
    ratify.add_argument("--validator-signature", help="Governance validator signature ref")
    ratify.add_argument(
        "--single-authority",
        action="store_true",
        help="Sign alone. Permitted only while the methodology is non-binding, and recorded as such.",
    )
    ratify.add_argument("--rationale", default="", help="Why a single authority signed")
    ratify.set_defaults(func=cmd_ratify)

    publish = sub.add_parser("publish", help="Publish the decision")
    publish.add_argument("--review", required=True)
    publish.add_argument("--actor", required=True)
    publish.set_defaults(func=cmd_publish)

    remediate = sub.add_parser("remediate", help="Answer blocking findings with a plan")
    remediate.add_argument("--review", required=True)
    remediate.add_argument("--plan", required=True, help="tpl-rmp remediation plan JSON")
    remediate.set_defaults(func=cmd_remediate)

    status = sub.add_parser("status", help="Where the review is")
    status.add_argument("--review", required=True)
    status.set_defaults(func=cmd_status)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except RBEError as exc:
        print(f"Refused [{exc.code}]: {exc}")
        if exc.details:
            print(f"  {json.dumps(exc.details, default=str)}")
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
