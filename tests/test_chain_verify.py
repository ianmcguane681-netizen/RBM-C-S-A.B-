"""A figure that cannot be regenerated is a claim, and a resample that never ran is not a pass.

Two things are under test. The first is the three-way outcome: reproduced, diverged, and
not-attempted, where the third exists because a sample that could not be run must never be
counted as one that passed.

The second is a bug this file exists to keep fixed. `ChainReading.digest` originally hashed
the full parameter list, which ends with the block the call was pinned to. A reading taken
via the `finalized` tag and the same reading re-run at the explicit height that tag
resolved to therefore hashed differently -- same chain, same block, same call, same value.
Every live resample came back DIVERGED, reporting that the provider was serving state it
had not been asked for. It was not; the hash was measuring the route rather than the
measurement.

A reproducibility gate that always fails is worse than no gate, because it teaches the
reader to ignore it.
"""
from __future__ import annotations

import random

import pytest

from connectors.chain import ChainClient, ChainProvider, ChainReading
from connectors.chain_verify import (
    DIVERGED,
    NOT_ATTEMPTED,
    REPRODUCED,
    resample,
)
from lib.http_retry import TransientRetrievalError

ARCHIVE = ChainProvider(
    name="fake", url="https://example.test", chain="testnet",
    max_log_range=50, archive="yes", logs="yes",
)
NO_ARCHIVE = ChainProvider(
    name="tip-only", url="https://example.test", chain="testnet",
    max_log_range=50, archive="unreliable",
)


def reading(value="0x64", block=500, params=None):
    return ChainReading(
        value=value, chain="testnet", block_number=block, method="eth_call",
        params=params if params is not None else [{"to": "0xabc", "data": "0x1"}, "finalized"],
        provider="fake", retrieved_at="t",
    )


def responder(value="0x64", block=500):
    def _post(_url, payload):
        if payload["method"] == "eth_getBlockByNumber":
            return {"result": {"number": hex(block)}}
        return {"result": value}

    return _post


class TestTheRouteIsNotTheMeasurement:
    """The regression tests for the digest bug."""

    def test_a_tag_read_and_a_height_read_of_the_same_state_agree(self):
        via_tag = reading(params=[{"to": "0xabc", "data": "0x1"}, "finalized"])
        via_height = reading(params=[{"to": "0xabc", "data": "0x1"}, "0x1f4"])

        assert via_tag.content_sha256 == via_height.content_sha256

    @pytest.mark.parametrize("tag", ["latest", "finalized", "safe", "pending", "earliest"])
    def test_every_block_tag_is_excluded_from_the_hash(self, tag):
        tagged = reading(params=[{"to": "0xabc", "data": "0x1"}, tag])
        bare = reading(params=[{"to": "0xabc", "data": "0x1"}])

        assert tagged.content_sha256 == bare.content_sha256

    def test_the_call_target_is_still_hashed(self):
        """Stripping the tag must not strip the parameters that identify the call."""

        one = reading(params=[{"to": "0xabc", "data": "0x1"}, "finalized"])
        other = reading(params=[{"to": "0xdef", "data": "0x1"}, "finalized"])

        assert one.content_sha256 != other.content_sha256

    def test_an_address_is_not_mistaken_for_a_block_reference(self):
        """Block numbers are short hex; addresses are 42 characters. The length bound is
        what separates them without knowing each method's parameter order."""

        one = reading(params=["0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"])
        other = reading(params=["0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599"])

        assert one.content_sha256 != other.content_sha256

    def test_the_same_value_at_a_different_block_still_differs(self):
        assert reading(block=100).content_sha256 != reading(block=101).content_sha256

    def test_a_live_shaped_resample_reproduces(self):
        client = ChainClient(ARCHIVE, post_json=responder())

        result = resample(client, [reading()], rng=random.Random(0))

        assert result.outcomes[0].status == REPRODUCED
        assert result.establishes_reproducibility is True


class TestNotAttemptedIsNotAPass:
    def test_a_transient_failure_is_not_attempted(self):
        def _post(_url, payload):
            if payload["method"] == "eth_getBlockByNumber":
                return {"result": {"number": "0x1f4"}}
            return {"error": {"code": -32005, "message": "rate limit exceeded"}}

        result = resample(ChainClient(ARCHIVE, post_json=_post), [reading()],
                          rng=random.Random(0))

        assert result.outcomes[0].status == NOT_ATTEMPTED
        assert result.reproduced == ()

    def test_not_attempted_blocks_the_reproducibility_claim(self):
        """A partial resample establishes something about the readings it reached and
        nothing about the set, which is what CG-06 asks about."""

        def _post(_url, payload):
            if payload["method"] == "eth_getBlockByNumber":
                return {"result": {"number": "0x1f4"}}
            return {"error": {"code": -32005, "message": "rate limit exceeded"}}

        result = resample(ChainClient(ARCHIVE, post_json=_post), [reading()],
                          rng=random.Random(0))

        assert result.establishes_reproducibility is False

    def test_the_description_says_unattempted_readings_are_not_confirmed(self):
        def _post(_url, payload):
            if payload["method"] == "eth_getBlockByNumber":
                return {"result": {"number": "0x1f4"}}
            return {"error": {"code": -32005, "message": "rate limit exceeded"}}

        described = resample(ChainClient(ARCHIVE, post_json=_post), [reading()],
                             rng=random.Random(0)).describe()

        assert "neither confirms nor contradicts" in described
        assert "not counted as reproduced" in described

    def test_there_is_no_single_pass_rate(self):
        """A rate would have to pick a denominator, and both choices mislead."""

        from connectors.chain_verify import ResampleResult

        for forbidden in ("pass_rate", "success_rate", "reproducibility_rate", "score"):
            assert forbidden not in ResampleResult.__dataclass_fields__
            assert not hasattr(ResampleResult, forbidden)

    def test_an_unreliable_archive_provider_is_flagged_in_the_description(self):
        client = ChainClient(NO_ARCHIVE, post_json=responder())

        described = resample(client, [reading()], rng=random.Random(0)).describe()

        assert "opportunistic rather than a measurement" in described


class TestDivergenceIsAFinding:
    def test_a_changed_value_at_a_pinned_height_diverges(self):
        client = ChainClient(ARCHIVE, post_json=responder(value="0xdeadbeef"))

        result = resample(client, [reading(value="0x64")], rng=random.Random(0))

        assert result.outcomes[0].status == DIVERGED

    def test_divergence_is_reported_as_a_provider_problem_not_an_error(self):
        client = ChainClient(ARCHIVE, post_json=responder(value="0xdeadbeef"))

        described = resample(client, [reading(value="0x64")], rng=random.Random(0)).describe()

        assert "not serving the state it is being asked for" in described

    def test_divergence_blocks_the_reproducibility_claim(self):
        client = ChainClient(ARCHIVE, post_json=responder(value="0xdeadbeef"))

        result = resample(client, [reading(value="0x64")], rng=random.Random(0))

        assert result.establishes_reproducibility is False


class TestSampling:
    def test_sampling_is_random_not_first_n(self):
        """Re-running the first few would systematically check the readings taken
        earliest, which on a degrading walk are the least likely to be wrong."""

        pool = [reading(block=b) for b in range(100, 120)]
        client = ChainClient(ARCHIVE, post_json=responder())

        first = resample(client, pool, fraction=0.25, rng=random.Random(1))
        second = resample(client, pool, fraction=0.25, rng=random.Random(2))

        assert {o.block_number for o in first.outcomes} != {o.block_number for o in second.outcomes}

    def test_a_fraction_outside_the_unit_interval_is_refused(self):
        client = ChainClient(ARCHIVE, post_json=responder())

        for bad in (0, -0.5, 1.5):
            with pytest.raises(ValueError):
                resample(client, [reading()], fraction=bad)

    def test_an_empty_set_establishes_nothing(self):
        client = ChainClient(ARCHIVE, post_json=responder())

        result = resample(client, [], rng=random.Random(0))

        assert result.outcomes == ()
        assert result.establishes_reproducibility is False
