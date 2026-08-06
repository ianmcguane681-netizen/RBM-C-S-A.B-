# Security review, 6 August 2026

A whole-repository review, not a diff review: the API and its auth, credential handling,
the connectors, the dashboard, the migrations, the deployment units, and a deliberate hunt
for anything that would let this system act without a person — a backdoor, a bypass, a
`force=True`.

Findings are ordered by what they would cost. Each says what was done about it, and the
ones that need a decision from Ian say so rather than being quietly fixed.

**What this review is not.** No penetration test was run against a live host, because no
host is running. Nothing here has been tested against a real broker or a real bookmaker,
so the API surfaces of Alpaca and The Odds API are reviewed as code that calls them rather
than as integrations under attack.

---

## Fixed in this pass

### 1. An exposed server served the money view on one static string — HIGH

`backend/__main__.py` defaults `HOST` to `0.0.0.0`, deliberately, so container and IDE
previews can reach it. That default is documented and reasonable. What made it a hole is
what stood behind it: `/api/v1/overview` returns the portfolio, every open decision's
subject, each lane's ring-fence and its unsettled exposure — precisely the set this
repository gitignores because it is public — protected by `PROVENA_VIEW_KEY`, a static
string that lives in browser storage, never expires, is rotated by nobody, and crosses
plain HTTP in clear.

The key was never wrong. It was sized for a boundary — an ssh tunnel to a loopback bind —
that the default had removed. `deploy/provena-web.service` does set `HOST=127.0.0.1`, so a
by-the-runbook deployment was never in this state; anyone running `python -m backend` on a
box with a public address was.

**Fixed.** `lib/access.py` distinguishes LOCAL from EXPOSED from UNKNOWN, and the read gate
now depends on it: bound to loopback a key is still enough, and reachable from elsewhere a
login is required. **UNKNOWN counts as EXPOSED** — assuming loopback when nobody said would
make the default the case that silently turns the check off. An exposed server with no
operator credential serves no lane data at all rather than falling back to the key.

### 2. Nothing counted a wrong credential — MEDIUM

No lockout, no throttle, no record of failed attempts anywhere. A 24-byte random key is not
guessable, but a human-chosen passphrase is, and adding a login without adding a counter
would have introduced the guessable secret without the guard.

**Fixed.** Five failures inside fifteen minutes locks the login. The record is file-backed
so a restart does not reset an attacker's budget, **an unreadable record denies the attempt**
rather than permitting it — corrupting one file must not buy unlimited guesses — and
repeated failures raise an alert, so a burst is something you are told about rather than
something found later in a log nobody opens.

### 3. Two unescaped interpolations in the dashboard — LOW

`app.js` escapes text with `safe()` everywhere it renders a value, with two exceptions:
`class="status-pill ${e.status.toLowerCase()}"` and `class="${l.status.toLowerCase()}"`
placed a server value inside an HTML attribute unescaped. Both come from our own API today,
and lane ids ultimately come from `data/reapers.json`, which a person writes by hand.

**Fixed.** Both go through `safe()`.

---

## Needs a decision — not fixed here

### 4. Nothing is encrypted in transit — HIGH if the port is ever opened

There is no TLS anywhere in this repository, and the login introduced above sends a
passphrase. The runbook's answer is the right one — bind loopback, reach it through an ssh
tunnel — and while that holds, the tunnel is the encryption. If the port is ever opened to
the internet, the passphrase and the session token cross in clear.

**Recommendation:** keep the tunnel. If you ever want the dashboard reachable without one,
put Caddy or nginx in front with a certificate and keep uvicorn on loopback behind it. I
have not added a TLS terminator: it is a deployment decision with a hostname and a
certificate attached, and guessing at those would produce a config nobody could trust.

### 5. Dependencies are unpinned — MEDIUM

`requirements.txt` uses `>=` throughout and there is no lockfile and no hashes. The box that
installs these also holds the broker key, so a compromised release of `fastapi`, `uvicorn`,
`pydantic` or `jsonschema` executes next to the money.

**Recommendation:** pin exact versions and install with `--require-hashes`, refreshed
deliberately. I have not done it unilaterally because it changes what the deployment
installs, and a pinned set generated from this container is a set nobody has reviewed.

### 6. Credential file modes are never checked — MEDIUM

`deploy/setup-credentials.sh` writes `600` files under `700` directories and argues why. But
nothing verifies it afterwards: a hand-placed `~/.oddsapi/key` at `644` is read without
complaint, and `~/.provena/alert_webhook` likewise. The one guard is in the script people
are most likely to skip.

**Recommendation:** a mode check in `preflight.py` that reports a world-readable credential
as a finding. Deliberately not built in this pass — it wants a decision about whether a
loose mode blocks a lane or merely reports, and the honest answer is probably "reports",
since halting research over a permission bit is the wrong direction to fail in for something
that is not itself money movement.

---

## Checked and clean

Recorded so the next review knows what was covered rather than re-deriving it.

**No dangerous primitives.** No `eval`, `exec`, `pickle`, `yaml.load`, `os.system` or
`shell=True` anywhere in the repository. The two `subprocess` call sites (`run.py:166`,
`board/cli.py:136`) both pass argument lists with no shell, and neither interpolates user
input into a command.

**SQL.** One f-string reaches a query, in `lib/journal.py:223`, and it interpolates names
from a literal tuple written three lines above it. Everything else is parameterised.

**No secrets in the repository.** A scan for high-entropy assignments to key/secret/token/
password names found nothing. Credentials live in files under `~/`, never in the tree, and a
test already asserts the QuickNode URL never reaches preflight output.

**No backdoor, and I looked for one specifically.** Every human-only act — ratifying a board
decision, declaring settlement equivalence, authoring a thesis, re-arming a tripped breaker,
declaring a FORECAST criterion — refuses the `agent:`/`ai:`/`model:`/`automation:`/`bot:`/
`system:` prefixes at construction, in five separate modules. There is no `force=True`
anywhere in non-test code, and no debug branch that returns permission. `connectors/
chain_exec.py` has no key path, no signing library and no send method: `sign()` raises
`SigningRefused`, and `send` and `broadcast` are bound to the same function so neither name
is a way round the other.

**The API's other gates.** `compare_digest` on both keys. Commands require the command key
and refuse with 503 when it is unset — unset never means public. Live execution needs
`PROVENA_EXECUTION_ENABLED=true` *and* the exact confirmation string, and neither alone
grants it. The API cannot route around the operating modes: `place=true` only permits, and
`place_harvest` still refuses any lane whose mode is not AUTONOMOUS.

**CORS.** `allow_credentials=False` beside a configurable origin list, which is the
combination that matters: the key is a header the caller sets rather than a cookie the
browser attaches, so a wildcard origin does not hand the API to any page in the browser. If
credentials are ever turned on, the origin list stops being cosmetic.

**Migrations.** RLS is enabled on the operations schema, `anon` and `authenticated` are
revoked, and the `public.operator_*` views are `security_invoker`, so the `GRANT ... TO anon`
on them cannot read the underlying tables.

**The new webhook.** The URL is operator-supplied and read from a 600 file. Alert bodies
carry lane names, control states and counts — never a subject, a stake or a credential.

---

## Known limits of what was added

- **A session cannot be revoked individually.** The tokens are stateless HMACs, so there is
  no session table to grow or leak; the revocation lever is changing the passphrase, which
  invalidates all of them at once because the signing key is derived from the stored hash.
- **The lockout is per-box, not per-source.** It counts failures, not who made them, so five
  wrong attempts lock the login for everyone including you. That is the safe direction and
  it is worth knowing before it happens.
- **`_run_lock` is per-process.** Under several uvicorn workers it serialises nothing.
  Unchanged from the earlier review and still true.
