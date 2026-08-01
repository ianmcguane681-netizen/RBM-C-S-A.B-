"""An address is not a person, and a cluster is not a proof.

CG-02 exists because ten thousand wallets funded from one wallet are one actor. The
obvious fix -- collapse addresses sharing a funder -- fails just as badly in the opposite
direction: it merges every exchange customer into one entity. A Coinbase hot wallet and a
Sybil farm are indistinguishable by funding pattern, so a module that chose between them
would understate real holder counts as confidently as raw wallet counts overstate them.

These tests exist mostly to stop that choice being made. The module reports clusters and
never applies them, and several assertions below check the *absence* of a collapsed
number rather than the presence of a correct one.
"""
from __future__ import annotations

import pytest

from connectors.chain import ChainClient, ChainProvider
from connectors.chain_clustering import (
    METHOD,
    TRANSFER_TOPIC,
    ZERO_ADDRESS,
    DistinctnessFinding,
    TransferGraph,
    address_distinctness,
)

PROVIDER = ChainProvider(
    name="fake", url="https://example.test", chain="testnet",
    max_log_range=50, archive="yes", logs="yes",
)


def addr(n):
    return "0x" + f"{n:040x}"


def topic(address):
    return "0x" + address.removeprefix("0x").rjust(64, "0")


def transfer(sender, recipient):
    return {"topics": [TRANSFER_TOPIC, topic(sender), topic(recipient)]}


def logs_responder(entries, block=1000):
    def _post(_url, payload):
        if payload["method"] == "eth_getBlockByNumber":
            return {"result": {"number": hex(block)}}
        return {"result": entries}

    return _post


class TestFactsAreSeparatedFromHypotheses:
    def test_a_self_transfer_is_counted_as_a_fact_not_activity(self):
        """A wallet sending to itself moves no value between parties. Counting it is the
        cheapest way to inflate a usage figure."""

        graph = TransferGraph()
        graph.add(addr(1), addr(1))

        assert graph.self_transfers == 1
        assert graph.first_funder == {}

    def test_a_cycle_between_two_addresses_is_detected(self):
        graph = TransferGraph()
        graph.add(addr(1), addr(2))
        graph.add(addr(2), addr(1))

        assert graph.cyclic_pairs() == ((addr(1), addr(2)),)

    def test_a_one_way_transfer_is_not_a_cycle(self):
        graph = TransferGraph()
        graph.add(addr(1), addr(2))

        assert graph.cyclic_pairs() == ()

    def test_a_shared_funder_produces_a_cluster(self):
        graph = TransferGraph()
        for recipient in (2, 3, 4):
            graph.add(addr(1), addr(recipient))

        clusters = graph.clusters()

        assert len(clusters) == 1
        assert clusters[0].funder == addr(1)
        assert clusters[0].size == 3

    def test_only_the_first_inbound_transfer_sets_the_funder(self):
        """Later senders are counterparties, not funders. Overwriting would make the
        cluster depend on walk order."""

        graph = TransferGraph()
        graph.add(addr(1), addr(9))
        graph.add(addr(2), addr(9))

        assert graph.first_funder[addr(9)] == addr(1)

    def test_a_mint_does_not_create_a_cluster(self):
        """Transfers from the zero address are issuance, not a funding relationship
        between parties. Including them would put every holder in one enormous cluster
        funded by 0x0, which is true and useless."""

        graph = TransferGraph()
        for recipient in (2, 3, 4):
            graph.add(ZERO_ADDRESS, addr(recipient))

        assert graph.clusters() == ()


class TestNothingIsCollapsed:
    """The assertions that stop the module answering a question it cannot answer."""

    def finding(self, clusters_of=3):
        graph = TransferGraph()
        for recipient in range(2, 2 + clusters_of):
            graph.add(addr(1), addr(recipient))
        return DistinctnessFinding(
            token="0xtok", from_block=1, to_block=50, covered_ranges=((1, 50),),
            transfers_seen=graph.transfers, addresses_seen=tuple(sorted(graph.addresses)),
            self_transfers=graph.self_transfers, cyclic_pairs=graph.cyclic_pairs(),
            clusters=graph.clusters(),
        )

    def test_there_is_no_single_holder_count_field(self):
        """Every candidate for one would be a guess dressed as a measurement, and the gate
        exists because that guess is routinely made."""

        fields = set(DistinctnessFinding.__dataclass_fields__)

        for forbidden in ("holder_count", "true_holders", "unique_users", "real_addresses"):
            assert forbidden not in fields

    def test_the_description_says_a_cluster_is_not_determined(self):
        described = self.finding().describe()

        assert "NOT determined by this evidence" in described
        assert "requires a reviewer's judgement" in described

    def test_the_description_never_calls_a_cluster_one_entity(self):
        """Checked on unambiguous phrasings only.

        An earlier version of this test looked for the substring "is one actor" and
        matched it inside "Whether any group is one actor or one exchange's customers is
        NOT determined" -- the correct hedged sentence. That is the substring-leakage
        defect `lib/terms.py` exists to prevent, committed in a test written to catch
        overreach. Hedged mentions are asserted separately below.
        """

        described = self.finding().describe().lower()

        for overreach in ("sybil", "fake accounts", "bot network", "wash trading"):
            assert overreach not in described

    def test_any_claim_about_a_cluster_being_one_actor_is_hedged(self):
        """The positive form of the assertion above: the phrase may appear, but only
        inside a sentence that withholds the conclusion."""

        described = self.finding().describe()

        for sentence in described.split("."):
            if "one actor" in sentence.lower():
                assert any(
                    hedge in sentence.lower()
                    for hedge in ("whether", "consistent with", "not determined")
                ), f"unhedged claim: {sentence.strip()}"

    def test_the_funder_is_named_so_a_reviewer_can_judge(self):
        """An exchange hot wallet is recognisable to a human and not to this rule."""

        assert addr(1) in self.finding().describe()

    def test_clusters_are_reported_separately_from_the_address_count(self):
        finding = self.finding()

        assert finding.raw_address_count == 4          # funder plus three recipients
        assert finding.clustered_address_count() == 3  # never subtracted from the above


class TestTheWindowTravels:
    def test_the_walked_window_is_stated(self):
        finding = DistinctnessFinding(
            token="0xtok", from_block=100, to_block=199, covered_ranges=((100, 149), (150, 199)),
            transfers_seen=0, addresses_seen=(), self_transfers=0, cyclic_pairs=(), clusters=(),
        )

        assert finding.blocks_walked == 100
        assert "describes no period outside it" in finding.describe()

    def test_covered_ranges_come_from_the_walk_not_the_request(self):
        """A walk split across the provider's cap must report what it actually covered,
        so a gap cannot hide behind the requested bounds."""

        client = ChainClient(PROVIDER, post_json=logs_responder([]))

        finding = address_distinctness(client, "0xtok", 0, 120)

        assert finding.covered_ranges == ((0, 49), (50, 99), (100, 120))

    def test_the_method_is_recorded_in_the_finding(self):
        """RBS-003: an unstated heuristic is not reproducible."""

        client = ChainClient(PROVIDER, post_json=logs_responder([]))

        finding = address_distinctness(client, "0xtok", 0, 10)

        assert finding.method == METHOD
        assert METHOD in finding.describe()
        assert "cannot distinguish them" in finding.describe()

    def test_an_empty_window_reports_no_groups_rather_than_no_clusters_existing(self):
        client = ChainClient(PROVIDER, post_json=logs_responder([]))

        described = address_distinctness(client, "0xtok", 0, 10).describe()

        assert "before the window began have no observable funder here" in described


class TestMalformedLogs:
    def test_a_transfer_without_indexed_parties_is_counted_but_not_attributed(self):
        """Some tokens do not index their Transfer parties. Guessing at the addresses
        would invent a funding relationship; dropping the log silently would understate
        volume. It is counted and not attributed."""

        client = ChainClient(PROVIDER, post_json=logs_responder([{"topics": [TRANSFER_TOPIC]}]))

        finding = address_distinctness(client, "0xtok", 0, 10)

        assert finding.transfers_seen == 1
        assert finding.raw_address_count == 0
        assert finding.clusters == ()

    def test_a_well_formed_transfer_is_attributed(self):
        client = ChainClient(
            PROVIDER, post_json=logs_responder([transfer(addr(1), addr(2))])
        )

        finding = address_distinctness(client, "0xtok", 0, 10)

        assert finding.transfers_seen == 1
        assert finding.raw_address_count == 2
