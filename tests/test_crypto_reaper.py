"""It produces something to sign and has no way to sign it, twice over.

`lib.reaper.NEVER_AUTONOMOUS` refuses autonomous placement for this lane, which is a policy.
`connectors/chain_exec` has no key path, no signing library and no send method, which is not
— and that second refusal is the one that survives somebody changing their mind about the
first at eleven at night.

The cascade's ordering is the other property under test. It asks whether the token can be
SOLD before it asks what the position costs, because a token that quotes on the buy leg and
not the sell leg is the sharpest finding the chain connectors produce and any ordering that
prices it first risks putting a number on something there is no way out of.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from connectors.chain_costs import INDETERMINATE as TRIP_INDETERMINATE
from connectors.chain_costs import NO_ROUTE, PRICED, RoundTrip
from connectors.chain_exec import SigningRefused, SwapPlan
from connectors.chain_queries import (
    INDETERMINATE as PROXY_INDETERMINATE,
    NO_PATTERN_MATCHED,
    ProxyFinding,
    UPGRADEABLE,
)
from lib.candidates import INDETERMINATE, REFUSED, SURFACED
from lib.crypto_reaper import (
    QUOTE_DECIMALS,
    Subject,
    build_crypto_reaper,
    gates_for,
    screen_subject,
)
from lib.reaper import COULD_NOT_LOOK, INDETERMINATE as HARVEST_INDETERMINATE
from lib.reaper import READY, REFUSED as HARVEST_REFUSED
from lib.thesis import Thesis
from tests.test_chain_exec import AMOUNT, USDC, WALLET, Client, amounts_out, word

TOKEN = "0x2222222222222222222222222222222222222222"
STAKE = 100 * 10**6          # 100 USDC


def identity():
    return {"symbol": type("R", (), {"value": "TKN"})(),
            "decimals": type("R", (), {"value": 18})()}


def proxy(status=NO_PATTERN_MATCHED, unreachable=()):
    return ProxyFinding(status, TOKEN, 25_000_000, {}, unreachable)


def trip(status=PRICED, spent=STAKE, returned=None, gas=25 * 10**9, reason=""):
    return RoundTrip(
        status, TOKEN, USDC, "USDC", 25_000_000,
        spent=spent,
        tokens_received=10**18,
        returned=int(spent * 0.98) if returned is None else returned,
        entry_venue="uniswap-v2/USDC", exit_venue="uniswap-v2/USDC",
        gas_price_wei=gas, reason=reason,
    )


def subject(**kw):
    return Subject(
        TOKEN, kw.pop("stake_units", STAKE), "USDC",
        identity=kw.pop("identity", identity()),
        proxy=kw.pop("proxy", proxy()),
        trip=kw.pop("trip", trip()),
        **kw,
    )


def thesis(limit=100.0):
    return Thesis(
        TOKEN, "Ian McGuane", "I want to hold this and here is why",
        ("the code can be replaced", "the pool can be drained"),
        "2026-08-02T09:00:00Z",
        (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(timespec="seconds"),
        limit, currency="USD",
    )


class Register:
    def __init__(self, held=None, readable=True):
        self.held, self.readable = held or {}, readable
        self.reason = "" if readable else "JSONDecodeError: line 1"

    def current(self, name):
        return self.held.get(name)


class TestSoldBeforePriced:
    def test_a_token_that_cannot_be_sold_is_refused(self):
        screened = screen_subject(subject(trip=trip(
            status=NO_ROUTE, reason="the buy leg quoted and the sell leg did not")))

        assert screened.verdict == REFUSED
        assert screened.decided_by.name == "there is a way out"
        assert "it is a donation" in screened.decided_by.detail

    def test_the_exit_question_comes_before_the_cost_question(self):
        names = [s.name for s in screen_subject(subject()).stages]

        assert names.index("there is a way out") < names.index(
            "the round trip is affordable")

    def test_an_unpriced_round_trip_is_indeterminate_not_cheap(self):
        screened = screen_subject(subject(trip=trip(
            status=TRIP_INDETERMINATE, reason="no venue answered")))

        assert screened.verdict == INDETERMINATE
        assert "not a finding that the trade is cheap" in screened.decided_by.detail

    def test_cost_is_unknown_rather_than_zero_when_the_trip_did_not_price(self):
        stage = next(s for s in screen_subject(
            subject(trip=trip(status=NO_ROUTE))).stages
            if s.name == "the round trip is affordable")

        assert stage.verdict == INDETERMINATE


class TestTheRoundTripCeiling:
    def test_an_expensive_round_trip_is_refused_on_the_breakeven_move(self):
        """Not the round-trip loss: losing 5% needs 5.26% back to be level."""

        screened = screen_subject(subject(trip=trip(returned=int(STAKE * 0.85))))

        assert screened.verdict == REFUSED
        assert "before the position is level" in screened.decided_by.detail

    def test_a_cheap_round_trip_surfaces(self):
        assert screen_subject(subject()).verdict == SURFACED

    def test_the_ceiling_can_be_raised(self):
        screened = screen_subject(subject(trip=trip(returned=int(STAKE * 0.85))),
                                  max_breakeven_move_pct=25.0)

        assert screened.verdict == SURFACED


class TestUpgradeabilityStopsTheLane:
    def test_an_upgradeable_contract_is_refused(self):
        screened = screen_subject(subject(proxy=ProxyFinding(
            UPGRADEABLE, TOKEN, 25_000_000, {"eip1967_implementation": "0x" + "3" * 40})))

        assert screened.verdict == REFUSED
        assert "no board is watching this" in screened.decided_by.detail

    def test_an_unprobed_contract_is_indeterminate_not_immutable(self):
        screened = screen_subject(subject(proxy=proxy(
            status=PROXY_INDETERMINATE, unreachable=("eip1967_implementation",))))

        assert screened.verdict == INDETERMINATE
        assert "not a finding of immutability" in screened.decided_by.detail

    def test_no_proxy_object_at_all_is_also_indeterminate(self):
        assert screen_subject(subject(proxy=None)).verdict == INDETERMINATE

    def test_no_pattern_matched_passes_without_claiming_immutability(self):
        stage = next(s for s in screen_subject(subject()).stages
                     if s.name == "the code cannot be swapped under you")

        assert "would produce this same result" in stage.detail


class TestTheContractMustAnswer:
    def test_nothing_read_is_indeterminate_not_an_empty_address(self):
        screened = screen_subject(subject(identity=None, reason="TimeoutError: 30s"))

        assert screened.verdict == INDETERMINATE
        assert "Not a finding that the address is empty" in screened.decided_by.detail

    def test_the_symbol_is_carried_when_it_was_read(self):
        assert screen_subject(subject()).stages[0].detail.endswith("symbol TKN")


class TestTheGates:
    def test_an_unread_gas_price_blocks(self):
        readings = gates_for(subject(trip=trip(gas=0)))

        assert readings[0].status == "GAS_PRICE_NOT_READ"
        assert readings[0].blocking

    def test_an_unreadable_portfolio_blocks(self):
        lost = type("P", (), {"readable": False})()

        assert gates_for(subject(), portfolio=lost)[0].status == "PORTFOLIO_UNREADABLE"

    def test_a_clean_subject_produces_nothing(self):
        assert gates_for(subject()) == ()


class TestTheLaneEndToEnd:
    class Chain(Client):
        """The chain_exec fake, plus the reads token_identity/proxy/round_trip need."""

        def __init__(self, *, sellable=True, **kw):
            super().__init__(**kw)
            self.sellable = sellable

    def _breakers(self, tmp_path, balance=20_000.0):
        from lib.breakers import Breakers, Ringfence

        return Breakers(Ringfence("crypto", balance), tmp_path / "b.json",
                        kill_switch=tmp_path / "HALT")

    def _reaper(self, tmp_path, *, register=None, chain=None, **kw):
        return build_crypto_reaper(
            watchlist=(TOKEN,),
            theses=register if register is not None else Register({TOKEN: thesis()}),
            breakers=self._breakers(tmp_path, balance=kw.pop("balance", 20_000.0)),
            wallet=WALLET,
            client=chain if chain is not None else self.Chain(),
            now=lambda: 1_800_000_000, **kw)

    def _patched(self, monkeypatch, *, ident=None, prox=None, tr=None):
        import connectors.chain_queries as queries
        import connectors.chain_costs as costs

        monkeypatch.setattr(queries, "token_identity",
                            lambda *_a, **_k: identity() if ident is None else ident)
        monkeypatch.setattr(queries, "proxy_finding",
                            lambda *_a, **_k: proxy() if prox is None else prox)
        monkeypatch.setattr(costs, "round_trip",
                            lambda *_a, **_k: trip() if tr is None else tr)

    def test_it_reaches_ready_with_an_unsigned_plan(self, tmp_path, monkeypatch):
        self._patched(monkeypatch)

        harvest = self._reaper(tmp_path).reap()[0]

        assert harvest.status == READY
        assert isinstance(harvest.instruction, SwapPlan)

    def test_the_ready_instruction_still_refuses_to_be_signed(self, tmp_path, monkeypatch):
        self._patched(monkeypatch)

        harvest = self._reaper(tmp_path).reap()[0]

        with pytest.raises(SigningRefused):
            harvest.instruction.sign()

    def test_the_plan_carries_a_floor(self, tmp_path, monkeypatch):
        self._patched(monkeypatch)

        plan = self._reaper(tmp_path).reap()[0].instruction

        assert plan.min_out > 0
        assert plan.min_out < plan.quoted_out

    def test_autonomous_execution_cannot_be_switched_on(self, tmp_path, monkeypatch):
        """Belt: the policy. The braces are that the adapter has no way to sign."""

        from dataclasses import replace

        self._patched(monkeypatch)

        with pytest.raises(ValueError, match="irreversible"):
            replace(self._reaper(tmp_path), autonomous_execution=True)

    def test_a_token_with_no_thesis_is_refused_not_minted_one(self, tmp_path, monkeypatch):
        """Unlike arb: holding a token is entirely a view about that token."""

        self._patched(monkeypatch)

        harvest = self._reaper(tmp_path, register=Register({})).reap()[0]

        assert harvest.status == HARVEST_REFUSED

    def test_an_unreadable_thesis_register_could_not_look(self, tmp_path, monkeypatch):
        self._patched(monkeypatch)

        harvest = self._reaper(tmp_path, register=Register(readable=False)).reap()[0]

        assert harvest.status == COULD_NOT_LOOK
        assert "unknown rather than nothing" in harvest.reason

    def test_no_chain_client_is_could_not_look(self, tmp_path):
        reaper = build_crypto_reaper(
            watchlist=(TOKEN,), theses=Register({TOKEN: thesis()}),
            breakers=self._breakers(tmp_path), wallet=WALLET, client=None)

        harvest = reaper.reap()[0]

        assert harvest.status == COULD_NOT_LOOK
        assert "not a finding that the tokens are untradeable" in harvest.reason

    def test_an_unsellable_token_is_refused(self, tmp_path, monkeypatch):
        self._patched(monkeypatch, tr=trip(status=NO_ROUTE, reason="sell leg silent"))

        harvest = self._reaper(tmp_path).reap()[0]

        assert harvest.status == HARVEST_REFUSED
        assert "there is a way out" in harvest.reason

    def test_a_failed_chain_read_is_could_not_look_for_the_only_token(self, tmp_path,
                                                                      monkeypatch):
        import connectors.chain_queries as queries

        monkeypatch.setattr(queries, "token_identity", _raise)

        harvest = self._reaper(tmp_path).reap()[0]

        assert harvest.status == COULD_NOT_LOOK

    def test_the_kill_switch_stops_a_clean_token(self, tmp_path, monkeypatch):
        self._patched(monkeypatch)
        (tmp_path / "HALT").write_text("stop", encoding="utf-8")

        harvest = self._reaper(tmp_path).reap()[0]

        assert harvest.status == HARVEST_REFUSED
        assert "kill switch" in harvest.reason

    def test_the_stake_over_the_ringfence_cap_is_refused_after_planning(self, tmp_path,
                                                                       monkeypatch):
        self._patched(monkeypatch)

        harvest = self._reaper(tmp_path, balance=100.0).reap()[0]

        assert harvest.status == HARVEST_REFUSED
        assert "position size" in harvest.reason

    def test_the_breakers_see_the_stake_in_currency_not_in_raw_units(self, tmp_path,
                                                                     monkeypatch):
        """100 USDC is 100, not 100,000,000. The connectors compared raw amounts once."""

        self._patched(monkeypatch)

        plan = self._reaper(tmp_path).reap()[0].instruction

        assert plan.amount_in / 10**QUOTE_DECIMALS["USDC"] == 100.0


def _raise(*_args, **_kwargs):
    raise RuntimeError("node down")
