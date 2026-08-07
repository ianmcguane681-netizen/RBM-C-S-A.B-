"""Who is allowed to see this, and the difference between a laptop and the internet.

The operator API has always taken a key. That was enough while the only documented way to
reach it was an ssh tunnel to a server bound to loopback — the key stopped a second person
on the same box, and the tunnel stopped everybody else.

It stopped being enough the moment the bind default was `0.0.0.0`. `python -m backend` on a
machine with a public address serves the money view to the whole internet behind one static
string that lives in browser storage until the tab closes, travels in cleartext over plain
HTTP, and never expires. Nothing rotates it, nothing counts how many times it has been
guessed, and nothing anywhere says out loud that this server is now reachable.

So there are two postures and the code knows which one it is in:

    LOCAL     bound to loopback. Nothing outside this machine can connect. A key is
              enough, because the tunnel or the absent route is the real boundary.
    EXPOSED   bound to an address another machine can reach. A key is NOT enough: an
              operator credential must exist and a login must have happened.
    UNKNOWN   nobody said what it bound to.

**UNKNOWN is treated as EXPOSED, and that is the whole safety of this module.** The
comfortable default would be to assume loopback when the bind is unstated, and it is
comfortable precisely because it is the assumption that silently disables the check. An
unknown exposure is not a proven-safe one, the same way an unreadable limit is not a
satisfied limit.

**A session grants seeing, never doing.** `PROVENA_COMMAND_KEY` runs lanes and stays in the
operator's shell; logging in from a browser yields a token with the view key's powers and a
lifetime measured in hours. That preserves the split the two keys were introduced for — the
convenient act must never be the one that puts a money-moving credential in a browser — and
improves on it, because a session expires and a pasted key does not.

**Passwords are hashed with `scrypt` from the standard library**, salted per credential, and
compared with `compare_digest`. No new dependency: a password hashing library added for one
call is a supply-chain decision made to save six lines.

**Failed attempts are counted, and the counter failing closes the door.** If the file that
records attempts cannot be read, the system cannot tell whether it is in a lockout, and
refuses the login rather than guessing in the direction that lets somebody keep trying.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hmac import compare_digest
from pathlib import Path

LOCAL = "LOCAL"
EXPOSED = "EXPOSED"
UNKNOWN = "UNKNOWN"

VALID = "VALID"
EXPIRED = "EXPIRED"
INVALID = "INVALID"
NOT_CONFIGURED = "NOT_CONFIGURED"
LOCKED_OUT = "LOCKED_OUT"
INDETERMINATE = "INDETERMINATE"

#: The environment variable `backend/__main__` sets so the application can know what it was
#: bound to. Absent means UNKNOWN, which is treated as EXPOSED.
BIND_VARIABLE = "PROVENA_BIND_HOST"

CREDENTIAL = Path("~/.provena/operator.json")
ATTEMPTS = Path("data/access-attempts.json")

SESSION_HOURS = 8

#: Distinguishes "the caller said nothing" from "the caller passed a path". A plain
#: `= CREDENTIAL` default binds the constant at import, which makes it unpatchable — the
#: defect that once sent a test run's journal into the live `data/`, and which here would
#: mean a test could not point the credential anywhere but the real operator's home.
_DEFAULT = object()

#: Five wrong passwords, then fifteen minutes. Slow enough that guessing a passphrase over
#: the network is hopeless; short enough that locking yourself out before dinner is not a
#: trip to the datacentre.
MAX_FAILURES = 5
LOCKOUT_SECONDS = 15 * 60

#: `n` is the cost parameter: 2**14 takes a few tens of milliseconds, which is nothing on a
#: login and expensive at scale for anyone with the file.
_SCRYPT = {"n": 2 ** 14, "r": 8, "p": 1, "dklen": 32}

_LOOPBACK = {"127.0.0.1", "::1", "localhost", "::ffff:127.0.0.1"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _stamp(moment: datetime | None = None) -> str:
    return (moment or _now()).isoformat(timespec="seconds").replace("+00:00", "Z")


def exposure(host: str | None = None) -> str:
    """LOCAL, EXPOSED or UNKNOWN, from what the server was actually bound to.

    `0.0.0.0` and `::` are every interface, which includes the public one on a droplet.
    They are named here rather than inferred, because "not obviously loopback" and
    "definitely reachable" are the same answer in the only direction that matters.
    """

    value = (host if host is not None else os.environ.get(BIND_VARIABLE, "")).strip()
    if not value:
        # `PROVENA_BIND_HOST` is set by the server process, so it does not exist in a
        # separate command like `access.py` — which therefore reported every box EXPOSED,
        # contradicting the runbook's own instruction that a loopback deployment needs no
        # passphrase. `HOST` is what the unit sets and what `backend/__main__` resolves the
        # bind from, so asking it answers "what would this box bind" rather than guessing.
        value = os.environ.get("HOST", "").strip()
    if not value:
        return UNKNOWN
    if value.lower() in _LOOPBACK:
        return LOCAL
    if value.startswith("127.") :
        return LOCAL
    return EXPOSED


def login_required(host: str | None = None) -> bool:
    """Anything that is not provably local requires a credential."""

    return exposure(host) != LOCAL


@dataclass(frozen=True, slots=True)
class OperatorCredential:
    """A username, a salt and a scrypt hash. The password itself is never stored."""

    username: str
    salt: str
    digest: str
    created_at: str
    algorithm: str = "scrypt"

    @classmethod
    def create(cls, username: str, password: str) -> "OperatorCredential":
        if not username.strip():
            raise ValueError("a username is required")
        if len(password) < 12:
            # Not a complexity ruleset — those push people toward `Passw0rd!`. Length is
            # the only property that reliably survives contact with a real person.
            raise ValueError(
                "the passphrase must be at least 12 characters. Four unrelated words beat "
                "a short string with punctuation in it."
            )
        salt = secrets.token_bytes(16)
        digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, **_SCRYPT)
        return cls(username.strip(), base64.b64encode(salt).decode(),
                   base64.b64encode(digest).decode(), _stamp())

    @classmethod
    def load(cls, path: Path | str | object = _DEFAULT) -> "OperatorCredential | None":
        """`None` means NOT_CONFIGURED — never a credential that accepts anything."""

        resolved = Path(CREDENTIAL if path is _DEFAULT else path).expanduser()  # type: ignore[arg-type]
        try:
            row = json.loads(resolved.read_text(encoding="utf-8"))
            return cls(row["username"], row["salt"], row["digest"], row.get("created_at", ""),
                       row.get("algorithm", "scrypt"))
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def save(self, path: Path | str | object = _DEFAULT) -> Path:
        """Written 600 under a 700 directory, like every other credential here."""

        resolved = Path(CREDENTIAL if path is _DEFAULT else path).expanduser()  # type: ignore[arg-type]
        resolved.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        resolved.touch(mode=0o600, exist_ok=True)
        resolved.chmod(0o600)
        resolved.write_text(json.dumps({
            "username": self.username, "salt": self.salt, "digest": self.digest,
            "created_at": self.created_at, "algorithm": self.algorithm,
        }, indent=2) + "\n", encoding="utf-8")
        return resolved

    def verify(self, username: str, password: str) -> bool:
        derived = hashlib.scrypt(
            password.encode("utf-8"), salt=base64.b64decode(self.salt), **_SCRYPT
        )
        # Both compared in constant time, and the username too: a fast rejection on the
        # username tells an attacker which half they got right.
        #
        # Encoded first because `compare_digest` on `str` raises TypeError the moment
        # either side is non-ASCII. An operator called "seán" could be created and could
        # then never log in — the endpoint returned 500, and because the raise happened
        # before `record_failure()` the attempts were not even counted.
        return (compare_digest(username.strip().encode("utf-8"), self.username.encode("utf-8"))
                & compare_digest(derived, base64.b64decode(self.digest)))

    @property
    def session_key(self) -> bytes:
        """The HMAC key for session tokens, derived from the stored hash.

        Deliberately not a separate secret to manage. It also means changing the passphrase
        invalidates every outstanding session, which is the behaviour a person expects from
        changing a password and would otherwise have to be built.
        """

        return hashlib.sha256(b"provena-session|" + base64.b64decode(self.digest)).digest()


@dataclass(frozen=True, slots=True)
class SessionCheck:
    status: str
    username: str = ""
    expires_at: str = ""
    reason: str = ""

    @property
    def is_valid(self) -> bool:
        return self.status == VALID


def issue_session(credential: OperatorCredential, *, hours: int = SESSION_HOURS) -> tuple[str, str]:
    """A signed, expiring bearer token. Returns `(token, expires_at)`.

    Stateless on purpose: there is no session table to grow, to leak, or to disagree with
    itself across restarts. The cost is that a token cannot be revoked individually — the
    revocation lever is changing the passphrase, which invalidates all of them at once, and
    that is stated here rather than discovered.
    """

    expires = _stamp(_now() + timedelta(hours=hours))
    payload = f"{credential.username}|{expires}".encode("utf-8")
    signature = hmac.new(credential.session_key, payload, hashlib.sha256).hexdigest()
    token = base64.urlsafe_b64encode(payload).decode().rstrip("=") + "." + signature
    return token, expires


def verify_session(credential: OperatorCredential | None, token: str | None) -> SessionCheck:
    """VALID, EXPIRED, INVALID or NOT_CONFIGURED — four answers, not a boolean.

    A caller that only asked "is this allowed" would report an expired session and a forged
    one the same way, and the person holding the expired one needs to be told to log in
    again rather than left wondering what they did wrong.
    """

    if credential is None:
        return SessionCheck(NOT_CONFIGURED, reason="no operator credential exists on this box")
    if not token:
        return SessionCheck(INVALID, reason="no session token was presented")
    try:
        encoded, signature = token.split(".", 1)
        padding = "=" * (-len(encoded) % 4)
        payload = base64.urlsafe_b64decode(encoded + padding)
        username, expires = payload.decode("utf-8").split("|", 1)
    except (ValueError, UnicodeDecodeError):
        return SessionCheck(INVALID, reason="the session token is malformed")

    expected = hmac.new(credential.session_key, payload, hashlib.sha256).hexdigest()
    if not compare_digest(signature, expected):
        return SessionCheck(INVALID, reason="the session signature does not verify")
    try:
        deadline = datetime.fromisoformat(expires.replace("Z", "+00:00"))
    except ValueError:
        return SessionCheck(INVALID, reason="the session carries no readable expiry")
    if deadline <= _now():
        return SessionCheck(EXPIRED, username, expires, "the session has expired; log in again")
    return SessionCheck(VALID, username, expires)


@dataclass
class AttemptRecord:
    """How many wrong passphrases lately, and whether the door is currently shut.

    File-backed rather than in-memory so a restart does not reset an attacker's budget —
    and because the alerting reads it: a burst of failed logins is something to be told
    about, not something to find later in a log nobody opens.
    """

    path: Path
    readable: bool = True
    reason: str = ""
    failures: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self.path = Path(self.path)
        self.failures = []
        if self.path.is_file():
            try:
                row = json.loads(self.path.read_text(encoding="utf-8"))
                self.failures = [str(f) for f in row.get("failures", [])]
            except (OSError, ValueError, AttributeError) as error:
                self.readable = False
                self.reason = f"{type(error).__name__}: {error}"[:120]

    def _recent(self) -> list[str]:
        cutoff = _now() - timedelta(seconds=LOCKOUT_SECONDS)
        keep = []
        for stamp in self.failures:
            try:
                when = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            except ValueError:
                continue
            if when > cutoff:
                keep.append(stamp)
        return keep

    def state(self) -> str:
        """VALID (may try), LOCKED_OUT, or INDETERMINATE when the record will not parse.

        INDETERMINATE denies the attempt. A lockout that cannot be read is not an absent
        lockout, and the alternative is that corrupting one file buys unlimited guesses.
        """

        if not self.readable:
            return INDETERMINATE
        return LOCKED_OUT if len(self._recent()) >= MAX_FAILURES else VALID

    def recent_failures(self) -> int:
        return len(self._recent()) if self.readable else -1

    def record_failure(self) -> None:
        self.failures = self._recent() + [_stamp()]
        self._save()

    def clear(self) -> None:
        """A correct passphrase ends the run of failures, as a login should."""

        self.failures = []
        self._save()

    def _save(self) -> None:
        if not self.readable:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps({"failures": self.failures, "updated_at": _stamp()}, indent=2),
                encoding="utf-8",
            )
        except OSError as error:
            # The first version swallowed this so a failed write could not deny a correct
            # login. That reasoning was backwards: a lockout that cannot persist is a
            # lockout that does not exist, so a read-only `data/` silently bought an
            # attacker unlimited guesses. It now matches the unreadable case — the record
            # goes INDETERMINATE and the next attempt is refused with the reason named.
            # Being locked out of your own box while `data/` is unwritable is the correct
            # direction to fail in, and it is a state `alerts.py` announces.
            self.readable = False
            self.reason = f"{type(error).__name__}: {error}"[:120]


@dataclass(frozen=True, slots=True)
class LoginOutcome:
    status: str
    token: str = ""
    expires_at: str = ""
    reason: str = ""

    def to_dict(self) -> dict:
        return {"status": self.status, "token": self.token or None,
                "expires_at": self.expires_at or None, "reason": self.reason or None}


def log_in(
    username: str,
    password: str,
    *,
    credential_path: Path | str | object = _DEFAULT,
    attempts_path: Path | str | object = _DEFAULT,
) -> LoginOutcome:
    """One attempt, with the lockout consulted first and the reason named on refusal."""

    attempts = AttemptRecord(Path(ATTEMPTS if attempts_path is _DEFAULT else attempts_path))
    state = attempts.state()
    if state == LOCKED_OUT:
        return LoginOutcome(LOCKED_OUT, reason=(
            f"{MAX_FAILURES} failed attempts; locked for "
            f"{LOCKOUT_SECONDS // 60} minutes. If this was not you, the passphrase is "
            f"being guessed — change it and check who can reach this port."
        ))
    if state == INDETERMINATE:
        return LoginOutcome(INDETERMINATE, reason=(
            f"the attempt record at {attempts.path} will not parse ({attempts.reason}), so "
            f"whether this box is in a lockout cannot be established. Repair or remove the "
            f"file by hand; an unreadable lockout is not an absent one."
        ))

    credential = OperatorCredential.load(credential_path)
    if credential is None:
        return LoginOutcome(NOT_CONFIGURED, reason=(
            f"no operator credential exists. Create one on the box with "
            f"`python access.py --set-operator <name>`; until then this server has nobody "
            f"it can let in."
        ))
    if not credential.verify(username, password):
        attempts.record_failure()
        return LoginOutcome(INVALID, reason="the username or passphrase is wrong")

    attempts.clear()
    token, expires = issue_session(credential)
    return LoginOutcome(VALID, token, expires)


def describe_posture(host: str | None = None, *,
                     credential_path: Path | str | object = _DEFAULT) -> str:
    """One paragraph a person can act on, for `access.py` and the runbook."""

    where = exposure(host)
    credential = OperatorCredential.load(credential_path)
    if where == LOCAL:
        return (
            "LOCAL — bound to loopback, so nothing outside this machine can connect. A key "
            "is enough here and a login is optional. Reach a remote box this way with an "
            "ssh tunnel rather than by opening the port."
        )
    unknown_note = (
        " The bind address was not stated — `PROVENA_BIND_HOST` exists only inside the "
        "server process — so this is UNKNOWN, and an unknown exposure is treated as an "
        "exposed one. Pass `--host 127.0.0.1` to state it." if where == UNKNOWN else ""
    )
    if credential is None:
        return (
            f"{where} — this server is reachable from other machines and NO operator "
            f"credential exists, so it will serve no lane data at all.{unknown_note} "
            f"Create one with `python access.py --set-operator <name>`, or bind to "
            f"127.0.0.1 and use an ssh tunnel."
        )
    return (
        f"{where} — reachable from other machines; a login is required and "
        f"'{credential.username}' can perform one.{unknown_note} Sessions last "
        f"{SESSION_HOURS}h. Put a TLS terminator in front of this or use an ssh tunnel: "
        f"nothing here encrypts the connection, so on plain HTTP the passphrase crosses "
        f"the network in clear."
    )
