"""Tell a person that something happened, and never let silence mean two things.

A system that only messages you when it finds something has a defect built into its
quietest state. No message can mean any of:

    nothing was found                  -- fine, and the thing you hoped to hear
    the supervisor stopped             -- nothing has run for a week
    the notifier broke                 -- a token expired, a chat id changed
    the lane could not reach a source  -- a broken pipeline reading as a quiet market

Four facts, one silence, and the flattering reading is the one a person adopts. So this
module sends a HEARTBEAT whose absence is the alarm: a short daily line saying what ran and
what it found, including when it found nothing. Silence then means something is wrong,
which is the only way silence can mean anything at all.

## A failed send is an event, not a non-event

`Delivery` is the third state applied to messaging. `SENT` is an acknowledgement from the
service. `REFUSED` is the service saying no -- a bad token, a chat that no longer exists.
`UNREACHABLE` is nothing answering. `NOT_CONFIGURED` is no credentials at all. They are
kept apart because a person does something different about each, and because a notifier
that fails quietly is worse than no notifier: you stop checking the dashboard *because* you
trust the messages, and then the messages stop.

Every attempt is recorded to `data/notifications.json` so `status.py` can show when
something was last delivered and whether it failed. An operator who has heard nothing for
two days can then tell "nothing happened" from "nothing was sent".

## What travels, and what does not

Ian chose full detail on both money lanes on 2026-08-08: for arb, the selection, both
books, the odds, the stake and the guaranteed return; for stocks, the shares, the ticker,
the price and the reason. That is a deliberate trade -- a Telegram message sits on somebody
else's server and this repository gitignores exactly this data because it is sensitive --
and it is made in exchange for a message that can be acted on without unlocking anything,
which for arb is the difference between a live price and a dead one.

What never travels: any credential, any key, any wallet address, and the URLs of the
endpoints that carry auth tokens in their path.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

from lib.http_retry import TransientRetrievalError, retrying_urlopen

SENT = "SENT"
REFUSED = "REFUSED"
UNREACHABLE = "UNREACHABLE"
NOT_CONFIGURED = "NOT_CONFIGURED"

#: Where attempts are recorded. A record, never a source of truth about the money.
LOG = Path("data/notifications.json")

#: Kept small on purpose. Telegram truncates around 4096 characters and a truncated
#: instruction is worse than a short one, because the part that gets cut is the tail --
#: which is where the sizing constraint and the timestamp live.
MAX_BODY = 3500

API = "https://api.telegram.org"


@dataclass(frozen=True, slots=True)
class TelegramCredentials:
    """A bot token and the chat to send to. Files, as every credential here is."""

    token: str
    chat_id: str

    @classmethod
    def load(cls, directory: str | Path = "~/.telegram") -> "TelegramCredentials | None":
        root = Path(directory).expanduser()
        token, chat = root / "bot_token", root / "chat_id"
        if not token.is_file() or not chat.is_file():
            return None
        return cls(
            token.read_text(encoding="utf-8").strip(),
            chat.read_text(encoding="utf-8").strip(),
        )


@dataclass(frozen=True, slots=True)
class Delivery:
    """What happened to one message. Four outcomes, deliberately not three.

    `NOT_CONFIGURED` is not a failure and must not read as one: a person who has not set up
    Telegram has not had a notification fail, and reporting it as `REFUSED` would send them
    looking for a broken token they never created.
    """

    status: str
    at: str
    subject: str = ""
    reason: str = ""

    @property
    def delivered(self) -> bool:
        return self.status == SENT

    def describe(self) -> str:
        if self.status == SENT:
            return f"SENT  {self.subject} at {self.at}"
        if self.status == NOT_CONFIGURED:
            return ("NOT_CONFIGURED  no Telegram credentials, so nothing was sent and "
                    "nothing failed. Put a bot token in ~/.telegram/bot_token and the "
                    "chat id in ~/.telegram/chat_id.")
        return f"{self.status}  {self.subject}: {self.reason}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class Telegram:
    """One channel. Sends, and says exactly what happened when it does not."""

    def __init__(
        self,
        credentials: TelegramCredentials | None,
        *,
        opener: Callable[..., Any] = retrying_urlopen,
        log_path: str | Path | None = None,
    ) -> None:
        self.credentials = credentials
        self._opener = opener
        # Resolved at call time rather than bound as a default, so a test can redirect it.
        # A default argument binding LOG at import is what sent a full test run's journal
        # into the live data directory once already.
        self.log_path = Path(log_path) if log_path is not None else None

    @classmethod
    def from_directory(cls, directory: str | Path = "~/.telegram", **kw: Any) -> "Telegram":
        return cls(TelegramCredentials.load(directory), **kw)

    @property
    def is_configured(self) -> bool:
        return self.credentials is not None

    def send(self, subject: str, body: str) -> Delivery:
        """Deliver one message. Never raises: a failed notification must not stop a lane.

        The lane's job is the money. If Telegram is down, the instruction is still correct
        and still recorded, and taking the run down with it would turn a messaging outage
        into a missed opportunity — which is the opposite of what this module is for.
        """

        if self.credentials is None:
            return self._record(Delivery(NOT_CONFIGURED, _now(), subject))

        text = f"{subject}\n\n{body}"
        if len(text) > MAX_BODY:
            # Truncate the MIDDLE, not the tail. The tail carries the binding constraint
            # and the timestamp, which are the parts that make an instruction actionable.
            keep = (MAX_BODY - 40) // 2
            text = f"{text[:keep]}\n\n[... trimmed ...]\n\n{text[-keep:]}"

        payload = urllib.parse.urlencode({
            "chat_id": self.credentials.chat_id,
            "text": text,
            "disable_web_page_preview": "true",
        }).encode("utf-8")
        request = urllib.request.Request(
            f"{API}/bot{self.credentials.token}/sendMessage", data=payload, method="POST"
        )
        try:
            with self._opener(request) as response:
                answered = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            # The service answered and said no. A bad token or a chat that no longer
            # exists lands here, and both want a person, not a retry.
            return self._record(Delivery(
                REFUSED, _now(), subject, f"HTTP {error.code}: {_redact(str(error))}"))
        except (urllib.error.URLError, TransientRetrievalError, OSError, ValueError) as error:
            return self._record(Delivery(
                UNREACHABLE, _now(), subject,
                f"{type(error).__name__}: {_redact(str(error))}"))

        if not answered.get("ok"):
            return self._record(Delivery(
                REFUSED, _now(), subject, _redact(str(answered.get("description", "")))[:200]))
        return self._record(Delivery(SENT, _now(), subject))

    def _record(self, delivery: Delivery) -> Delivery:
        """Append the attempt. A notifier that fails invisibly is worse than none."""

        path = self.log_path if self.log_path is not None else LOG
        try:
            rows = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else []
            if not isinstance(rows, list):
                rows = []
        except (OSError, ValueError):
            rows = []
        rows.append({"status": delivery.status, "at": delivery.at,
                     "subject": delivery.subject, "reason": delivery.reason})
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(rows[-200:], indent=2) + "\n", encoding="utf-8")
        except OSError:
            # Recording is best effort. Losing the record must not lose the message.
            pass
        return delivery


#: The token as it appears in a URL path: `/bot<digits>:<secret>/sendMessage`. Matched up
#: to the next slash so the method name and everything after it survive.
_TOKEN_IN_URL = re.compile(r"/bot[^/\s]*")


def _redact(text: str) -> str:
    """A bot token appears in the URL, and error strings quote the URL back at you.

    Only the token goes. The first version of this replaced the WHOLE string as soon as it
    contained `/bot`, which kept the secret out of the log and took the diagnosis with it —
    and a refusal that does not name what a person can go and do about it is barely a
    refusal. `HTTP 401 ... /bot<redacted>/sendMessage` says both things at once.
    """

    return _TOKEN_IN_URL.sub("/bot<redacted>", str(text))


# -- what a message says ----------------------------------------------------------------
#
# One formatter per lane, because the lanes are not alike and a common template would suit
# neither. Arb is time critical: the odds move, so the message carries everything needed to
# place without opening anything. Stocks is not a race, but carries the same detail because
# an instruction you have to go and look up is one you act on late or not at all.


def arb_message(slip: Any, *, market: str = "", at: str = "") -> tuple[str, str]:
    """Selection, books, odds, stake, return and time — enough to place from the message."""

    legs = getattr(slip, "legs", ()) or ()
    lines = [f"MARKET  {market or getattr(slip, 'market', '') or 'unnamed market'}", ""]
    for leg in legs:
        lines.append(f"{leg.book}")
        lines.append(f"  {leg.selection}  @ {leg.decimal_odds:.3f}")
        lines.append(f"  stake {leg.stake:,.2f}")
        if getattr(leg, "settlement_rule", ""):
            lines.append(f"  settles: {leg.settlement_rule}")
        lines.append("")

    stake = float(getattr(slip, "total_stake", 0.0) or 0.0)
    guaranteed = float(getattr(slip, "guaranteed_return", 0.0) or 0.0)
    profit = guaranteed - stake
    lines += [
        f"TOTAL STAKE       {stake:,.2f}",
        f"GUARANTEED RETURN {guaranteed:,.2f}",
        f"PROFIT            {profit:+,.2f}"
        + (f"  ({profit / stake * 100:.2f}%)" if stake else ""),
        "",
        # Not decoration. The stakes were computed against odds read at a moment, and a
        # bookmaker's available stake is read AT THE BOOK, never from an aggregator.
        f"READ AT  {at or getattr(slip, 'observed_at', '') or 'time not recorded'}",
        "Odds move. Re-check both books before placing; the stake each will accept is not",
        "what an aggregator reported.",
    ]
    return f"ARB READY · {len(legs)} legs · {profit:+,.2f}", "\n".join(lines)


def stocks_message(order: Any, *, thesis: Any = None,
                   why_unknown: str = "") -> tuple[str, str]:
    """Shares, ticker, price, and the short reason — what it is and why.

    `why_unknown` is the third state of the reason. An instruction reaches READY only with
    a thesis behind it, so "no reasoning attached" and "the register would not open" are
    different claims, and printing the first when the second is true tells a reader their
    gates let something through unauthorised when in fact a file failed to parse.
    """

    lines = [
        f"{order.side.upper()}  {order.shares} × {order.ticker}",
        f"  at up to {order.price:,.4f} {order.currency}   (the ask, not the mid)",
        f"  {order.cash:,.2f} {order.currency} total",
        f"  sized by: {order.bound_by}",
        "",
    ]
    reason = (getattr(thesis, "reasoning", "") or "").strip()
    if reason:
        short = reason if len(reason) <= 300 else reason[:297].rsplit(" ", 1)[0] + "..."
        lines += ["WHY (your thesis)", f"  {short}", ""]
        if getattr(thesis, "expires_at", ""):
            lines.append(f"  thesis expires {thesis.expires_at}")
            lines.append("")
    elif why_unknown:
        lines += [f"WHY  not shown: {why_unknown}.",
                  "  The instruction was authorised — this is the reason not being "
                  "readable, not the reason being absent.", ""]
    else:
        # An instruction with no stated reason is exactly what the thesis gate exists to
        # prevent, so if one reaches here the message says so rather than looking complete.
        lines += ["WHY  no thesis reasoning was attached to this instruction.", ""]

    lines.append(f"READ AT  {getattr(order, 'at', '') or 'time not recorded'}")
    return f"STOCKS READY · {order.shares} {order.ticker} · {order.cash:,.2f} {order.currency}", "\n".join(lines)


def chain_message(plan: Any, *, subject: str = "", thesis: Any = None,
                  why_unknown: str = "") -> tuple[str, str]:
    """An unsigned swap, and the fact that nothing in this system can sign it.

    The other two lanes send an instruction somebody executes at a venue. This one sends
    something to sign in a wallet the sender does not have and will never have, so the
    message says that in the subject line: an operator who reads "CHAIN READY" and waits
    for a fill is waiting for an event that cannot occur.

    Amounts are raw contract units and are labelled as such. Dividing by the decimals here
    would need to know them, getting them wrong is a factor of a thousand billion, and a
    number that might be wrong by that much should not be the one somebody eyeballs.
    """

    token = subject or getattr(plan, "token_out", "") or "unnamed token"
    lines = [
        f"BUY  {token}",
        f"  pay      {getattr(plan, 'amount_in', 0):,} units of "
        f"{getattr(plan, 'token_in', '?')}",
        f"  quoted   {getattr(plan, 'quoted_out', 0):,} units out",
        f"  at least {getattr(plan, 'min_out', 0):,} units, or the swap reverts "
        f"({getattr(plan, 'slippage_bps', 0)} bps tolerated)",
        f"  raw contract units, not decimal-adjusted. Read at block "
        f"{getattr(plan, 'block_number', 0):,}.",
        "",
        f"{len(getattr(plan, 'steps', ()) or ())} transaction(s) to sign, in order.",
        "",
    ]
    reason = (getattr(thesis, "reasoning", "") or "").strip()
    if reason:
        short = reason if len(reason) <= 300 else reason[:297].rsplit(" ", 1)[0] + "..."
        lines += ["WHY (your thesis)", f"  {short}", ""]
    elif why_unknown:
        lines += [f"WHY  not shown: {why_unknown}.", ""]
    else:
        lines += ["WHY  no thesis reasoning was attached to this instruction.", ""]

    lines += [
        "NOTHING HERE CAN SIGN THIS. The adapter has no key path, no signing library and",
        "no send method — sign the steps in a wallet you control, or they do not happen.",
        f"READ AT  {getattr(plan, 'at', '') or 'time not recorded'}",
    ]
    return f"CHAIN READY (UNSIGNED) · {token}", "\n".join(lines)


def placement_message(placement: Any) -> tuple[str, str]:
    """Money that moved, or money that may have. The second is the urgent one.

    `UNRESOLVED` is the most expensive state this system produces: an order went to the
    broker, nothing came back, and a position is on file that may or may not exist. It
    leads the subject line because a person reading three words on a lock screen has to
    get *that* one, and because the wrong reflex — resubmitting — doubles the position.
    """

    from lib.placing import PLACED, REFUSED, UNRESOLVED

    status = getattr(placement, "status", "")
    lane = getattr(placement, "lane", "?")
    subject = getattr(placement, "subject", "") or "unnamed subject"
    body = placement.describe() if hasattr(placement, "describe") else str(placement)

    if status == UNRESOLVED:
        return f"⚠ ORDER MAY EXIST · {lane} · {subject}", body
    if status == PLACED:
        return f"PLACED · {lane} · {subject}", body
    if status == REFUSED:
        return f"NOT PLACED · {lane} · {subject}", body
    # Any other status still travels rather than being dropped: a placement outcome this
    # formatter has not been taught is exactly the one worth a person's eyes.
    return f"{status or 'UNKNOWN PLACEMENT'} · {lane} · {subject}", body


def heartbeat_message(lanes: Sequence[Any], *, extra: str = "") -> tuple[str, str]:
    """The daily line whose ABSENCE is the alarm.

    It reports lanes that found nothing, deliberately. "arb ran and found nothing" is the
    message that makes tomorrow's silence mean something, and a digest that only listed
    findings would be indistinguishable from a digest that never sent.
    """

    lines = []
    for lane in lanes:
        name = getattr(lane, "lane", getattr(lane, "name", "?"))
        status = getattr(lane, "status", "?")
        detail = getattr(lane, "reason", "") or ""
        lines.append(f"{name:<8} {status}" + (f" — {detail[:90]}" if detail else ""))
    if extra:
        lines += ["", extra]
    lines += [
        "",
        "This message is the heartbeat.",
        "If a day passes with no digest, something has stopped.",
        "Check that `python run.py --serve` is running before assuming a quiet market.",
    ]
    return f"DAILY · {len(lanes)} lane(s)", "\n".join(lines)


def breaker_message(lane: str, state: Any) -> tuple[str, str]:
    """A tripped breaker stops money and does not clear itself. That needs a person."""

    return (
        f"BREAKER TRIPPED · {lane}",
        "\n".join([
            f"The {lane} breaker has tripped and the lane has stopped placing.",
            f"  {getattr(state, 'reason', '') or 'no reason recorded'}",
            "",
            "It does not reset on a timer, at midnight, or on its own. Re-arming is a",
            "human act with a stated reason:",
            f"  python -m lib.breakers reset {lane} \"<your name>\" \"<why it is now right>\"",
        ]),
    )


def blind_lane_message(lane: str, runs: int, reason: str) -> tuple[str, str]:
    """Repeated COULD_NOT_LOOK. The one a quiet market is most often mistaken for."""

    return (
        f"LANE IS BLIND · {lane}",
        "\n".join([
            f"The {lane} lane has failed to reach its source {runs} run(s) in a row.",
            f"  {reason[:200]}",
            "",
            "This is NOT a report that there was nothing to find. Nothing was looked at,",
            "so nothing about the market has been established.",
        ]),
    )
