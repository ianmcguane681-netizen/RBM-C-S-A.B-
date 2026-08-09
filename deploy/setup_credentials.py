"""Place the credentials each lane needs, in the files the connectors actually read.

The same job as `setup-credentials.sh`, on any operating system. The shell version is
GNU-flavoured — `stat -c` and `find -printf` — so on Windows it does not run at all and on
macOS its confirmation output comes out blank while the files themselves are fine. This one
is stdlib Python and behaves identically everywhere, which matters because the first thing
a person does with this repository is place keys, and being told to install a shell first
is a poor way to begin.

Secrets are typed at a prompt with echo off, via `getpass`. They are never taken as
arguments: an argument is visible in the process list to every user on the box and lands in
the shell history, where it outlives any amount of care taken afterwards. `echo key > file`
has the same problem and is the usual way this goes wrong.

Nothing here is written into the repository. The connectors read from the home directory
precisely so that a public checkout can never contain a key.

## Permissions, and why Windows is not silently claimed to be secure

On POSIX the directories are 700 and the files 600, set before the secret is written rather
than after, so there is no window in which the file exists and is readable.

Windows has no such mode, and `os.chmod` there sets only the read-only bit — calling it
would return success while changing nothing about who can read the file. Reporting `600` on
a platform that has no such concept is this repository's recurring defect in miniature: a
value meaning *not applicable* rendered as *satisfied*. So the check reports NOT_POSIX and
says what actually protects the file there, which is the ACL inherited from the user
profile directory.
"""
from __future__ import annotations

import os
import sys
from getpass import getpass
from pathlib import Path

POSIX = os.name != "nt"

#: What the connectors read, and what each one unlocks. `AlpacaCredentials.load` and
#: `OddsApiCredentials.load` both resolve these with `Path.expanduser()`, so `~` is the
#: user profile on Windows exactly as it is a home directory elsewhere.
WANTED = (
    ("~/.oddsapi", "key", "Odds API key",
     "THE ODDS API  (free key at the-odds-api.com)"),
    ("~/.alpaca", "key_id", "Alpaca key id",
     "ALPACA  (paper trading keys from alpaca.markets)"),
    ("~/.alpaca", "secret_key", "Alpaca secret key", ""),
    # Not a lane. It is how a lane reaches you, and a lane that finds something at 16:00
    # on a Monday and tells nobody has not done its job. Absent, every lane still runs and
    # `lib.notify` reports NOT_CONFIGURED, which is not a failure.
    ("~/.telegram", "bot_token", "Telegram bot token",
     "TELEGRAM  (notifications: talk to @BotFather for a token, @userinfobot for your id)"),
    ("~/.telegram", "chat_id", "Telegram chat id (not secret; hidden anyway)", ""),
)


def place(directory: str, name: str, prompt: str) -> bool:
    """Write one secret, or report that nothing was entered. Returns whether it wrote."""

    try:
        value = getpass(f"  {prompt} (ENTER to skip): ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n  cancelled")
        raise SystemExit(1)

    if not value:
        print(f"  skipped {directory}/{name}\n")
        return False

    root = Path(directory).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    if POSIX:
        os.chmod(root, 0o700)

    path = root / name
    # Create with the mode already correct rather than chmod'ing afterwards: the gap
    # between the two is a window in which the secret exists and is world-readable.
    if POSIX:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(value + "\n")
    else:
        path.write_text(value + "\n", encoding="utf-8")

    print(f"  wrote {path}  [{describe_mode(path)}]\n")
    return True


def describe_mode(path: Path) -> str:
    """The real permission, or an honest statement that the platform has no such thing."""

    if not POSIX:
        return "NOT_POSIX: protected by the ACL on your user profile, not by a mode"
    mode = path.stat().st_mode & 0o777
    warning = "" if mode == 0o600 else "  <-- NOT 600, another user can read this"
    return f"{mode:o}{warning}"


def alpaca_environment() -> None:
    """Paper or live, as a separate deliberate act.

    A key gives no hint which environment it belongs to and the two base URLs differ by one
    word, so the connector refuses to load unless exactly one marker exists. A live order
    placed believing it was paper is not a bug found later.
    """

    root = Path("~/.alpaca").expanduser()
    if not (root / "key_id").is_file():
        return

    print("Which Alpaca environment do these keys belong to?")
    print("  [p] paper  (recommended: start here)")
    print("  [l] live   (real money)")
    answer = input("  p/l: ").strip().lower()

    for marker in ("paper", "live"):
        (root / marker).unlink(missing_ok=True)

    chosen = "paper"
    if answer in ("l", "live"):
        if input("  Type LIVE in full to confirm real money: ").strip() == "LIVE":
            chosen = "live"
        else:
            print("  not confirmed — marking paper")

    (root / chosen).touch()
    if POSIX:
        os.chmod(root / chosen, 0o600)
    print(f"  marked {chosen.upper()}\n")


def main() -> int:
    print("\nCredentials are optional one at a time. Press ENTER to skip any of them;")
    print("preflight will tell you what is still missing and what each one unlocks.")
    print("Nothing you type here is echoed, stored in shell history, or written into")
    print("this repository.\n")

    for directory, name, prompt, heading in WANTED:
        if heading:
            print(heading)
        place(directory, name, prompt)

    alpaca_environment()

    print("What is in place now:\n")
    found = False
    for directory in ("~/.oddsapi", "~/.alpaca", "~/.betfair", "~/.smarkets"):
        root = Path(directory).expanduser()
        for path in sorted(root.glob("*")) if root.is_dir() else ():
            if path.is_file():
                found = True
                print(f"  {path}  [{describe_mode(path)}]")
    if not found:
        print("  nothing — every prompt was skipped")

    print("\nNow run:\n  python preflight.py --probe\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
