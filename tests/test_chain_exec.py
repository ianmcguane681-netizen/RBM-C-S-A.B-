"""It computes the transaction to the last byte and it cannot sign it.

The refusal is structural rather than configured: there is no key path, no signing library
and no send method, and `sign()` raises whatever you hand it. A policy is a thing somebody
changes at eleven at night; an absent capability is not.

Two properties carry the rest. `amountOutMin` is computed from a live quote and floored, so
rounding never lands on the permissive side — a swap broadcast without a floor is not a
tail risk, it is a business somebody runs. And the allowance is READ: assuming none wastes
an approval, assuming enough produces a swap that reverts after the approval step was
skipped, so neither is assumed and an unreadable allowance refuses the plan.
"""
from __future__ import annotations

import pytest

from connectors.chain import ChainAccessError, ChainReading
from connectors.chain_exec import (
    MAX_SLIPPAGE_BPS,
    NOT_BUILDABLE,
    REFUSED,
    SELECTORS,
    UNISWAP_V2_ROUTER,
    UNSIGNED,
    SigningRefused,
    SwapPlan,
    build_swap_plan,
    decode_amounts_out,
    encode_approve,
    encode_swap,
)
from lib.thesis import PERMITTED, Permission

USDC = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
WETH = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
WALLET = "0x1111111111111111111111111111111111111111"
AMOUNT = 1_000_000_000          # 1,000 USDC at 6 decimals


def word(value: int) -> str:
    return hex(value)[2:].rjust(64, "0")


def amounts_out(*values: int) -> str:
    return "0x" + word(0x20) + word(len(values)) + "".join(word(v) for v in values)


class Client:
    """Enough of ChainClient to exercise every path, counting what was asked."""

    def __init__(self, *, quote=None, allowance=0, chain_id=1, nonce=7,
                 gas_price=25 * 10**9, read_raises=None, allowance_raises=False,
                 call_raises=False):
        self.quote = amounts_out(AMOUNT, 300_000_000_000_000_000) if quote is None else quote
        self.allowance = allowance
        self.chain_id, self.nonce, self.gas_price = chain_id, nonce, gas_price
        self.read_raises = read_raises
        self.allowance_raises = allowance_raises
        self.call_raises = call_raises
        self.reads: list[str] = []

    def read(self, method, params, **_kw):
        data = params[0]["data"]
        self.reads.append(data[:10])
        if self.read_raises and data.startswith(SELECTORS["getAmountsOut"]):
            raise self.read_raises
        if data.startswith(SELECTORS["allowance"]):
            if self.allowance_raises:
                raise ChainAccessError("archive refused")
            value = hex(self.allowance)
        else:
            value = self.quote
        return ChainReading(value, "ethereum", 25_000_000, method, params, "test", "t")

    def call(self, method, params=None):
        if self.call_raises:
            raise ChainAccessError("node down")
        return {"eth_chainId": hex(self.chain_id),
                "eth_getTransactionCount": hex(self.nonce),
                "eth_gasPrice": hex(self.gas_price)}[method]


def plan(client=None, **kw):
    return build_swap_plan(
        client or Client(), wallet=WALLET, token_in=USDC, token_out=WETH,
        amount_in=kw.pop("amount_in", AMOUNT), now=lambda: 1_800_000_000, **kw)


class TestItCannotSign:
    def test_the_plan_refuses_to_sign(self):
        with pytest.raises(SigningRefused):
            plan().sign()

    def test_a_step_refuses_to_sign(self):
        with pytest.raises(SigningRefused, match="atomic and irreversible"):
            plan().steps[0].sign()

    def test_send_is_the_same_refusal_rather_than_a_way_round_it(self):
        with pytest.raises(SigningRefused):
            plan().steps[0].send()

    def test_broadcast_is_too(self):
        with pytest.raises(SigningRefused):
            plan().steps[0].broadcast()

    def test_the_module_imports_no_signing_or_key_material(self):
        """Structural, not configured. The capability is absent, not switched off."""

        from pathlib import Path

        source = Path("connectors/chain_exec.py").read_text(encoding="utf-8")

        for forbidden in ("private_key", "eth_sendRawTransaction", "eth_sendTransaction",
                          "eth_account", "PRIVATE_KEY", "mnemonic"):
            assert forbidden not in source, forbidden

    def test_the_output_says_nothing_was_signed_or_sent(self):
        described = plan().describe()

        assert "NOTHING HAS BEEN SIGNED AND NOTHING HAS BEEN SENT" in described


class TestTheFloorIsTheWholePoint:
    def test_min_out_is_computed_from_the_quote_and_the_tolerance(self):
        built = plan(slippage_bps=50)

        assert built.quoted_out == 300_000_000_000_000_000
        assert built.min_out == 298_500_000_000_000_000

    def test_it_is_floored_so_rounding_never_favours_the_swap(self):
        built = build_swap_plan(
            Client(quote=amounts_out(AMOUNT, 999)), wallet=WALLET, token_in=USDC,
            token_out=WETH, amount_in=AMOUNT, slippage_bps=33, now=lambda: 0)

        assert built.min_out == 999 * 9967 // 10_000 == 995

    def test_the_floor_is_in_the_swap_calldata(self):
        built = plan()
        swap = built.steps[-1]

        assert word(built.min_out) in swap.data

    def test_zero_tolerance_is_refused_as_no_room_to_move(self):
        assert plan(slippage_bps=0).status == REFUSED

    def test_a_wide_tolerance_is_refused_as_a_blank_cheque(self):
        built = plan(slippage_bps=MAX_SLIPPAGE_BPS + 1)

        assert built.status == REFUSED
        assert "blank cheque" in built.reason

    def test_a_floor_that_rounds_to_zero_refuses_rather_than_shipping_unprotected(self):
        built = build_swap_plan(
            Client(quote=amounts_out(AMOUNT, 1)), wallet=WALLET, token_in=USDC,
            token_out=WETH, amount_in=AMOUNT, slippage_bps=MAX_SLIPPAGE_BPS,
            now=lambda: 0)

        assert built.status == NOT_BUILDABLE
        assert "no protection at all" in built.reason

    def test_what_is_at_risk_inside_the_tolerance_is_stated(self):
        built = plan(slippage_bps=50)

        assert built.tolerated_loss == 1_500_000_000_000_000
        assert "units at risk" in built.describe()


class TestTheAllowanceIsReadNotAssumed:
    def test_a_short_allowance_produces_an_exact_amount_approval(self):
        built = plan(Client(allowance=0))

        assert len(built.steps) == 2
        assert built.steps[0].data == encode_approve(UNISWAP_V2_ROUTER, AMOUNT)

    def test_the_approval_is_never_unlimited(self):
        built = plan(Client(allowance=0))

        assert word(2**256 - 1) not in built.steps[0].data
        assert "Never unlimited" in built.describe()

    def test_a_sufficient_allowance_skips_the_approval(self):
        built = plan(Client(allowance=AMOUNT * 2))

        assert len(built.steps) == 1
        assert built.steps[0].to == UNISWAP_V2_ROUTER

    def test_an_unreadable_allowance_refuses_rather_than_guessing_either_way(self):
        built = plan(Client(allowance_raises=True))

        assert built.status == NOT_BUILDABLE
        assert "Not a finding that it is zero" in built.reason
        assert "not a finding that it is sufficient" in built.reason

    def test_the_nonces_increment_across_the_steps(self):
        built = plan(Client(allowance=0, nonce=7))

        assert [step.nonce for step in built.steps] == [7, 8]


class TestNothingIsDefaulted:
    def test_an_unquotable_route_is_not_buildable(self):
        built = plan(Client(read_raises=ChainAccessError("no such pair")))

        assert built.status == NOT_BUILDABLE
        assert "not a finding that the swap is" in built.describe()

    def test_an_empty_amounts_array_is_not_a_zero_output(self):
        built = plan(Client(quote="0x"))

        assert built.status == NOT_BUILDABLE
        assert "not about whether the token trades" in built.reason

    def test_an_unreadable_nonce_or_gas_price_refuses_the_whole_plan(self):
        built = plan(Client(call_raises=True))

        assert built.status == NOT_BUILDABLE
        assert "replaces one you did not mean to replace" in built.reason

    def test_a_zero_gas_price_is_a_measurement_failure_not_a_free_block(self):
        built = plan(Client(gas_price=0))

        assert built.status == NOT_BUILDABLE
        assert "rather than a free block" in built.reason

    def test_the_block_the_quote_came_from_is_recorded(self):
        assert plan().block_number == 25_000_000


class TestPermissionIsCheckedBeforeAnythingIsRead:
    def _refused(self):
        return Permission("REFUSED", "a token", ())

    def test_an_unpermitted_swap_is_refused(self):
        built = plan(permission=self._refused())

        assert built.status == REFUSED
        assert "still a transaction somebody may sign" in built.reason

    def test_no_chain_call_is_made_for_one(self):
        client = Client()

        plan(client, permission=self._refused())

        assert client.reads == []

    def test_a_permitted_one_proceeds(self):
        built = plan(permission=Permission(PERMITTED, "a token", ()))

        assert built.status == UNSIGNED


class TestTheEncodingRoundTrips:
    def test_the_swap_selector_and_array_offset_are_right(self):
        data = encode_swap(1, 2, (USDC, WETH), WALLET, 99)

        assert data.startswith(SELECTORS["swapExactTokensForTokens"])
        # Five head words, so the tail starts at 0xA0.
        assert data[10 + 128:10 + 192] == word(0xA0)

    def test_the_path_is_carried_in_order(self):
        data = encode_swap(1, 2, (USDC, WETH), WALLET, 99)

        assert data.index(USDC.lower()[2:]) < data.index(WETH.lower()[2:])

    def test_decoding_an_amounts_array(self):
        assert decode_amounts_out(amounts_out(5, 9)) == (5, 9)

    def test_a_truncated_return_decodes_to_nothing_rather_than_a_guess(self):
        assert decode_amounts_out("0x" + word(0x20)) == ()

    def test_a_length_longer_than_the_payload_decodes_to_nothing(self):
        assert decode_amounts_out("0x" + word(0x20) + word(9) + word(1)) == ()


class TestTheDeadlineIsPresent:
    def test_it_is_the_stated_window_past_now(self):
        assert plan(deadline_seconds=600).deadline == 1_800_000_600

    def test_it_is_in_the_calldata(self):
        built = plan(deadline_seconds=600)

        assert word(built.deadline) in built.steps[-1].data

    def test_the_description_says_what_it_is_for(self):
        assert "reverts rather than" in plan().describe()


class TestTheWalletFields:
    def test_every_field_is_hex_for_pasting_into_a_wallet(self):
        fields = plan().steps[-1].as_wallet_fields()

        assert all(str(v).startswith("0x") for v in fields.values())
        assert fields["to"] == UNISWAP_V2_ROUTER

    def test_the_recipient_of_the_swap_is_the_wallet_itself(self):
        assert WALLET.lower()[2:] in plan().steps[-1].data

    def test_a_self_swap_is_refused(self):
        built = build_swap_plan(Client(), wallet=WALLET, token_in=USDC, token_out=USDC,
                                amount_in=AMOUNT)

        assert built.status == REFUSED

    def test_a_non_positive_amount_is_refused(self):
        assert plan(amount_in=0).status == REFUSED
