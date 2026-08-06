"""What is asking for you, and whether anybody was told.

    python alerts.py                 assess and announce what is due
    python alerts.py --quiet         assess only; send nothing
    python alerts.py --json          the same, as the UI contract
    python alerts.py --repeat 3600   re-announce a standing condition after an hour

Exit codes, so a timer or a cron entry can act on this without parsing prose:

    0   nothing needs you
    1   something needs you and it was announced
    2   something needs you and NOBODY WAS TOLD — no channel, or delivery failed
    3   the state could not be read at all, so nothing was checked

**2 and 3 are separate from 1 deliberately.** A condition that was raised and delivered has
done its job; a condition that was raised and never left the machine has not, and the whole
point of this command is that a person finds out. An exit code that made them equal would
put the failure of the alerting system into the same bucket as the alerts working.

**Run this on its own timer, not inside the supervisor.** A supervisor cannot report its own
death, and the heartbeat going still is the most consequential thing this checks. See
`deploy/provena-alerts.timer`.
"""
from __future__ import annotations

import json
import sys

from lib.alerting import (
    COULD_NOT_ASSESS,
    DELIVERED,
    NOT_CONFIGURED,
    REPEAT_AFTER_SECONDS,
    STORE,
    UNDELIVERABLE,
    AlertStore,
    WebhookChannel,
    assess,
    deliver,
    gather_state,
)


def run(*, quiet: bool = False, repeat_after: float = REPEAT_AFTER_SECONDS) -> tuple[dict, int]:
    """Assess, announce, and report both halves separately."""

    state, reason = gather_state()
    assessment = assess(state, reason=reason)

    store = AlertStore(STORE)
    cleared = ()
    if store.readable:
        cleared = store.cleared([c.key for c in assessment.conditions])

    if quiet:
        payload = {"assessment": assessment.to_dict(), "delivery": None,
                   "cleared": list(cleared), "store_readable": store.readable}
        return payload, _code(assessment, None)

    delivery = deliver(assessment, store, WebhookChannel(), repeat_after=repeat_after)
    if store.readable and delivery.status == DELIVERED:
        # Only ever written after a successful send. See `deliver`'s docstring for why the
        # ordering is this way round and not the other.
        store.save()

    payload = {"assessment": assessment.to_dict(), "delivery": delivery.to_dict(),
               "cleared": list(cleared), "store_readable": store.readable}
    return payload, _code(assessment, delivery)


def _code(assessment, delivery) -> int:
    if assessment.look == COULD_NOT_ASSESS:
        return 3
    if not assessment.conditions:
        return 0
    if delivery is not None and delivery.status in {NOT_CONFIGURED, UNDELIVERABLE}:
        return 2
    return 1


def main(argv: list[str]) -> int:
    quiet = "--quiet" in argv
    repeat = REPEAT_AFTER_SECONDS
    if "--repeat" in argv:
        try:
            repeat = float(argv[argv.index("--repeat") + 1])
        except (IndexError, ValueError):
            print("--repeat takes a number of seconds", file=sys.stderr)
            return 2

    payload, code = run(quiet=quiet, repeat_after=repeat)

    if "--json" in argv:
        from lib.ui_contract import SCHEMA_VERSION

        print(json.dumps({"schema_version": SCHEMA_VERSION, **payload}, indent=2))
        return code

    assessment = payload["assessment"]
    print("ALERTS")
    if assessment["look"] == COULD_NOT_ASSESS:
        print(f"  COULD_NOT_ASSESS: {assessment['reason']}")
        print("  This is not a clean bill of health — nothing was checked.")
    elif not assessment["conditions"]:
        print("  Nothing to report. Every control that could be read was read, and none")
        print("  of them is asking for you.")
    else:
        print(f"  {assessment['stop']} STOP, {assessment['attention']} ATTENTION")
        for condition in assessment["conditions"]:
            print(f"\n  [{condition['severity']}] {condition['subject']}: "
                  f"{condition['summary']}")
            print(f"      -> {condition['action']}")

    if payload["cleared"]:
        print(f"\n  CLEARED since the last run: {', '.join(payload['cleared'])}")
    if not payload["store_readable"]:
        print("\n  The alert store would not parse, so everything is treated as new. You")
        print("  may see a condition announced again that you have already seen.")

    delivery = payload["delivery"]
    if delivery is None:
        print("\n  --quiet: nothing was sent, and nothing was recorded as sent.")
    elif delivery["status"] == NOT_CONFIGURED:
        print(f"\n  NOT DELIVERED  {delivery['reason']}")
        print("  The conditions above are real and nobody has been told them by this system.")
    elif delivery["status"] == UNDELIVERABLE:
        print(f"\n  UNDELIVERED  {delivery['channel']} failed: {delivery['reason']}")
        print("  They are NOT recorded as announced, so the next run will try again.")
    elif delivery["announced"]:
        print(f"\n  DELIVERED  {len(delivery['announced'])} condition(s) via "
              f"{delivery['channel']}.")
    return code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
