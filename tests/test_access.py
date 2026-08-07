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
    AttemptRecord,
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


class TestWhatTheReviewFound:
    """Nine defects, found by running this branch rather than reading it. Four are here.

    Each is the same shape: a guard that looked correct and did not engage. A username the
    comparison could not handle, a lockout that vanished when its file could not be written,
    a command that could not see what the server bound, and an environment variable that
    outranked the fact it was meant to report.
    """

    def test_a_non_ascii_username_can_log_in(self, tmp_path):
        """`compare_digest` raises TypeError on `str` the moment either side is non-ASCII.

        An operator called "seán" could be created and could then never authenticate: the
        endpoint returned 500, and because the raise happened before `record_failure()` the
        attempts were not even counted toward the lockout.
        """

        made = OperatorCredential.create("seán", PASSPHRASE)

        assert made.verify("seán", PASSPHRASE) is True
        assert made.verify("sean", PASSPHRASE) is False

    def test_a_lockout_that_cannot_be_written_denies_rather_than_disappears(self, tmp_path):
        """A read-only `data/` silently bought an attacker unlimited guesses.

        The write failure was swallowed so that it could not deny a correct login. That is
        the permissive direction: a lockout that cannot persist is a lockout that does not
        exist, and the unreadable case had always denied.
        """

        # A directory where the file should be, rather than a chmod: this suite runs as
        # root in the container, where a read-only directory is not read-only.
        blocked = tmp_path / "attempts.json"
        blocked.mkdir()
        record = AttemptRecord(blocked)

        record.record_failure()

        assert record.readable is False
        assert record.state() == INDETERMINATE

    def test_a_command_outside_the_server_still_sees_a_loopback_bind(self, monkeypatch):
        """`access.py` reported every box EXPOSED and exited 1 on a loopback deployment.

        `PROVENA_BIND_HOST` exists only inside the server process, so a separate command
        never saw it and the runbook's own instruction — that a tunnelled box needs no
        passphrase — was contradicted by the tool that reports the posture.
        """

        monkeypatch.delenv("PROVENA_BIND_HOST", raising=False)
        monkeypatch.setenv("HOST", "127.0.0.1")

        assert exposure() == LOCAL
        assert login_required() is False

    def test_a_stale_bind_variable_does_not_outrank_what_was_bound(self, monkeypatch):
        """`setdefault` let a leftover `127.0.0.1` report LOCAL beside `HOST=0.0.0.0`.

        That reopens the money view on the static view key, which is the one outcome the
        whole module exists to prevent.
        """

        import backend.__main__ as entry

        monkeypatch.setenv("PROVENA_BIND_HOST", "127.0.0.1")
        monkeypatch.setenv("HOST", "0.0.0.0")
        host, _ = entry.server_address()
        import os

        os.environ["PROVENA_BIND_HOST"] = host

        assert exposure() == EXPOSED


def test_the_session_header_survives_a_cross_origin_preflight():
    """The login shipped without adding its own header to the CORS allow list.

    A dashboard on the default `http://localhost:3000` would log in successfully and then
    fail every read at the preflight, which presents as a broken session rather than as a
    missing entry in a list — the kind of fault a person debugs in the wrong module.
    """

    from backend.app import create_app

    app = create_app()
    cors = [m for m in app.user_middleware if "CORS" in str(m)][0]
    allowed = cors.kwargs["allow_headers"]

    assert "X-Provena-Session" in allowed
    assert "X-Provena-View-Key" in allowed


def test_a_stated_bind_is_believed_when_the_environment_cannot_answer(monkeypatch):
    """`--host` exists because neither variable reaches the operator's shell.

    `PROVENA_BIND_HOST` is set inside the server process and `HOST` lives in the systemd
    unit, so `access.py` reported EXPOSED on a correctly tunnelled box — the command
    contradicting the deployment it describes. Unstated is still UNKNOWN and still strict;
    what changed is that a person may state it.
    """

    import access

    monkeypatch.delenv("PROVENA_BIND_HOST", raising=False)
    monkeypatch.delenv("HOST", raising=False)

    assert access.main(["--host", "127.0.0.1"]) == 0
    assert access.main([]) == 1
