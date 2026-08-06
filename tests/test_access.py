"""A key was enough while the only way in was an ssh tunnel. The bind default is 0.0.0.0.

`python -m backend` on a machine with a public address served the portfolio, every open
decision's subject and each lane's exposure behind one static string that lives in browser
storage, never expires, is rotated by nobody and crosses plain HTTP in clear. The key was
never wrong; it was sized for a boundary that the bind default had quietly removed.

The properties here are about the direction each unknown resolves in. An unstated bind
address must count as exposed, because the comfortable assumption — loopback until told
otherwise — is comfortable precisely because it disables the check. An unreadable lockout
record must deny the attempt, because the alternative is that corrupting one file buys an
attacker unlimited guesses. And a login must yield the power to SEE and never the power to
run a lane, or the convenient act is once again the one that puts a money-moving credential
in a browser.
"""
from __future__ import annotations

import json

import pytest

from lib.access import (
    EXPIRED,
    EXPOSED,
    INDETERMINATE,
    INVALID,
    LOCAL,
    LOCKED_OUT,
    MAX_FAILURES,
    NOT_CONFIGURED,
    UNKNOWN,
    VALID,
    AttemptRecord,
    OperatorCredential,
    exposure,
    issue_session,
    log_in,
    login_required,
    verify_session,
)

PASSPHRASE = "four unrelated words here"


def credential(tmp_path, username="ian", passphrase=PASSPHRASE):
    made = OperatorCredential.create(username, passphrase)
    made.save(tmp_path / "operator.json")
    return made


class TestAnUnknownExposureIsNotAProvenSafeOne:
    def test_loopback_is_local_and_needs_no_login(self):
        assert exposure("127.0.0.1") == LOCAL
        assert login_required("127.0.0.1") is False

    def test_every_interface_is_exposed(self):
        """`0.0.0.0` includes the public address of the droplet this is meant to run on."""

        assert exposure("0.0.0.0") == EXPOSED
        assert login_required("0.0.0.0") is True

    def test_an_unstated_bind_is_unknown_and_treated_as_exposed(self, monkeypatch):
        """The safety of the whole module is in this one resolution.

        Assuming loopback when nobody said would make the default the case that silently
        turns the check off, which is how a control ends up present and never engaging.
        """

        monkeypatch.delenv("PROVENA_BIND_HOST", raising=False)

        assert exposure() == UNKNOWN
        assert login_required() is True

    def test_a_public_address_is_exposed(self):
        assert exposure("203.0.113.10") == EXPOSED


class TestTheCredentialItself:
    def test_the_passphrase_is_never_stored(self, tmp_path):
        made = credential(tmp_path)

        written = json.loads((tmp_path / "operator.json").read_text(encoding="utf-8"))

        assert PASSPHRASE not in json.dumps(written)
        assert written["algorithm"] == "scrypt"
        assert made.verify("ian", PASSPHRASE) is True

    def test_it_is_written_readable_only_by_its_owner(self, tmp_path):
        credential(tmp_path)

        assert oct((tmp_path / "operator.json").stat().st_mode & 0o777) == "0o600"

    def test_two_credentials_with_one_passphrase_do_not_share_a_hash(self, tmp_path):
        """Per-credential salt: one leaked hash must not identify the same passphrase."""

        first = OperatorCredential.create("ian", PASSPHRASE)
        second = OperatorCredential.create("ian", PASSPHRASE)

        assert first.digest != second.digest

    def test_a_wrong_username_is_refused_even_with_the_right_passphrase(self, tmp_path):
        assert credential(tmp_path).verify("someone-else", PASSPHRASE) is False

    def test_a_short_passphrase_is_refused_with_advice_rather_than_a_rule_set(self):
        with pytest.raises(ValueError, match="four unrelated words|12 characters"):
            OperatorCredential.create("ian", "short")

    def test_an_absent_file_is_not_configured_rather_than_a_credential(self, tmp_path):
        assert OperatorCredential.load(tmp_path / "nothing.json") is None

    def test_a_corrupt_file_is_not_configured_rather_than_accepting_anything(self, tmp_path):
        path = tmp_path / "operator.json"
        path.write_text("{ not json", encoding="utf-8")

        assert OperatorCredential.load(path) is None

    def test_the_credential_path_is_resolved_at_call_time(self):
        """A path bound at import cannot be redirected, and this one guards the money view.

        The journal's defect, in the module that decides who may look at the portfolio: a
        test that could not point this somewhere else would be a test run against the real
        operator's home directory.
        """

        import inspect

        default = inspect.signature(OperatorCredential.load).parameters["path"].default

        assert not isinstance(default, (str, type(None)))
        assert default.__class__ is object


class TestASessionSeesAndDoesNotDo:
    def test_a_fresh_session_verifies(self, tmp_path):
        made = credential(tmp_path)
        token, _ = issue_session(made)

        assert verify_session(made, token).status == VALID

    def test_an_expired_session_is_told_apart_from_a_forged_one(self, tmp_path):
        """The person holding an expired token needs to be told to log in again."""

        made = credential(tmp_path)
        token, _ = issue_session(made, hours=-1)

        assert verify_session(made, token).status == EXPIRED
        assert verify_session(made, "not.a-real-token").status == INVALID

    def test_a_tampered_payload_does_not_verify(self, tmp_path):
        import base64

        made = credential(tmp_path)
        token, _ = issue_session(made)
        encoded, signature = token.split(".", 1)
        forged = base64.urlsafe_b64encode(b"root|2099-01-01T00:00:00Z").decode().rstrip("=")

        assert verify_session(made, f"{forged}.{signature}").status == INVALID

    def test_changing_the_passphrase_invalidates_every_outstanding_session(self, tmp_path):
        """The only revocation lever a stateless token has, and it must actually work."""

        made = credential(tmp_path)
        token, _ = issue_session(made)
        replaced = OperatorCredential.create("ian", "a completely different phrase")

        assert verify_session(replaced, token).status == INVALID

    def test_no_credential_reports_not_configured_rather_than_invalid(self):
        assert verify_session(None, "anything").status == NOT_CONFIGURED


class TestGuessingIsCounted:
    def test_a_wrong_passphrase_is_recorded_and_refused(self, tmp_path):
        credential(tmp_path)

        outcome = log_in("ian", "wrong passphrase here",
                         credential_path=tmp_path / "operator.json",
                         attempts_path=tmp_path / "attempts.json")

        assert outcome.status == INVALID
        assert AttemptRecord(tmp_path / "attempts.json").recent_failures() == 1

    def test_enough_failures_lock_the_door(self, tmp_path):
        credential(tmp_path)
        paths = {"credential_path": tmp_path / "operator.json",
                 "attempts_path": tmp_path / "attempts.json"}
        for _ in range(MAX_FAILURES):
            log_in("ian", "wrong passphrase here", **paths)

        outcome = log_in("ian", PASSPHRASE, **paths)

        assert outcome.status == LOCKED_OUT
        assert "being guessed" in outcome.reason

    def test_a_correct_passphrase_ends_the_run_of_failures(self, tmp_path):
        credential(tmp_path)
        paths = {"credential_path": tmp_path / "operator.json",
                 "attempts_path": tmp_path / "attempts.json"}
        log_in("ian", "wrong passphrase here", **paths)

        assert log_in("ian", PASSPHRASE, **paths).status == VALID
        assert AttemptRecord(tmp_path / "attempts.json").recent_failures() == 0

    def test_an_unreadable_attempt_record_denies_rather_than_permits(self, tmp_path):
        """Corrupting one file must not buy an attacker unlimited guesses."""

        credential(tmp_path)
        (tmp_path / "attempts.json").write_text("{ not json", encoding="utf-8")

        outcome = log_in("ian", PASSPHRASE,
                         credential_path=tmp_path / "operator.json",
                         attempts_path=tmp_path / "attempts.json")

        assert outcome.status == INDETERMINATE
        assert "will not parse" in outcome.reason

    def test_no_credential_at_all_names_the_command_that_makes_one(self, tmp_path):
        outcome = log_in("ian", PASSPHRASE,
                         credential_path=tmp_path / "nothing.json",
                         attempts_path=tmp_path / "attempts.json")

        assert outcome.status == NOT_CONFIGURED
        assert "access.py --set-operator" in outcome.reason


class TestTheApiEnforcesIt:
    def _client(self, monkeypatch, tmp_path, *, host, credential_file=True):
        from fastapi.testclient import TestClient

        import lib.access as access
        from backend.app import create_app

        monkeypatch.setenv("PROVENA_BIND_HOST", host)
        monkeypatch.setenv("PROVENA_VIEW_KEY", "view-key")
        monkeypatch.setenv("PROVENA_COMMAND_KEY", "command-key")
        monkeypatch.setattr(access, "CREDENTIAL", tmp_path / "operator.json")
        monkeypatch.setattr(access, "ATTEMPTS", tmp_path / "attempts.json")
        if credential_file:
            credential(tmp_path)
        return TestClient(create_app())

    def test_a_local_server_still_serves_on_the_view_key_alone(self, monkeypatch, tmp_path):
        client = self._client(monkeypatch, tmp_path, host="127.0.0.1")

        response = client.get("/api/v1/overview", headers={"X-Provena-View-Key": "view-key"})

        assert response.status_code == 200

    def test_an_exposed_server_refuses_the_view_key_without_a_login(self, monkeypatch, tmp_path):
        client = self._client(monkeypatch, tmp_path, host="0.0.0.0")

        response = client.get("/api/v1/overview", headers={"X-Provena-View-Key": "view-key"})

        assert response.status_code == 401
        assert "login is required" in response.json()["detail"]

    def test_an_exposed_server_with_no_credential_serves_nothing_at_all(
        self, monkeypatch, tmp_path
    ):
        """Not a fallback to the key: an exposed box nobody can log in to is a closed box."""

        client = self._client(monkeypatch, tmp_path, host="0.0.0.0", credential_file=False)

        response = client.get("/api/v1/overview", headers={"X-Provena-View-Key": "view-key"})

        assert response.status_code == 503
        assert "access.py --set-operator" in response.json()["detail"]

    def test_a_login_yields_a_session_that_reads(self, monkeypatch, tmp_path):
        client = self._client(monkeypatch, tmp_path, host="0.0.0.0")

        token = client.post("/api/v1/login",
                            json={"username": "ian", "password": PASSPHRASE}).json()["token"]
        response = client.get("/api/v1/overview", headers={"X-Provena-Session": token})

        assert response.status_code == 200

    def test_a_session_cannot_run_a_lane(self, monkeypatch, tmp_path):
        """The split the two keys exist for, preserved through the login.

        A token that could run a lane would put a money-moving credential back in browser
        storage, which is the exact thing the view key was introduced to avoid.
        """

        client = self._client(monkeypatch, tmp_path, host="0.0.0.0")
        token = client.post("/api/v1/login",
                            json={"username": "ian", "password": PASSPHRASE}).json()["token"]

        response = client.post("/api/v1/reapers/run", json={"dry_run": True},
                               headers={"X-Provena-Session": token})

        assert response.status_code == 401

    def test_a_wrong_passphrase_at_the_endpoint_is_401_and_names_nothing_useful(
        self, monkeypatch, tmp_path
    ):
        client = self._client(monkeypatch, tmp_path, host="0.0.0.0")

        response = client.post("/api/v1/login",
                               json={"username": "ian", "password": "wrong passphrase"})

        assert response.status_code == 401
        assert PASSPHRASE not in response.text

    def test_the_posture_endpoint_says_what_is_required_without_naming_the_operator(
        self, monkeypatch, tmp_path
    ):
        client = self._client(monkeypatch, tmp_path, host="0.0.0.0")

        payload = client.get("/api/v1/access").json()

        assert payload["login_required"] is True
        assert payload["operator_credential"] == "CONFIGURED"
        assert "ian" not in json.dumps(payload)
