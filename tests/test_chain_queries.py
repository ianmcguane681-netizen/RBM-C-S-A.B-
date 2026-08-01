"""An empty storage slot is not evidence that a contract is immutable.

USDC forced this design. Probing it with the EIP-1967 slots returns three empties, and
`implementation()` reverts, so both signals say "not a proxy". USDC is a proxy -- its
FiatTokenProxy predates EIP-1967 and uses the older OpenZeppelin slots, and being a
transparent proxy it reverts function probes from non-admin callers.

A CG-04 implementation that checked only EIP-1967 would report one of the largest tokens
in existence as immutable. That is a SEV-1 false negative, and it is the sentinel defect
this system has now met in three domains: a value meaning "I did not find it" being read
as "it is not there".

So the finding has three states and never a boolean, and NO_PATTERN_MATCHED is a statement
about the probes rather than about the contract.
"""
from __future__ import annotations

import pytest

from connectors.chain import ChainAccessError, ChainClient, ChainProvider
from connectors.chain_queries import (
    INDETERMINATE,
    NO_PATTERN_MATCHED,
    PROXY_SLOTS,
    REVERTED,
    SELECTORS,
    UPGRADEABLE,
    ZERO_ADDRESS,
    ProxyFinding,
    authority_holders,
    is_paused,
    proxy_finding,
    token_identity,
    total_supply,
)
from lib.http_retry import TransientRetrievalError

PROVIDER = ChainProvider(
    name="fake", url="https://example.test", chain="testnet",
    max_log_range=50, archive="yes",
)

EMPTY = "0x" + "0" * 64
USDC_IMPL = "0x43506849d7c04f9138d1a2050bbf3a0c054402dd"
USDC_ADMIN = "0x807a96288a1a408dbc13de2b1d087d10356395d2"


def slot_responder(values: dict[str, str], *, block: int = 1000):
    """Answer storage reads from a slot map; anything unlisted reads empty."""

    def _post(_url, payload):
        method = payload["method"]
        if method == "eth_getBlockByNumber":
            return {"result": {"number": hex(block)}}
        if method == "eth_getStorageAt":
            return {"result": values.get(payload["params"][1], EMPTY)}
        return {"result": EMPTY}

    return _post


def client_for(values, **kw):
    return ChainClient(PROVIDER, post_json=slot_responder(values, **kw))


class TestTheUSDCCase:
    """The test the module was written for. If this passes for the wrong reason the
    module is worthless, so it asserts the pattern that matched, not just the status."""

    def test_a_zeppelinos_proxy_is_found_despite_empty_eip1967_slots(self):
        finding = proxy_finding(
            client_for({
                PROXY_SLOTS["zeppelinos_implementation"]: "0x" + USDC_IMPL[2:].rjust(64, "0"),
                PROXY_SLOTS["zeppelinos_admin"]: "0x" + USDC_ADMIN[2:].rjust(64, "0"),
            }),
            "0xUSDC",
        )

        assert finding.status == UPGRADEABLE
        assert finding.implementation == USDC_IMPL
        assert finding.admin == USDC_ADMIN
        assert "zeppelinos_implementation" in finding.slots

    def test_an_eip1967_proxy_is_also_found(self):
        finding = proxy_finding(
            client_for({PROXY_SLOTS["eip1967_implementation"]: "0x" + "ab".rjust(64, "0")}),
            "0xother",
        )

        assert finding.status == UPGRADEABLE

    def test_a_beacon_proxy_counts_as_upgradeable(self):
        """A beacon holds the implementation elsewhere; the contract is still replaceable."""

        finding = proxy_finding(
            client_for({PROXY_SLOTS["eip1967_beacon"]: "0x" + "cd".rjust(64, "0")}),
            "0xbeacon",
        )

        assert finding.status == UPGRADEABLE

    def test_every_convention_is_probed_not_just_the_first(self):
        probed = []

        def _post(_url, payload):
            if payload["method"] == "eth_getBlockByNumber":
                return {"result": {"number": "0x1"}}
            probed.append(payload["params"][1])
            return {"result": EMPTY}

        proxy_finding(ChainClient(PROVIDER, post_json=_post), "0xany")

        assert set(probed) == set(PROXY_SLOTS.values())


class TestAbsenceIsNotImmutability:
    def test_all_slots_empty_reports_no_pattern_matched(self):
        finding = proxy_finding(client_for({}), "0xplain")

        assert finding.status == NO_PATTERN_MATCHED

    def test_the_wording_never_claims_immutability(self):
        """The single most important assertion in this file. A reviewer reading the
        description must not be able to quote it as evidence of immutability."""

        described = proxy_finding(client_for({}), "0xplain").describe().lower()

        assert "immutable" not in described
        assert "not upgradeable" not in described
        assert "not a proxy" not in described
        assert "would produce this same result" in described

    def test_the_description_says_how_many_conventions_were_probed(self):
        """So a reader can judge the strength of the absence rather than assume it."""

        assert str(len(PROXY_SLOTS)) in proxy_finding(client_for({}), "0xp").describe()


class TestAFailedProbeIsNotAnEmptyProbe:
    def test_a_transient_failure_yields_indeterminate(self):
        """Concluding 'no pattern' from probes that never ran would be a measurement over
        an incomplete numerator -- the defect EG-02 names."""

        def _post(_url, payload):
            if payload["method"] == "eth_getBlockByNumber":
                return {"result": {"number": "0x1"}}
            return {"error": {"code": -32005, "message": "rate limit exceeded"}}

        finding = proxy_finding(ChainClient(PROVIDER, post_json=_post), "0xany")

        assert finding.status == INDETERMINATE
        assert len(finding.unreachable) == len(PROXY_SLOTS)

    def test_indeterminate_is_explicitly_not_a_finding_of_immutability(self):
        finding = ProxyFinding(INDETERMINATE, "0xa", 10, {}, ("eip1967_admin",))

        assert "not a finding of immutability" in finding.describe()

    def test_a_partial_failure_still_reports_a_match_it_found(self):
        """A found proxy is a positive fact and does not become uncertain because some
        other convention could not be checked."""

        calls = {"n": 0}

        def _post(_url, payload):
            if payload["method"] == "eth_getBlockByNumber":
                return {"result": {"number": "0x1"}}
            calls["n"] += 1
            if payload["params"][1] == PROXY_SLOTS["zeppelinos_implementation"]:
                return {"result": "0x" + USDC_IMPL[2:].rjust(64, "0")}
            if calls["n"] % 2 == 0:
                return {"error": {"code": -32005, "message": "rate limit exceeded"}}
            return {"result": EMPTY}

        finding = proxy_finding(ChainClient(PROVIDER, post_json=_post), "0xusdc")

        assert finding.status == UPGRADEABLE
        assert finding.implementation == USDC_IMPL
        assert finding.unreachable


class TestRevertedIsNotRenounced:
    def call_responder(self, answers):
        def _post(_url, payload):
            if payload["method"] == "eth_getBlockByNumber":
                return {"result": {"number": "0x1"}}
            selector = payload["params"][0]["data"][:10]
            result = answers.get(selector)
            if result is None:
                return {"error": {"code": 3, "message": "execution reverted"}}
            return {"result": result}

        return _post

    def test_a_missing_function_reports_reverted(self):
        """WBTC has no masterMinter(). That is not the same as having one set to zero."""

        client = ChainClient(PROVIDER, post_json=self.call_responder(
            {SELECTORS["owner"]: "0x" + "11".rjust(64, "0")}))

        holders = authority_holders(client, "0xwbtc")

        assert holders["masterMinter"] == REVERTED
        assert holders["owner"] != REVERTED

    def test_a_renounced_owner_reports_the_zero_address(self):
        """The distinction that matters commercially: renouncing ownership is a real act
        a project can point to, and it must not be creditable by accident."""

        client = ChainClient(PROVIDER, post_json=self.call_responder(
            {SELECTORS["owner"]: EMPTY}))

        assert authority_holders(client, "0xrenounced")["owner"] == ZERO_ADDRESS

    def test_reverted_and_zero_are_different_values(self):
        assert REVERTED != ZERO_ADDRESS

    def test_an_unpausable_contract_reports_reverted_not_false(self):
        """'false' means transfers are running. 'REVERTED' means there is no pause
        function at all. A holder cares about the difference."""

        client = ChainClient(PROVIDER, post_json=self.call_responder({}))

        assert is_paused(client, "0xnopause") == REVERTED

    def test_a_paused_contract_reports_true(self):
        client = ChainClient(PROVIDER, post_json=self.call_responder(
            {SELECTORS["paused"]: "0x" + "1".rjust(64, "0")}))

        assert is_paused(client, "0xpaused") == "true"


class TestSupplyAndIdentityCarryProvenance:
    def responder(self, answers, block=777):
        def _post(_url, payload):
            if payload["method"] == "eth_getBlockByNumber":
                return {"result": {"number": hex(block)}}
            selector = payload["params"][0]["data"][:10]
            if selector not in answers:
                return {"error": {"code": 3, "message": "execution reverted"}}
            return {"result": answers[selector]}

        return _post

    def test_supply_carries_its_block_height(self):
        client = ChainClient(PROVIDER, post_json=self.responder(
            {SELECTORS["totalSupply"]: "0x" + "64".rjust(64, "0")}))

        reading = total_supply(client, "0xtoken")

        assert reading.block_number == 777
        assert reading.provenance()["kind"] == "CHAIN_STATE"

    def test_decimals_is_read_not_assumed(self):
        """USDC is 6 and WBTC is 8. A supply divided by the wrong power of ten is wrong by
        orders of magnitude while looking entirely plausible."""

        client = ChainClient(PROVIDER, post_json=self.responder(
            {SELECTORS["decimals"]: "0x" + "6".rjust(64, "0")}))

        identity = token_identity(client, "0xusdc")

        assert int(identity["decimals"].value, 16) == 6

    def test_missing_optional_metadata_is_absent_rather_than_defaulted(self):
        """A token without name() is not malformed, and inventing one would be a claim."""

        client = ChainClient(PROVIDER, post_json=self.responder(
            {SELECTORS["decimals"]: "0x" + "12".rjust(64, "0")}))

        identity = token_identity(client, "0xminimal")

        assert "name" not in identity
        assert "symbol" not in identity
        assert "decimals" in identity
