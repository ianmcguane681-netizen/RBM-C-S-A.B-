"""The one list of prefixes that are not a person, and the predicate that reads it.

Six copies of this tuple existed across five files and two of them had drifted to four
entries. `lib.arb.EquivalenceDeclaration` and `rbe_runtime.profile.is_agent_actor` both
accepted `bot:` and `system:`, so `EquivalenceDeclaration(declared_by="bot: scanner")`
constructed without complaint and `board verify --by "system: importer"` was accepted as a
human ratification. Those are the two most consequential guards here: declaring settlement
equivalence is the single judgement that turns an arb from INDETERMINATE into something
placeable, and `board verify` is what publishes a decision.

Nothing about either copy looked wrong. A tuple of plausible prefixes reads as complete
whichever four or six it holds, and both fired convincingly for `agent:` — which is the
prefix anyone testing the guard reaches for first. So the list lives here and is imported
rather than written out again. A guard documented as closed and open in two places is
worse than no guard at all, because the documentation is what stops anybody looking.

**This module holds the list and deliberately not the refusals.** Every call site raises
its own message naming what a person can go and do instead, and collapsing six specific
refusals into one generic one would trade a real defect for a smaller one.
"""
from __future__ import annotations

#: An actor carrying any of these is automation, however it is named. All six everywhere:
#: a seat dodging the agent rules by choosing a different prefix, and automation dodging
#: the human rules by choosing `agent:`, are one hole seen from two sides.
AUTOMATION_PREFIXES = ("agent:", "ai:", "model:", "automation:", "bot:", "system:")


def is_automation(actor: str) -> bool:
    """Whether this actor is a machine. Case and surrounding space are not a loophole."""

    return actor.strip().lower().startswith(AUTOMATION_PREFIXES)
