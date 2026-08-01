"""Burned is not locked, an empty search is not an absence, and 0.0049% is not zero.

CG-03 asks what supply is locked. Three ways to answer it wrongly, all represented here.

The registry ships empty because an earlier draft named lockers from memory. A wrong
locker address returns a zero balance and renders as "no locks found" -- silent, and
flattering to the token. So an unsearched registry says so, loudly.

Burned and locked are never summed. Burned supply cannot return; locked supply is
scheduled to. A holder asking what can hit the market needs the second number, not a total.

And a share formatter that rounds 0.0049% to "0.00%" tells a reader nothing is burned. That
is the sentinel defect again, produced by a format string.
"""
from __future__ import annotations

import pytest

from connectors.chain import ChainClient, ChainProvider
from connectors.chain_locks import (
    BURN_ADDRESSES,
    INDETERMINATE,
    LOCKER_REGISTRY,
    LOCKS_FOUND,
    NO_LOCK_CONTRACT_IDENTIFIED,
    RegisteredLocker,
    lock_finding,
    verify_locker,
)
from connectors.chain_queries import SELECTORS
from lib.shares import format_share

LOCK_ADDR = "0x" + "11" * 20
CAND_ADDR = "0x" + "22" * 20
NOTHING_ADDR = "0x" + "33" * 20

PROVIDER = ChainProvider(
    name="fake", url="https://example.test", chain="testnet",
    max_log_range=50, archive="yes", logs="yes",
)
EMPTY = "0x" + "0" * 64


def word(value):
    return "0x" + hex(value)[2:].rjust(64, "0")


def responder(supply=10**24, balances=None, block=900, code="0x60016000"):
    balances = balances or {}

    def _post(_url, payload):
        if payload["method"] == "eth_getBlockByNumber":
            return {"result": {"number": hex(block)}}
        if payload["method"] == "eth_getCode":
            return {"result": code}
        data = payload["params"][0]["data"]
        if data.startswith(SELECTORS["totalSupply"]):
            return {"result": word(supply)}
        if data.startswith(SELECTORS["balanceOf"]):
            holder = "0x" + data[-40:]
            for address, amount in balances.items():
                if address.lower() == holder.lower():
                    return {"result": word(amount)}
            return {"result": EMPTY}
        return {"result": EMPTY}

    return _post


class TestTheRegistryShipsEmpty:
    def test_no_locker_is_registered_by_default(self):
        """Addresses recalled rather than retrieved do not belong in the registry that
        decides whether supply is locked."""

        assert LOCKER_REGISTRY == ()

    def test_an_empty_registry_is_stated_in_the_finding(self):
        client = ChainClient(PROVIDER, post_json=responder())

        described = lock_finding(client, "0xtok").describe()

        assert "registry is EMPTY" in described
        assert "zero known lockers were searched" in described
        assert "establishes nothing about whether supply is locked" in described

    def test_a_registered_locker_is_searched(self):
        locker = RegisteredLocker(LOCK_ADDR, "example", "verified by test")
        client = ChainClient(PROVIDER, post_json=responder(balances={LOCK_ADDR: 500}))

        finding = lock_finding(client, "0xtok", registry=(locker,))

        assert finding.status == LOCKS_FOUND
        assert finding.locked_supply == 500
        assert finding.registry_size == 1

    def test_a_supplied_candidate_is_searched_and_labelled(self):
        client = ChainClient(PROVIDER, post_json=responder(balances={CAND_ADDR: 42}))

        finding = lock_finding(client, "0xtok", candidates=(CAND_ADDR,))

        assert finding.status == LOCKS_FOUND
        assert any("supplied candidate" in h.label for h in finding.locked)


class TestAbsenceIsNotUnlocked:
    def test_the_wording_never_claims_supply_is_unlocked(self):
        client = ChainClient(PROVIDER, post_json=responder())

        described = lock_finding(client, "0xtok").describe().lower()

        for overreach in ("unlocked", "no locks", "fully circulating", "freely tradable"):
            assert overreach not in described

    def test_the_search_scope_limit_is_stated(self):
        client = ChainClient(PROVIDER, post_json=responder())

        described = lock_finding(client, "0xtok").describe()

        assert "Top-holder enumeration is not available" in described

    def test_a_populated_registry_that_finds_nothing_says_what_it_searched(self):
        locker = RegisteredLocker(NOTHING_ADDR, "example", "verified by test")
        client = ChainClient(PROVIDER, post_json=responder())

        described = lock_finding(client, "0xtok", registry=(locker,)).describe()

        assert "would produce this same result" in described
        assert "unlocked" not in described.lower()


class TestBurnedIsNotLocked:
    def test_burned_and_locked_are_separate_fields(self):
        locker = RegisteredLocker(LOCK_ADDR, "example", "verified by test")
        client = ChainClient(PROVIDER, post_json=responder(
            balances={BURN_ADDRESSES[1]: 300, LOCK_ADDR: 700}))

        finding = lock_finding(client, "0xtok", registry=(locker,))

        assert finding.burned_supply == 300
        assert finding.locked_supply == 700

    def test_the_description_says_they_are_not_summed(self):
        locker = RegisteredLocker(LOCK_ADDR, "example", "verified by test")
        client = ChainClient(PROVIDER, post_json=responder(
            balances={BURN_ADDRESSES[1]: 300, LOCK_ADDR: 700}))

        described = lock_finding(client, "0xtok", registry=(locker,)).describe()

        assert "NOT summed" in described

    def test_burned_supply_is_described_as_unable_to_return(self):
        client = ChainClient(PROVIDER, post_json=responder(
            balances={BURN_ADDRESSES[1]: 300}))

        described = lock_finding(client, "0xtok").describe()

        assert "cannot return to circulation" in described


class TestOnlyAContractCanBeALocker:
    def test_a_contract_verifies(self):
        client = ChainClient(PROVIDER, post_json=responder(code="0x6080604052"))

        assert verify_locker(client, "0xcontract") is True

    def test_an_externally_owned_account_does_not(self):
        """A whale holding tokens is a person, not a lock. Registering one would report
        their balance as locked supply, which is wrong in the flattering direction."""

        client = ChainClient(PROVIDER, post_json=responder(code="0x"))

        assert verify_locker(client, "0xwhale") is False


class TestSmallIsNotZero:
    def test_a_tiny_nonzero_share_does_not_render_as_zero(self):
        """SHIB's burned supply is 0.0049% of total. At two decimal places that is
        "0.00%", which reads as nothing burned."""

        rendered = format_share(49_357_006_729_078_295_662_102_081_935,
                                999_982_329_478_393_982_378_038_372_706_779)

        assert rendered == "0.0049%"
        assert float(rendered.rstrip("%")) != 0

    def test_a_genuine_zero_renders_as_zero(self):
        assert format_share(0, 100) == "0%"

    def test_an_extremely_small_share_is_bounded_rather_than_rounded(self):
        assert format_share(1, 10**20) == "<0.00000001%"

    def test_an_ordinary_share_keeps_two_places(self):
        assert format_share(50, 100) == "50.00%"

    def test_a_zero_total_is_not_a_division(self):
        assert format_share(5, 0) == "n/a"


class TestAFailedProbeIsNotAnAbsence:
    def test_an_unreadable_supply_is_indeterminate(self):
        def _post(_url, payload):
            if payload["method"] == "eth_getBlockByNumber":
                return {"result": {"number": "0x1"}}
            return {"error": {"code": -32005, "message": "rate limit exceeded"}}

        finding = lock_finding(ChainClient(PROVIDER, post_json=_post), "0xtok")

        assert finding.status == INDETERMINATE

    def test_indeterminate_is_explicitly_not_a_finding_about_locks(self):
        def _post(_url, payload):
            if payload["method"] == "eth_getBlockByNumber":
                return {"result": {"number": "0x1"}}
            return {"error": {"code": -32005, "message": "rate limit exceeded"}}

        described = lock_finding(ChainClient(PROVIDER, post_json=_post), "0xtok").describe()

        assert "not a finding about how much supply is locked" in described
