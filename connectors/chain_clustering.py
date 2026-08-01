"""CG-02: an address is not a person, and a cluster is not a proof.

The gate exists because ten thousand wallets funded from one wallet are one actor. The
obvious fix -- collapse addresses sharing a funding source -- fails in the opposite
direction and just as badly: it merges every exchange customer into a single entity. A
Coinbase hot wallet and a Sybil farm are indistinguishable by funding pattern alone, and a
module that guessed between them would understate real holder counts as confidently as
counting raw wallets overstates them.

So nothing here collapses anything. Findings are separated by evidential strength:

    FACT        self-transfers and closed cycles -- definitively not distinct activity
    HYPOTHESIS  addresses sharing a first funder, with the funder NAMED
    CONTEXT     the block window walked, so a three-hour sample cannot read as all-time

A reviewer sees "8,431 addresses first funded by 0xA9D1..." and rules on whether that is
an exchange or a farm. That judgement is the reviewer's, and the module's job is to put it
in front of them with the evidence attached rather than to pre-empt it.

RBS-003 requires the method be recorded: "an unstated heuristic is not reproducible." The
parameters travel in the finding for that reason.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from connectors.chain import ChainClient

# keccak256("Transfer(address,address,uint256)")
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

ZERO_ADDRESS = "0x" + "0" * 40

# The heuristic's name and version travel with every finding. A cluster produced by a
# different rule is not comparable to one produced by this rule, and a finding that cannot
# say which rule made it cannot be reproduced or challenged.
METHOD = "first-funder-v1"
METHOD_DESCRIPTION = (
    "Addresses are grouped by the sender of the first inbound transfer observed within the "
    "walked window. Grouping is reported, never applied: a shared funder is consistent with "
    "one actor using many wallets and equally consistent with an exchange serving many "
    "customers, and this rule cannot distinguish them."
)


@dataclass(frozen=True, slots=True)
class Cluster:
    """Addresses sharing a first funder. A hypothesis, and labelled as one."""

    funder: str
    members: tuple[str, ...]

    @property
    def size(self) -> int:
        return len(self.members)


@dataclass(frozen=True, slots=True)
class DistinctnessFinding:
    """What the transfer log supports, at three levels of confidence.

    There is deliberately no single "true holder count" field. Every candidate for one
    would be a guess dressed as a measurement, and the gate exists because that guess is
    routinely made.
    """

    token: str
    from_block: int
    to_block: int
    covered_ranges: tuple[tuple[int, int], ...]
    transfers_seen: int
    addresses_seen: tuple[str, ...]
    self_transfers: int
    cyclic_pairs: tuple[tuple[str, str], ...]
    clusters: tuple[Cluster, ...]
    method: str = METHOD
    method_description: str = METHOD_DESCRIPTION

    @property
    def blocks_walked(self) -> int:
        return sum(end - start + 1 for start, end in self.covered_ranges)

    @property
    def raw_address_count(self) -> int:
        """Every address that appeared. The number people quote as "users"."""

        return len(self.addresses_seen)

    @property
    def largest_cluster(self) -> Cluster | None:
        return max(self.clusters, key=lambda c: c.size, default=None)

    def clustered_address_count(self) -> int:
        return sum(c.size for c in self.clusters)

    def describe(self) -> str:
        """Deliberately hard to quote out of context.

        Every number is bounded by its window, and the cluster line says what a cluster is
        not. A reader who wants "the holder count" will not find one here.
        """

        lines = [
            f"Transfer activity for {self.token} over blocks {self.from_block}-"
            f"{self.to_block} ({self.blocks_walked} blocks walked, "
            f"{self.transfers_seen:,} transfers).",
            "",
            "Established:",
            f"  {self.raw_address_count:,} distinct addresses appeared in this window.",
            f"  {self.self_transfers:,} transfers were self-transfers and are not activity "
            f"between parties.",
            f"  {len(self.cyclic_pairs):,} address pairs transferred in both directions.",
            "",
            "Not established:",
        ]
        if self.clusters:
            biggest = self.largest_cluster
            lines.append(
                f"  {len(self.clusters):,} group(s) of addresses share a first funder, "
                f"covering {self.clustered_address_count():,} addresses. The largest is "
                f"{biggest.size:,} addresses funded by {biggest.funder}."
            )
            lines.append(
                "  Whether any group is one actor or one exchange's customers is NOT "
                "determined by this evidence and requires a reviewer's judgement."
            )
        else:
            lines.append(
                "  No shared-funder groups were observed in this window. Addresses funded "
                "before the window began have no observable funder here."
            )
        lines += [
            "",
            f"Method: {self.method}. {self.method_description}",
            f"Window: this is a sample of {self.blocks_walked} blocks and describes no "
            f"period outside it.",
        ]
        return "\n".join(lines)


def _topic_address(topic: str) -> str:
    """A 32-byte indexed topic holding a left-padded address."""

    return "0x" + topic[-40:] if topic else ""


@dataclass
class TransferGraph:
    """Accumulated transfer structure. Built incrementally so a walk can be resumed."""

    first_funder: dict[str, str] = field(default_factory=dict)
    self_transfers: int = 0
    directed: set[tuple[str, str]] = field(default_factory=set)
    addresses: set[str] = field(default_factory=set)
    transfers: int = 0

    def add(self, sender: str, recipient: str) -> None:
        self.transfers += 1
        if sender:
            self.addresses.add(sender)
        if recipient:
            self.addresses.add(recipient)

        if sender and sender == recipient:
            # A wallet sending to itself moves no value between parties. Counting it as
            # activity is the cheapest way to inflate a usage figure.
            self.self_transfers += 1
            return

        # Mints come from the zero address and are not a funding relationship between
        # parties, so they are excluded from clustering rather than producing one enormous
        # cluster funded by 0x0.
        if sender and sender != ZERO_ADDRESS and recipient:
            self.directed.add((sender, recipient))
            self.first_funder.setdefault(recipient, sender)

    def cyclic_pairs(self) -> tuple[tuple[str, str], ...]:
        """Pairs that transferred in both directions within the window."""

        seen: set[tuple[str, str]] = set()
        for sender, recipient in self.directed:
            if (recipient, sender) in self.directed:
                seen.add(tuple(sorted((sender, recipient))))  # type: ignore[arg-type]
        return tuple(sorted(seen))

    def clusters(self, minimum_size: int = 2) -> tuple[Cluster, ...]:
        grouped: dict[str, list[str]] = defaultdict(list)
        for address, funder in self.first_funder.items():
            grouped[funder].append(address)
        return tuple(
            Cluster(funder=funder, members=tuple(sorted(members)))
            for funder, members in sorted(grouped.items())
            if len(members) >= minimum_size
        )


def address_distinctness(
    client: ChainClient,
    token: str,
    from_block: int,
    to_block: int,
    *,
    minimum_cluster_size: int = 2,
    **kw: Any,
) -> DistinctnessFinding:
    """CG-02 over a stated window.

    The window is an argument and never a default, because the honest version of this
    finding is bounded and a caller should have to choose the bound deliberately.

    `get_logs` returns the ranges it covered as well as the logs, so a walk split across
    the provider's cap cannot silently under-report. Those ranges travel into the finding.
    """

    logs, covered = client.get_logs(token, [TRANSFER_TOPIC], from_block, to_block, **kw)

    graph = TransferGraph()
    for entry in logs:
        topics = entry.get("topics") or []
        if len(topics) < 3:
            # A non-indexed or malformed Transfer cannot be attributed to parties. It is
            # skipped rather than guessed at, and remains counted in transfers_seen.
            graph.transfers += 1
            continue
        graph.add(_topic_address(topics[1]), _topic_address(topics[2]))

    return DistinctnessFinding(
        token=token,
        from_block=from_block,
        to_block=to_block,
        covered_ranges=tuple(covered),
        transfers_seen=graph.transfers,
        addresses_seen=tuple(sorted(graph.addresses)),
        self_transfers=graph.self_transfers,
        cyclic_pairs=graph.cyclic_pairs(),
        clusters=graph.clusters(minimum_cluster_size),
    )
