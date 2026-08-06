"""Who can log in to this box, and whether this box needs anybody to.

    python access.py                      what the posture is and what it requires
    python access.py --set-operator ian   create or replace the operator credential
    python access.py --json               the same posture, for a script

The credential is a username and a passphrase hashed with scrypt into
`~/.provena/operator.json`, mode 600. The passphrase itself is never written down, never
passed as an argument — an argument is visible in `ps` to every user on the box and lands
in shell history — and never accepted from a pipe, so it cannot end up in a script.

**A login is required when this server is reachable from another machine, and optional
when it is bound to loopback.** That is the whole rule. Reaching a remote box through an
ssh tunnel keeps it loopback and keeps the rule satisfied without a passphrase.
"""
from __future__ import annotations

import getpass
import json
import sys

from lib.access import CREDENTIAL, OperatorCredential, describe_posture, exposure, login_required


def set_operator(username: str) -> int:
    if not sys.stdin.isatty():
        # Refused rather than read: a passphrase arriving on a pipe is a passphrase in
        # somebody's deployment script, and this file is the one thing standing in front
        # of the money view on an exposed box.
        print("Refusing to read a passphrase from a pipe. Run this in a terminal.",
              file=sys.stderr)
        return 2

    existing = OperatorCredential.load()
    if existing is not None:
        print(f"An operator credential already exists for '{existing.username}'.")
        print("Replacing it will invalidate every session issued under the old one.")
        if input("Replace it? [y/N] ").strip().lower() not in {"y", "yes"}:
            return 1

    first = getpass.getpass("Passphrase (12+ characters; four unrelated words beat one short word): ")
    second = getpass.getpass("Again: ")
    if first != second:
        print("They do not match. Nothing was written.", file=sys.stderr)
        return 2
    try:
        credential = OperatorCredential.create(username, first)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2

    path = credential.save()
    print(f"Written {path} (mode 600) for '{credential.username}'.")
    print("Sessions issued from it last 8 hours. Changing this passphrase ends all of them.")
    return 0


def main(argv: list[str]) -> int:
    if "--set-operator" in argv:
        try:
            username = argv[argv.index("--set-operator") + 1]
        except IndexError:
            print("--set-operator takes a username", file=sys.stderr)
            return 2
        return set_operator(username)

    credential = OperatorCredential.load()
    if "--json" in argv:
        print(json.dumps({
            "exposure": exposure(),
            "login_required": login_required(),
            "operator_credential": "CONFIGURED" if credential else "NOT_CONFIGURED",
            "credential_path": str(CREDENTIAL),
        }, indent=2))
    else:
        print("ACCESS")
        print(f"  {describe_posture()}")
        print()
        if credential is None:
            print("  No operator credential on this box. `python access.py --set-operator "
                  "<name>` creates one.")
        else:
            print(f"  Operator '{credential.username}', created {credential.created_at}.")
    # 0 when this posture needs nothing; 1 when it is exposed with nobody able to log in.
    return 1 if login_required() and credential is None else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
