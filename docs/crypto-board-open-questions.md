# Open questions against RBM-003

**Not a controlled document.** RBM-003's package is hash-pinned in
`docs/crypto-board/MANIFEST.json`, and two reviews are pinned to that checksum. Anything
written here is a note toward a future amendment, never an amendment itself.

That distinction was learned the hard way: this text was first appended directly to
`CRYPTO-REVIEW-METHODOLOGY.md`, which changed the file's hash and made the whole package
fail validation. Ratification refused with `RBE_AUTHORITY_PACKAGE_INVALID` — a controlled
document edited mid-review, caught by the control that exists for exactly that.

---

## Q1 — Findings about the subject vs findings about the review

`RBM003-USDC-0002` raised sixteen findings. Three describe USDC. Four describe the review
process. **Nine describe what the review could not reach** — backing that is not on-chain,
a lock gate that searched nothing, reproducibility covering four of nine evidence items, a
twelve-minute clustering window, exit costs that are single-route, DAI and every V3
position unprobed.

That is either unusually honest or not very useful, and both are true at once. A reader
looking for what the board established has to find three findings inside sixteen, and
severity does not separate them: a SEV-3 meaning "this figure is unreliable" and a SEV-3
meaning "this was never measured" ask completely different things of whoever reads them.

Section 11 of the methodology already promises three lists — *established*, *alleged*,
*not reached*. No seat currently produces them. That is the likely shape of the fix.

**Deliberately unresolved.** Splitting them now means guessing which findings ought to gate
an action, and that guess is what the mandate artifact will answer with evidence instead of
intuition. Once `is_stake_permitted` exists and it is visible which findings block a stake
and which merely inform one, the split becomes a measurement rather than a preference.

Recorded so RBM-004 and RBM-005 do not rediscover it from scratch.

## Q2 — What authority does a summary-read ratification carry?

Both USDC decisions are ratified single-authority, and the signatory states plainly that
they did not read the full findings. `board verify --basis` records this on the seat
drafts, and the ratification rationale records it on the decision.

The record is therefore honest. The open question is what the mandate artifact should *do*
with it. A decision carrying `single_authority`, `binding: false`, and a summary-level
reading is close to the weakest possible authority the system can express, and
`is_stake_permitted` should almost certainly refuse to let it gate anything that moves
money.

Worth stating as a design input rather than discovering later: the bridge must read the
scrutiny level, not just the outcome.

## Q3 — Can a tier be claimed with a gate unassessed?

`RBM003-USDC-0002` met the Tier 3 quorum — six specialists, `omitted_roles` empty — while
TKA recorded CG-03 as NOT ASSESSED with `evidence_sufficiency: INSUFFICIENT`. Five of six
gates were answered on the artefact.

MA raised this (`CG004-MA-CG-03`). The methodology does not currently say whether seat
count and gate coverage may diverge, and a Tier 3 badge asserts the first while a reader
hears the second.
