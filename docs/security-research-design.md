# The security research engine, designed

Designed 2026-08-09, reviewed the same day, **not built and not next**. Two gates stand in
front of it: the scope check at the bottom of this document, and the 2026-08-09 decision in
`docs/next-work.md` that no new lane is built until an existing one produces something real.
Either alone is enough to keep this on paper. One of the functions beyond the original
seven in `docs/target-functions.md`; its autonomy target and the line it must not cross are
stated in `docs/end-state.md` and are not reopened here — this document is how it would
*work* if it is built at all.

Ian's framing was "a bounty-hunter AI for security issues in apps, code, websites or
anything that may be worth money to someone if found, run autonomously." The legitimate
version of that is real and valuable. The illegitimate version is a crime, and the
difference between them is a single input this lane treats the way the arb lane treats a
settlement declaration.

One thing this document does not model, flagged on review for the same reason the flipper
now flags it: **bounty income is taxable**, and "a way the system could earn" is a pre-tax
statement everywhere below.

## The one thing that is decided, not designed

**Scope is a hard input, and absent scope blocks.** The lane takes a list of authorised
programs and their rules — public bug-bounty programs within their stated scope, your own
assets, engagements with written permission — and refuses everything outside that list the
way every other lane refuses a missing gate. A domain nobody authorised is not a low-
confidence target; it is `OUT_OF_SCOPE`, and testing it is unauthorised access whatever it
might be worth. "Worth money to someone if found" is not authorisation, and a bank you have
no agreement with is a crime scene rather than a bounty.

This is the third-state doctrine in the place it matters most. The lane's first question is
not "is this vulnerable" but "am I allowed to look", and its answer has three values:

```
AUTHORISED       on the list, within its stated scope and rules
OUT_OF_SCOPE     reachable, and explicitly not permitted. Refused, loudly
SCOPE_UNKNOWN    the program's rules could not be read or parsed
```

`SCOPE_UNKNOWN` **blocks**, exactly as an unreadable breaker limit blocks a trade. A scope
you cannot establish is not a scope you may assume — the failure that direction is testing
something you were not cleared for, which is the one failure in this whole system with a
legal rather than a financial cost. Everything below assumes this gate is first, is
structural, and is never routed around.

## The lane in the five callables every lane supplies

The point of the reaper shape is that a new lane is a new set of five functions and some
registry lines, not a new architecture. The security lane fits it, and writing it in this
frame is what keeps it inside the doctrine rather than beside it.

```
look()        the authorised programs you are enrolled in, and your own assets, each
              carried WITH its scope rules attached — never a bare target
screen()      the cascade: scope first and fatal, then does it pay cash, then are its
              rules machine-checkable
gates()       what the cascade did not establish: rate limits, testing windows, finding
              classes the program excludes
thesis_for()  a per-finding reason, because a finding is a claim — see below
size()        a report written against the program's submission format. NOT an exploit
```

### `look()` reads programs, not the open internet

Candidates come from the bug-bounty platforms you are enrolled in, plus assets you own
outright. **Whether those platforms expose scope over an API in a form your account can read
is precisely the open question at the bottom of this document, and it is not assumed here.**
An earlier draft of this paragraph asserted that they all do; that assertion was removed on
review because it quietly answered the one question the whole design is gated on, and a
reader who believed it would skip the check. A candidate is never a hostname on its own; it is a target *and* the rules that
say what may be done to it. A lane that fetched targets and looked their scope up separately
is a lane one refactor away from testing a target whose scope failed to load, which is the
`SCOPE_UNKNOWN` failure wearing a plausible disguise.

### `screen()` puts scope where the arb lane puts settlement

Cheapest and most fatal first, as everywhere. Fatal first here is scope: `OUT_OF_SCOPE`
refuses before any other stage runs, so no reconnaissance, no pattern match and no reasoning
ever touches a target that is not permitted. Then the cheap disqualifiers — a program that
pays only "kudos" is not a way the system earns; a program whose rules are prose a human
must interpret cannot be enforced by the machine and is `INDETERMINATE` rather than assumed
permissive.

### `thesis_for()` — this lane is stocks, not arb

The arb lane runs on a standing authority because an arb asserts nothing about the fixture;
the claim is only that two books disagree. A security finding is the opposite. It is
entirely a claim about a specific target — *this endpoint has this weakness* — the same shape
as a stock purchase being a claim about a company. So a finding needs a reason recorded per
finding, authored by a named person, exactly as `lib/thesis` requires for stocks and the
crypto lane requires per asset. Sharing the reconnaissance plumbing across findings is fine;
sharing an authority model that lets one standing grant bless every submission is the error
to avoid, and it is the same error `docs/end-state.md` warns against for a betting thesis.

### `size()` produces a report, and the boundary is structural

The deliverable is a written finding against the program's submission format — the same kind
of object as the arb lane's slip and the flipper's suggestion: a person reviews it and
submits it. **The lane reads, correlates and reasons; it does not exploit.** It matches an
authorised asset against known vulnerability classes and disclosed CVEs, reasons about what
is probably exploitable and worth a human's time, and stops at *here is a probable finding
and the evidence for it*.

The moment "confirm this is real" would mean sending a payload that actually compromises a
system, the lane has crossed from research into action — and that capability is left out of
the adapter the way `connectors/chain_exec` has no signing path. This is deliberate and it
is load-bearing: a policy is something somebody relaxes at eleven at night, and an absent
capability is not. A finding reaches `READY` as evidence and a person decides whether to
prove it out. Proving it out, where the program's rules permit active testing, is a
human-in-the-loop step and not an autonomous one, for the same reason re-arming a breaker is.

## The breaker is reputation, not money

Every money lane's breaker is denominated in cash. This one is not, and pretending it were
would leave its most expensive failure uncounted — this repository's founding defect in a
new suit.

A researcher account has a **signal-to-noise reputation**, and submitting weak or wrong
findings spends it: platforms down-rank and eventually ban accounts that file noise, which
is this lane's version of the arb lane's restriction risk on a winning account. So the
breaker here trips on a run of rejected or duplicate submissions, not on a loss figure, and
a tripped reputation breaker stops the lane submitting exactly as a tripped money breaker
stops it placing. It does not reset itself, and re-arming is a named human act with a stated
reason, because "the account is fine to use again" is a judgement about a relationship rather
than a number.

This matters because the success signal is genuinely weaker here than in any money lane. An
arb has a guaranteed return computed before it goes on; a stock has a settled profit or loss.
A security finding has neither until a program triages it, days later, and most candidate
findings are false positives. A lane that treats its own reputation as free will burn an
asset that never appears in a ring-fence, which is why the breaker is built around the asset
that actually depletes.

## Why this is further out than it looks, stated plainly

Three things make this the hardest of the planned lanes, and none of them is the code.

**The legal boundary is sharp and unforgiving.** Every other lane's worst case is losing
money. This lane's worst case is unauthorised access, which is why scope is structural and
first and why `SCOPE_UNKNOWN` blocks. The design can make that boundary hard to cross; it
cannot make crossing it cheap, so the boundary has to hold without exception.

**The success signal is the weakest.** See the breaker section. A lane whose feedback
arrives late, sparse and mostly negative is hard to tune and easy to fool into submitting
noise.

**The value evidence is thin.** The four crypto gates are hygiene, not edge, and the same is
true here: matching an asset against known CVEs is table stakes that many people run. "Find
something worth money" needs a real research edge — a source of *what is likely vulnerable
and under-examined* — and that is a genuine research project rather than a configuration.
Absent it, the lane is a compliance scanner, which is useful and is not what was asked for.

## The one thing to check before writing any code

**Do the platform APIs expose scope and submission in a machine-readable form your account
can actually read?**

The entire lawful version of this lane rests on enforcing scope from data rather than from a
human reading a page — and if a program states its scope only as prose, the machine cannot
enforce the one gate that keeps the lane out of a courtroom. So before a line of lane code:
enrol in one program, and check what its API returns for scope, rules and submission. This
is the same discipline the flipper's eBay-sold-data question imposed, and the same shape of
answer: if scope is not machine-readable, the honest conclusion is that this function does
not work as designed — not that a human pre-approves each target and the lane runs against
the rest. That substitution is where "scoped and lawful" quietly becomes "autonomous and
not", and it is the failure this whole document exists to prevent.

## Where it sits, and what must not happen

Behind everything currently designed. It carries the sharpest legal boundary, the weakest
success signal and the thinnest value evidence of any planned lane — a lot of unknowns to
hold at once — and the cheapest first step is the scope-API check above, gated on Ian
confirming he wants to pursue it at all.

- **Scope must never default to permitted.** `SCOPE_UNKNOWN` and `OUT_OF_SCOPE` both block.
  A target the lane cannot establish authorisation for is a target it does not touch.
- **No exploitation capability in the adapter.** The lane reasons to a report and stops. The
  ability to weaponise a finding is absent by construction, not disabled by a flag.
- **A finding is a claim and needs a per-finding reason**, authored by a named human. No
  standing grant blesses submissions.
- **The reputation breaker is real.** A run of rejected submissions stops the lane, and only
  a named human re-arms it.
- **Recording standing in for acting.** As with every lane here, the deliverable is
  something a person reviews and submits. Nothing here submits autonomously in v1, and
  active testing — even in scope — is a human-in-the-loop step.
