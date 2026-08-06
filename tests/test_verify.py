"""A rejected key and an unreachable service are not the same finding.

Both leave you without an answer and only one is about the credential. Reporting a timeout
as a bad key sends a person to regenerate a key that was fine, watch the new one "fail" the
same way, and conclude the system is broken — the founding defect of this repository,
applied to the moment somebody first places a credential.

So a 401 is REFUSED and everything else is COULD_NOT_REACH, including a 500: the venue's
server breaking says nothing about the key. The other properties here are about what
verifying must not cost. Confirming the odds key must not spend the quota it was placed to
use, and confirming the broker key must not place anything — not a dry run, not an order
that is cancelled afterwards. No order path is imported by that command at all.
"""
from __future__ import annotations

import urllib.error

import pytest

import verify
from verify import CONFIRMED, COULD_NOT_REACH, NOT_CONFIGURED, REFUSED


class FakeBroker:
    def __init__(self, *, configured=True, paper=True, account_raises=None, open_now=True):
        self.is_configured = configured
        self.is_paper = paper
        self._raises = account_raises
        self._open = open_now

    def account(self):
        if self._raises:
            raise self._raises
        return {"status": "ACTIVE", "cash": "100000.00", "currency": "USD"}

    def is_market_open(self):
        return self._open


def _broker(monkeypatch, broker):
    import connectors.alpaca

    monkeypatch.setattr(connectors.alpaca.AlpacaBroker, "from_directory",
                        classmethod(lambda cls, *a, **kw: broker))


class TestARejectedKeyIsNotAnUnreachableService:
    def test_a_401_is_the_credential_being_wrong(self, monkeypatch):
        _broker(monkeypatch, FakeBroker(account_raises=urllib.error.HTTPError(
            "https://paper-api.alpaca.markets/v2/account", 401, "Unauthorized", {}, None)))

        check = verify.check_alpaca()[0]

        assert check.status == REFUSED
        assert "regenerate" in check.action

    def test_a_network_failure_says_nothing_about_the_credential(self, monkeypatch):
        _broker(monkeypatch, FakeBroker(account_raises=OSError("connection reset")))

        check = verify.check_alpaca()[0]

        assert check.status == COULD_NOT_REACH
        assert "may be perfectly good" in check.action

    def test_a_broken_server_at_the_venue_does_not_blame_the_key(self, monkeypatch):
        """A 500 is their outage. Calling it REFUSED costs somebody an afternoon."""

        _broker(monkeypatch, FakeBroker(account_raises=urllib.error.HTTPError(
            "https://paper-api.alpaca.markets/v2/account", 500, "Server Error", {}, None)))

        assert verify.check_alpaca()[0].status == COULD_NOT_REACH

    def test_an_absent_credential_is_not_a_failed_one(self, monkeypatch):
        _broker(monkeypatch, FakeBroker(configured=False))

        assert verify.check_alpaca()[0].status == NOT_CONFIGURED


class TestTheEnvironmentIsShoutedRatherThanMentioned:
    def test_a_live_account_says_live_money_in_the_detail(self, monkeypatch):
        """The base URLs differ by one word and nobody finds this mistake afterwards."""

        _broker(monkeypatch, FakeBroker(paper=False))

        assert "LIVE MONEY" in verify.check_alpaca()[0].detail

    def test_a_paper_account_is_named_as_paper(self, monkeypatch):
        _broker(monkeypatch, FakeBroker(paper=True))

        detail = verify.check_alpaca()[0].detail

        assert "PAPER" in detail and "LIVE MONEY" not in detail

    def test_an_unreadable_clock_is_reported_rather_than_assumed_shut(self, monkeypatch):
        _broker(monkeypatch, FakeBroker(open_now=None))

        clock = verify.check_alpaca()[1]

        assert clock.status == COULD_NOT_REACH
        assert "STALE" in clock.detail


class TestVerifyingCostsNothing:
    class FakeOdds:
        def __init__(self, *, configured=True, raises=None):
            self.is_configured = configured
            self._raises = raises
            self.quotes_called = False
            from connectors.oddsapi import Usage

            self.usage = Usage(437, 63, 2)

        def sports(self):
            if self._raises:
                raise self._raises
            return ("soccer_epl", "basketball_nba")

        def quotes(self, *a, **kw):        # pragma: no cover - the point is it is unused
            self.quotes_called = True
            raise AssertionError("verifying a key must not spend a credit")

    def _odds(self, monkeypatch, source):
        import connectors.oddsapi

        monkeypatch.setattr(connectors.oddsapi.OddsApiSource, "from_directory",
                            classmethod(lambda cls, *a, **kw: source))

    def test_the_odds_key_is_confirmed_without_spending_a_credit(self, monkeypatch):
        source = self.FakeOdds()
        self._odds(monkeypatch, source)

        check = verify.check_odds()[0]

        assert check.status == CONFIRMED
        assert source.quotes_called is False
        assert "no credit was spent" in check.detail

    def test_the_remaining_quota_is_reported_from_the_same_call(self, monkeypatch):
        self._odds(monkeypatch, self.FakeOdds())

        assert "437 credit(s) remain" in verify.check_odds()[0].detail

    def test_an_unmeasured_quota_is_unknown_rather_than_plentiful(self, monkeypatch):
        from connectors.oddsapi import Usage

        source = self.FakeOdds()
        source.usage = Usage()
        self._odds(monkeypatch, source)

        assert "UNKNOWN rather than plentiful" in verify.check_odds()[0].detail

    def test_a_revoked_odds_key_is_refused_rather_than_unreachable(self, monkeypatch):
        self._odds(monkeypatch, self.FakeOdds(raises=urllib.error.HTTPError(
            "https://api.the-odds-api.com/v4/sports", 401, "Unauthorized", {}, None)))

        assert verify.check_odds()[0].status == REFUSED

    def test_no_order_path_is_reachable_from_this_command(self):
        """Not a dry run, not a cancelled order. The module never imports one."""

        source = (verify.__file__ and open(verify.__file__, encoding="utf-8").read())

        assert "lib.placing" not in source
        assert "place_harvest" not in source
        assert "Instruction" not in source


class TestTheExitCodeSeparatesNothingToCheckFromSomethingWrong:
    def _all(self, monkeypatch, *, broker, odds_configured=False):
        import connectors.oddsapi

        _broker(monkeypatch, broker)
        monkeypatch.setattr(
            connectors.oddsapi.OddsApiSource, "from_directory",
            classmethod(lambda cls, *a, **kw: TestVerifyingCostsNothing.FakeOdds(
                configured=odds_configured)))
        monkeypatch.delenv("QUICKNODE_ETHEREUM_URL", raising=False)
        return verify.run()

    def test_nothing_configured_exits_two(self, monkeypatch):
        _, code = self._all(monkeypatch, broker=FakeBroker(configured=False))

        assert code == 2

    def test_everything_present_and_accepted_exits_zero(self, monkeypatch):
        _, code = self._all(monkeypatch, broker=FakeBroker())

        assert code == 0

    def test_a_configured_credential_that_failed_exits_one(self, monkeypatch):
        _, code = self._all(monkeypatch, broker=FakeBroker(
            account_raises=OSError("connection reset")))

        assert code == 1


class TestCredentialModesAreCheckedAfterTheScriptHasRun:
    """`setup-credentials.sh` writes 600 and nothing ever looked again.

    A key placed by hand, restored from a backup that flattened the modes, or copied with
    `cp` is read without a word, and the file looks identical either way. This reports and
    does not block: a permission bit is not a limit that cannot be read, and halting the
    research lanes over one would aim the refusal at the wrong thing.
    """

    def _secret(self, tmp_path, mode):
        directory = tmp_path / ".alpaca"
        directory.mkdir(exist_ok=True)
        path = directory / "key_id"
        path.write_text("PK-not-a-real-key", encoding="utf-8")
        path.chmod(mode)
        return path

    def test_a_private_key_produces_no_finding(self, tmp_path):
        from lib.credentials import exposed

        self._secret(tmp_path, 0o600)

        assert exposed(tmp_path) == ()

    def test_a_world_readable_key_is_named_with_the_command_that_fixes_it(self, tmp_path):
        from lib.credentials import EXPOSED_MODE, exposed

        self._secret(tmp_path, 0o644)

        findings = exposed(tmp_path)

        assert len(findings) == 1
        assert findings[0].state == EXPOSED_MODE
        assert "chmod 600" in findings[0].describe()

    def test_a_group_readable_key_counts_too(self, tmp_path):
        from lib.credentials import exposed

        self._secret(tmp_path, 0o640)

        assert len(exposed(tmp_path)) == 1

    def test_a_credential_that_is_not_present_is_not_a_finding(self, tmp_path):
        """Absence is preflight's business, and saying it twice gives it two wordings."""

        from lib.credentials import inspect_modes

        assert inspect_modes(tmp_path) == ()

    def test_the_summary_says_so_plainly_when_nothing_is_exposed(self, tmp_path):
        from lib.credentials import describe

        self._secret(tmp_path, 0o600)

        assert "readable only by its owner" in describe(tmp_path)
