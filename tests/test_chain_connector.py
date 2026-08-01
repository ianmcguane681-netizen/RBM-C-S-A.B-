"""A rate limit is a fact about the run. An empty log range is a fact about the chain.

These two arrive at the caller looking identical -- both are "I got nothing back" -- and
conflating them is how a throttled hour becomes a permanent statement that no activity
occurred. The same defect, in a different domain, once turned a rate-limited afternoon
into a recorded claim about what a court archive holds.

The second thing under test is subtler and was discovered by measuring rather than
reasoning. A public endpoint answered one historical query, which looked like archive
support. Across a spread of heights it answered some and refused others -- a load balancer
over backends with different state retention. So `serves_archive` is only true where
historical reads can be *relied* upon, and a provider that merely sometimes answers is
recorded as unreliable rather than promoted to capable.
"""
from __future__ import annotations

import urllib.error

import pytest

from connectors.chain import (
    FINALIZED,
    QUICKNODE_URL_ENV,
    ChainAccessError,
    ChainClient,
    ChainProvider,
    ChainReading,
    best_for,
    quicknode_ethereum,
)
from lib.http_retry import TransientRetrievalError

FAKE = ChainProvider(
    name="fake", url="https://example.test", chain="testnet",
    max_log_range=50, archive="yes",
)
NO_ARCHIVE = ChainProvider(
    name="tip-only", url="https://example.test", chain="testnet",
    max_log_range=50, archive="no",
)
UNRELIABLE = ChainProvider(
    name="lottery", url="https://example.test", chain="testnet",
    max_log_range=50, archive="unreliable",
)


def responder(*results):
    """Return each queued result in turn, so call order is asserted by construction."""

    queue = list(results)

    def _post(_url, payload):
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        if callable(item):
            return item(payload)
        return item

    return _post


def block(number):
    return {"result": {"number": hex(number)}}


def value(hexstr):
    return {"result": hexstr}


class TestRefusalIsNotAnObservation:
    def test_a_rate_limited_call_raises_rather_than_returning_nothing(self):
        client = ChainClient(FAKE, post_json=responder(
            urllib.error.HTTPError("u", 429, "Too Many Requests", {}, None)))

        with pytest.raises(TransientRetrievalError):
            client.call("eth_blockNumber")

    def test_a_throttling_message_inside_a_200_is_still_a_refusal(self):
        """Providers report throttling as a JSON-RPC error in a 200 response, so the
        status code alone cannot classify it. This is the case a status-only check
        would silently record as an answer."""

        client = ChainClient(FAKE, post_json=responder(
            {"error": {"code": -32005, "message": "rate limit exceeded, try again"}}))

        with pytest.raises(TransientRetrievalError):
            client.call("eth_blockNumber")

    def test_an_archive_refusal_is_transient_not_an_empty_result(self):
        client = ChainClient(FAKE, post_json=responder(
            {"error": {"code": -32602,
                       "message": "Archive requests require a personal token"}}))

        with pytest.raises(TransientRetrievalError):
            client.call("eth_call", [{}])

    def test_a_real_rpc_error_is_an_answer_and_does_not_retry(self):
        """A malformed call will fail identically forever. Deferring it would leave it
        unattempted for good, which is the mirror-image defect."""

        client = ChainClient(FAKE, post_json=responder(
            {"error": {"code": -32602, "message": "invalid argument 0: hex string"}}))

        with pytest.raises(ChainAccessError):
            client.call("eth_call", [{}])

    def test_an_empty_log_range_is_a_result_not_an_error(self):
        """The contrast that gives the others meaning: this one IS an observation."""

        client = ChainClient(FAKE, post_json=responder({"result": []}))

        logs, covered = client.get_logs("0xabc", [], 100, 120)

        assert logs == []
        assert covered == [(100, 120)]


class TestProviderLimitsAreDeclaredNotDiscovered:
    def test_a_wide_log_range_is_split_never_truncated(self):
        client = ChainClient(FAKE, post_json=responder(
            {"result": [{"n": 1}]}, {"result": [{"n": 2}]}, {"result": [{"n": 3}]}))

        logs, covered = client.get_logs("0xabc", [], 0, 149)

        assert covered == [(0, 49), (50, 99), (100, 149)]
        assert len(logs) == 3

    def test_the_covered_ranges_are_returned_so_a_gap_is_visible(self):
        """A walk that returned only its logs would understate activity by exactly the
        ranges it never reached, with nothing in the result to say so."""

        client = ChainClient(FAKE, post_json=responder({"result": []}, {"result": []}))

        _logs, covered = client.get_logs("0xabc", [], 0, 60)

        assert covered == [(0, 49), (50, 60)]
        assert covered[0][0] == 0 and covered[-1][1] == 60

    def test_a_provider_that_serves_no_logs_refuses_rather_than_returning_empty(self):
        client = ChainClient(
            ChainProvider(name="x", url="u", chain="t", max_log_range=0, archive="no"),
            post_json=responder({"result": []}),
        )

        with pytest.raises(ChainAccessError, match="absence of activity"):
            client.get_logs("0xabc", [], 0, 10)


class TestArchiveCapabilityIsThreeValued:
    def test_unreliable_is_not_promoted_to_capable(self):
        """One successful historical query is one draw, not a capability."""

        assert UNRELIABLE.archive == "unreliable"
        assert UNRELIABLE.serves_archive is False

    def test_a_historical_read_is_refused_where_archive_is_not_reliable(self):
        client = ChainClient(UNRELIABLE, post_json=responder(value("0x1")))

        with pytest.raises(ChainAccessError, match="archive"):
            client.read("eth_call", [{"to": "0xabc"}], block_number=1_000_000)

    def test_a_historical_read_is_allowed_where_archive_is_reliable(self):
        client = ChainClient(FAKE, post_json=responder(value("0x2a")))

        reading = client.read("eth_call", [{"to": "0xabc"}], block_number=1_000_000)

        assert reading.block_number == 1_000_000
        assert reading.params[-1] == hex(1_000_000)


class TestProvidersAreChosenByMeasurementNotPreference:
    """Measured 2026-08-01, and the result inverts the obvious assumption.

    The keyed endpoint answered 9 of 9 historical heights and caps eth_getLogs at 6
    blocks. The anonymous one answered 4 of 8 and caps at 50. Neither wins both, so a
    single "preferred provider" would silently degrade half the work.
    """

    def test_state_prefers_the_endpoint_that_can_actually_serve_history(self, monkeypatch):
        monkeypatch.setenv(QUICKNODE_URL_ENV, "https://example.test/token/")

        provider = best_for("state")

        assert provider.name == "quicknode"
        assert provider.serves_archive is True

    def test_logs_prefer_the_wider_range_even_when_a_key_is_configured(self, monkeypatch):
        monkeypatch.setenv(QUICKNODE_URL_ENV, "https://example.test/token/")

        assert best_for("logs").max_log_range == 50

    def test_state_falls_back_when_no_key_is_configured(self, monkeypatch):
        """Legitimate for current-state reads, which the anonymous endpoint serves
        reliably."""

        monkeypatch.delenv(QUICKNODE_URL_ENV, raising=False)

        assert best_for("state").name == "1rpc.io"

    def test_the_fallback_cannot_silently_satisfy_a_historical_read(self, monkeypatch):
        """The half that matters. Falling back for current state is fine; falling back
        and then answering a historical question would return a different measurement
        wearing the requested block's label."""

        monkeypatch.delenv(QUICKNODE_URL_ENV, raising=False)
        client = ChainClient(best_for("state"), post_json=responder(value("0x1")))

        with pytest.raises(ChainAccessError, match="archive"):
            client.read("eth_call", [{"to": "0xabc"}], block_number=20_000_000)

    def test_an_unknown_task_raises_rather_than_defaulting(self):
        with pytest.raises(ValueError, match="Unknown task"):
            best_for("prices")


class TestCredentialHandling:
    def test_a_missing_url_names_the_variable_to_set(self, monkeypatch):
        monkeypatch.delenv(QUICKNODE_URL_ENV, raising=False)

        with pytest.raises(ChainAccessError, match=QUICKNODE_URL_ENV):
            quicknode_ethereum()

    def test_the_url_is_the_credential_so_no_separate_key_is_demanded(self, monkeypatch):
        """QuickNode embeds its token in the URL path. An earlier version demanded an
        `api_key` argument as well and rejected a correctly authenticated provider."""

        monkeypatch.setenv(QUICKNODE_URL_ENV, "https://example.test/token/")

        client = ChainClient(quicknode_ethereum(), post_json=responder(value("0x1")))

        assert client.provider.requires_key is True

    def test_a_credentialed_provider_with_no_url_is_refused(self):
        """An unauthenticated call returns an authorisation error indistinguishable from
        an empty result, so it must never be attempted."""

        with pytest.raises(ChainAccessError, match="no URL configured"):
            ChainClient(ChainProvider(name="keyed", url="  ", chain="t",
                                      max_log_range=6, archive="yes", requires_key=True))


class TestEveryReadCarriesItsProvenance:
    def test_a_read_resolves_the_tag_before_taking_the_value(self):
        """Recorded height must never be later than the state it describes, so the
        height is resolved first and the value read second."""

        seen = []

        def _post(_url, payload):
            seen.append(payload["method"])
            if payload["method"] == "eth_getBlockByNumber":
                return block(5000)
            return value("0x64")

        reading = ChainClient(NO_ARCHIVE, post_json=_post).read("eth_call", [{"to": "0x1"}])

        assert seen == ["eth_getBlockByNumber", "eth_call"]
        assert reading.block_number == 5000

    def test_the_tag_is_queried_and_the_height_is_recorded(self):
        """Querying the resolved number instead would re-enter the availability lottery
        for no gain, so the request carries the tag and the record carries the number."""

        client = ChainClient(NO_ARCHIVE, post_json=responder(block(777), value("0x1")))

        reading = client.read("eth_call", [{"to": "0x1"}], tag=FINALIZED)

        assert reading.params[-1] == FINALIZED
        assert reading.block_number == 777

    def test_provenance_carries_everything_needed_to_regenerate(self):
        client = ChainClient(NO_ARCHIVE, post_json=responder(block(42), value("0xff")))

        provenance = client.read("eth_call", [{"to": "0xabc"}]).provenance()

        for required in ("kind", "chain", "block_number", "method", "params",
                         "provider", "retrieved_at", "content_sha256"):
            assert provenance[required], f"{required} missing from provenance"
        assert provenance["kind"] == "CHAIN_STATE"

    def test_a_reading_without_a_block_height_cannot_be_constructed(self):
        """CG-06 says a figure without a height is a claim. This makes it unbuildable
        rather than merely discouraged."""

        with pytest.raises(ValueError, match="claim"):
            ChainReading(value="0x1", chain="ethereum", block_number=0,
                         method="eth_call", params=[], provider="p", retrieved_at="t")

    def test_the_hash_covers_the_value_and_its_height(self):
        """Same value at a different height is a different measurement."""

        common = dict(chain="ethereum", method="eth_call", params=[],
                      provider="p", retrieved_at="t")
        one = ChainReading(value="0x1", block_number=100, **common)
        other = ChainReading(value="0x1", block_number=101, **common)

        assert one.content_sha256 != other.content_sha256
