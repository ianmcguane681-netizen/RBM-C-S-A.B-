"""Where the secrets live on this box, and whether anybody else can read them.

`deploy/setup-credentials.sh` writes `600` files under `700` directories and argues at
length why. Nothing verified it afterwards. A key placed by hand — `printf ... > key` on a
tired evening, a restore from a backup that flattened the modes, a file copied with `cp`
from somewhere permissive — was read without a word, and the one guard lived in the script
a hurrying person is most likely to skip.

On a single-user laptop that is nearly harmless. On the droplet it is the difference
between "the broker key is readable by the owner" and "the broker key is readable by every
account on the box", and the file itself looks identical either way.

**This reports; it does not block.** The doctrine's "fail toward stopping" is about money
and about limits that cannot be read — a loose permission bit is neither, and halting the
research lanes over one would be a refusal aimed at the wrong thing. So a world-readable
key produces a finding in `preflight.py` and an ATTENTION alert, and the lane keeps running.

**One structured list, here.** The paths appear elsewhere as prose inside preflight's
`remedy` strings, which is fine — nothing reads those, so they are documentation rather
than a competing source of truth. Anything that needs to *act* on where a credential lives
reads this list.
"""
from __future__ import annotations

import stat
from dataclasses import dataclass
from pathlib import Path

SECURE = "SECURE"
#: Readable by the group or by everybody. The file exists and its contents are not private.
EXPOSED_MODE = "EXPOSED_MODE"
ABSENT = "ABSENT"
#: The mode could not be read at all. Not the same as secure, and not the same as absent.
UNREADABLE = "UNREADABLE"

#: `0o077` is every group and world bit. A file at 600 has none of them; 640 and 644 do.
_OTHERS = stat.S_IRWXG | stat.S_IRWXO


@dataclass(frozen=True, slots=True)
class CredentialFile:
    """One secret on disk, and what holding it would let somebody do."""

    path: str
    what: str


#: Relative to the operator's home unless absolute. Extend this when a connector gains a
#: credential — it is the list `preflight` and `alerts` both read.
SECRETS = (
    CredentialFile(".alpaca/key_id", "place and cancel orders in the brokerage account"),
    CredentialFile(".alpaca/secret_key", "place and cancel orders in the brokerage account"),
    CredentialFile(".oddsapi/key", "spend the odds quota, and see what it has left"),
    CredentialFile(".betfair/app_key", "read exchange prices as this account"),
    CredentialFile(".betfair/password", "log in to the exchange account"),
    CredentialFile(".smarkets/password", "log in to the exchange account"),
    CredentialFile(".provena/operator.json", "log in to the operator API as the owner"),
    CredentialFile(".provena/alert_webhook", "post messages that look like this system's"),
)


@dataclass(frozen=True, slots=True)
class ModeFinding:
    path: Path
    state: str
    mode: str
    what: str

    def describe(self) -> str:
        if self.state == EXPOSED_MODE:
            return (
                f"{self.path} is mode {self.mode} — readable beyond its owner. It would let "
                f"anybody with an account on this box {self.what}. Fix with "
                f"`chmod 600 {self.path}`."
            )
        if self.state == UNREADABLE:
            return (
                f"{self.path} exists and its mode could not be read ({self.mode}). That is "
                f"not a confirmation that it is private."
            )
        return f"{self.path} is mode {self.mode}."


def inspect_modes(home: str | Path | None = None) -> tuple[ModeFinding, ...]:
    """Every secret that exists, with its mode. Absent files are not findings.

    A credential that has not been placed is a preflight matter — the lane already reports
    it MISS and names the fix — and repeating it here would put the same fact in two panels
    with two wordings.
    """

    root = Path(home).expanduser() if home else Path.home()
    findings: list[ModeFinding] = []
    for secret in SECRETS:
        path = Path(secret.path)
        resolved = path if path.is_absolute() else root / path
        try:
            mode = resolved.stat().st_mode
        except FileNotFoundError:
            # Not placed. Preflight already reports that and names the fix.
            continue
        except OSError as error:
            # `Path.exists()` swallows every OSError and returns False, so a credential
            # whose directory denies traversal read as "not present" and this module's own
            # UNREADABLE state could never be reached — `describe()` then said every secret
            # on the box was private. Statting first is what makes absent and unreadable
            # two different answers, which is the whole point of the state existing.
            findings.append(ModeFinding(resolved, UNREADABLE, type(error).__name__, secret.what))
            continue
        octal = oct(stat.S_IMODE(mode))
        state = EXPOSED_MODE if stat.S_IMODE(mode) & _OTHERS else SECURE
        findings.append(ModeFinding(resolved, state, octal, secret.what))
    return tuple(findings)


def exposed(home: str | Path | None = None) -> tuple[ModeFinding, ...]:
    """Only the ones worth saying out loud."""

    return tuple(f for f in inspect_modes(home) if f.state in {EXPOSED_MODE, UNREADABLE})


def describe(home: str | Path | None = None) -> str:
    findings = exposed(home)
    if not findings:
        return (
            "CREDENTIAL MODES  every secret on this box is readable only by its owner, or "
            "is not present."
        )
    lines = [f"CREDENTIAL MODES  {len(findings)} file(s) are not private:"]
    lines += [f"  {f.describe()}" for f in findings]
    return "\n".join(lines)
