"""What each lane needs before it can read anything, and what it can already do.

    python preflight.py            presence only, no network, no logins
    python preflight.py --probe    also reach the endpoints and confirm they answer

Exit codes so a script can act without parsing text:

    0   every lane READY
    1   at least one lane DEGRADED, none BLOCKED
    2   at least one lane BLOCKED

`--probe` is opt-in on purpose. Betfair and Smarkets credentials are checked by presence
and never logged in with: a login is a real authentication event against a real account,
and Smarkets caps them at five per five minutes, so a preflight that authenticated on every
run could spend the budget a scan then needs.
"""
from __future__ import annotations

import sys

from lib.preflight import BLOCKED, DEGRADED, all_lanes, report


def main(probe: bool) -> int:
    lanes = all_lanes(probe=probe)
    if not probe:
        print("Presence check only. Nothing was contacted; run with --probe to confirm "
              "the endpoints answer.\n")
    print(report(lanes))

    if any(l.status == BLOCKED for l in lanes):
        return 2
    return 1 if any(l.status == DEGRADED for l in lanes) else 0


if __name__ == "__main__":
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        raise SystemExit(0)
    raise SystemExit(main("--probe" in sys.argv))
