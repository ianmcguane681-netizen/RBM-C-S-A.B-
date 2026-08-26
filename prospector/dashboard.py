"""A local dashboard with a scan button, and nothing on it that can reach a business.

The command line is the honest interface and it is not the one somebody uses on a Tuesday
morning. This is the same pipeline behind a page: pick a county, press Scan, watch it run,
open the briefings it produced. Standard library only — `http.server` and a page with no
dependencies — because adding a web framework to a package that has kept to the standard
library would be a decision, and this is a convenience.

## What is deliberately not on it

**No send button. No publish button.** Not "disabled until later" — absent. Sending is a
person reading a draft and pressing send in their own mail client, and publishing needs an
`Authorisation` naming somebody at the business. A dashboard is exactly where those two
would end up as a one-click action, and one-click is the wrong number of clicks for both.

**No stop button, because there is no honest one.** A scan is a thread doing network I/O;
killing it halfway would leave dossiers half-written and a register that disagrees with
the disk. The scan is bounded by `--limit` instead, and the page says what it is doing.

## It binds to the loopback address and nothing else

The dashboard serves contact details for real businesses and, on the costing panel, what an
hour of somebody's time is worth. That is not material to put on a public interface from a
laptop in a café, so the bind address is not configurable. Running it somewhere it needs to
be reached from another machine is a tunnel, not a flag.

## The states it can be in, which are four rather than two

    IDLE       nothing has run in this process
    RUNNING    a scan is in progress; the log is live
    FINISHED   a scan completed, and what it found is on the page
    FAILED     a scan raised, and the traceback is on the page rather than in a terminal
               nobody was watching

`FINISHED` with nothing prepared is a real answer and reads as one. It is not the same as
`FAILED`, and neither is the same as `IDLE`, which is the state that means nobody has
looked yet.
"""
from __future__ import annotations

import io
import json
import threading
import traceback
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from prospector import cli, ireland

IDLE = "IDLE"
RUNNING = "RUNNING"
FINISHED = "FINISHED"
FAILED = "FAILED"

HOST = "127.0.0.1"
DEFAULT_PORT = 8765
LOG_LINES = 400


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class _LiveLog(io.TextIOBase):
    """A stream that puts finished lines straight into the log the page is polling.

    Buffering the whole run and flushing at the end was the obvious version, and it makes
    the progress panel useless exactly while somebody is watching it — a scan of a county
    takes minutes and shows nothing until it is over.
    """

    def __init__(self, sink) -> None:
        self._sink = sink
        self._partial = ""

    def write(self, text: str) -> int:  # noqa: D102 - the stdlib documents it
        self._partial += text
        while "\n" in self._partial:
            line, self._partial = self._partial.split("\n", 1)
            self._sink.append(line)
        return len(text)

    def flush_last(self) -> None:
        if self._partial:
            self._sink.append(self._partial)
            self._partial = ""


@dataclass
class Runner:
    """One scan at a time, its log, and what it left on disk."""

    out_dir: Path
    register: Path
    costs: Path
    operator: str
    status: str = IDLE
    area: str = ""
    started: str = ""
    finished: str = ""
    exit_code: int | None = None
    error: str = ""
    log: deque = field(default_factory=lambda: deque(maxlen=LOG_LINES))
    _thread: Any = None
    _lock: Any = field(default_factory=threading.Lock)

    @property
    def running(self) -> bool:
        return self.status == RUNNING

    def start(self, **options) -> tuple[bool, str]:
        with self._lock:
            if self.running:
                return False, "a scan is already running; wait for it or open a new area "\
                              "when it finishes"
            area = str(options.get("area", "")).strip()
            if not area:
                return False, "pick an area first"
            self.status = RUNNING
            self.area = area
            self.started = _now()
            self.finished = ""
            self.exit_code = None
            self.error = ""
            self.log.clear()
        self._thread = threading.Thread(target=self._run, kwargs=options, daemon=True)
        self._thread.start()
        return True, "started"

    def _argv(self, **options) -> list[str]:
        argv = ["--area", str(options["area"]), "--operator", self.operator,
                "--out", str(self.out_dir), "--register", str(self.register),
                "--costs", str(self.costs),
                "--limit", str(int(options.get("limit", 60))),
                "--images", str(options.get("images", "both")),
                "--browser", str(options.get("browser", "auto"))]
        if options.get("language"):
            argv += ["--language", str(options["language"])]
        country = ireland.country_of(str(options["area"]))
        if country:
            argv += ["--country", country]
        if options.get("dry"):
            argv.append("--dry")
        if not options.get("fetch", True):
            argv.append("--no-fetch")
        return argv

    def _run(self, **options) -> None:
        buffer = _LiveLog(self.log)
        try:
            # The scan writes into a buffer passed to it, rather than into a redirected
            # `sys.stdout`. Redirecting the process-wide stream from a worker thread was
            # the first version of this and it swallowed everything the rest of the server
            # printed — a logging change that quietly took the log away from somebody else.
            code = cli.main(self._argv(**options), stream=buffer, errors=buffer)
            self.exit_code = code
            self.status = FINISHED
        except SystemExit as exit_called:
            # argparse exits the process on a bad argument, and `except Exception` does not
            # catch that — the worker thread died silently and the page sat on RUNNING for
            # ever. A scan that cannot start is a failure like any other.
            self.exit_code = getattr(exit_called, "code", 2)
            self.error = (f"the scan exited before it began (code {self.exit_code}) — "
                          f"usually a bad argument")
            self.status = FAILED
        except BaseException:  # noqa: BLE001 - a failed scan belongs on the page, not a void
            self.error = traceback.format_exc()
            self.status = FAILED
        finally:
            buffer.flush_last()
            if self.error:
                self.log.extend(self.error.splitlines()[-12:])
            self.finished = _now()

    def state(self) -> dict:
        return {"status": self.status, "area": self.area, "started": self.started,
                "finished": self.finished, "exit_code": self.exit_code,
                "log": list(self.log), "operator": self.operator,
                "out_dir": str(self.out_dir)}

    def dossiers(self) -> list[dict]:
        """What is on disk, read from the evidence files rather than from the log.

        The log says what a run reported; the disk says what exists. Those diverge the
        moment a run is interrupted, and the panel should show the second.
        """

        rows: list[dict] = []
        if not self.out_dir.exists():
            return rows
        for evidence_path in sorted(self.out_dir.glob("*/*/evidence.json")):
            folder = evidence_path.parent
            try:
                evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                # A dossier whose evidence will not parse is listed as broken rather than
                # skipped: a silently shorter list is how a half-written run looks fine.
                rows.append({"name": folder.name, "area": folder.parent.name,
                             "broken": True, "folder": str(folder)})
                continue
            business = evidence.get("business") or {}
            rows.append({
                "name": (business.get("name") or {}).get("value", folder.name),
                "area": folder.parent.name,
                "folder": str(folder),
                "relative": str(folder.relative_to(self.out_dir)),
                "language": evidence.get("language", ""),
                "language_reviewed": evidence.get("language_reviewed", True),
                "published": bool(evidence.get("published")),
                "engagement": evidence.get("engagement", "SAMPLE"),
                "has_briefing": (folder / "BRIEFING.html").exists(),
                "has_comparison": (folder / "COMPARISON.html").exists(),
                "broken": False,
            })
        rows.sort(key=lambda row: (row["area"], row["name"]))
        return rows


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Webatron</title>
<style>
:root{--ink:#191714;--muted:#6b6155;--line:#e4ded4;--bg:#faf7f2;--card:#fff;
--accent:#a8511f;--good:#2f6a43;--bad:#8c2f16;--band:#efe8dd}
@media (prefers-color-scheme:dark){:root{--ink:#f4efe7;--muted:#a99f92;--line:#332f2a;
--bg:#141311;--card:#1d1b18;--accent:#e0925c;--good:#77b98d;--bad:#e0836a;--band:#1a1815}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.6 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial}
.serif{font-family:ui-serif,Georgia,"Iowan Old Style",serif}
.wrap{max-width:70rem;margin:0 auto;padding:26px clamp(16px,3vw,28px) 70px}
header{display:flex;flex-wrap:wrap;align-items:baseline;gap:12px;margin-bottom:22px}
h1{font-size:30px;margin:0;letter-spacing:-.02em}
.tag{color:var(--muted);font-size:13px}
.grid{display:grid;gap:16px;grid-template-columns:minmax(260px,320px) 1fr}
@media (max-width:860px){.grid{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 18px}
h2{font-size:11.5px;letter-spacing:.13em;text-transform:uppercase;color:var(--muted);
margin:0 0 12px;font-weight:600}
label{display:block;font-size:12px;color:var(--muted);margin:12px 0 4px}
select,input{width:100%;padding:9px 10px;border:1px solid var(--line);border-radius:9px;
background:var(--bg);color:var(--ink);font:inherit;font-size:14px}
optgroup{font-style:normal}
.row{display:flex;gap:10px}
.row>*{flex:1}
button{margin-top:16px;width:100%;padding:13px 18px;border:0;border-radius:10px;
background:var(--accent);color:#fff;font:inherit;font-weight:650;font-size:16px;
cursor:pointer}
button[disabled]{opacity:.45;cursor:not-allowed}
.note{color:var(--muted);font-size:12px;margin:10px 0 0}
.state{display:flex;align-items:center;gap:9px;font-weight:650;font-size:15px}
.dot{width:9px;height:9px;border-radius:50%;background:var(--muted)}
.dot.RUNNING{background:var(--accent);animation:pulse 1.1s infinite}
.dot.FINISHED{background:var(--good)}
.dot.FAILED{background:var(--bad)}
@keyframes pulse{50%{opacity:.25}}
pre{background:var(--band);border-radius:10px;padding:12px;margin:12px 0 0;
max-height:340px;overflow:auto;font-size:12px;line-height:1.5;white-space:pre-wrap}
table{width:100%;border-collapse:collapse;font-size:14px}
th{text-align:left;font-size:11px;letter-spacing:.1em;text-transform:uppercase;
color:var(--muted);padding:0 8px 8px 0;font-weight:600}
td{border-top:1px solid var(--line);padding:9px 8px 9px 0;vertical-align:top}
td a{color:var(--accent)}
.pill{display:inline-block;font-size:11px;padding:2px 7px;border-radius:20px;
border:1px solid var(--line);color:var(--muted)}
.pill.warn{color:var(--bad);border-color:var(--bad)}
.empty{color:var(--muted);font-size:14px}
footer{margin-top:26px;color:var(--muted);font-size:12px;border-top:1px solid var(--line);
padding-top:14px}
</style>
</head>
<body><div class="wrap">
<header>
  <h1 class="serif">Webatron</h1>
  <span class="tag">local only &middot; nothing here sends or publishes</span>
</header>
<div class="grid">
  <div>
    <div class="card">
      <h2>Scan an area</h2>
      <label for="area">Area</label>
      <select id="area"></select>
      <p class="note" id="areanote"></p>
      <div class="row">
        <div><label for="limit">Limit</label><input id="limit" type="number" value="60"
          min="1" max="500"></div>
        <div><label for="images">Images</label><select id="images">
          <option>both</option><option>subject</option><option>stock</option>
          <option>none</option></select></div>
      </div>
      <div class="row">
        <div><label for="browser">Browser</label><select id="browser">
          <option value="auto">auto</option><option value="never">never</option>
        </select></div>
        <div><label for="dry">Mode</label><select id="dry">
          <option value="">write dossiers</option><option value="1">dry run</option>
        </select></div>
      </div>
      <button id="go">Scan</button>
      <p class="note" id="msg"></p>
    </div>
    <div class="card" style="margin-top:16px">
      <h2>What this cannot do</h2>
      <p class="note">There is no send button and no publish button, and neither is
      missing by accident. Sending is you, in your own mail client, having read the draft.
      Publishing needs an authorisation naming somebody at the business.</p>
      <p class="note">There is no stop button either: a half-killed scan leaves dossiers
      part-written and a register that disagrees with the disk. Use the limit.</p>
    </div>
  </div>
  <div>
    <div class="card">
      <h2>Run</h2>
      <div class="state"><span class="dot" id="dot"></span><span id="status">IDLE</span>
        <span class="tag" id="when"></span></div>
      <pre id="log">Nothing has run in this process yet. That is not the same as a scan
that found nothing.</pre>
    </div>
    <div class="card" style="margin-top:16px">
      <h2>Dossiers on disk</h2>
      <div id="dossiers"><p class="empty">None yet.</p></div>
    </div>
  </div>
</div>
<footer id="foot"></footer>
</div>
<script>
const $ = (id) => document.getElementById(id);
let areas = [];

async function loadAreas() {
  const data = await (await fetch("/api/areas")).json();
  areas = data.areas;
  const groups = {};
  for (const area of areas) (groups[area.group] ||= []).push(area);
  $("area").innerHTML = Object.entries(groups).map(([name, list]) =>
    `<optgroup label="${name}">` + list.map(a =>
      `<option value="${a.name}">${a.name}</option>`).join("") + `</optgroup>`).join("");
  showNote();
}

function showNote() {
  const picked = areas.find(a => a.name === $("area").value);
  $("areanote").textContent = picked && picked.note
    ? picked.note + (picked.also ? ` · also try "${picked.also}"` : "")
    : (picked && picked.also ? `also try "${picked.also}"` : "");
}

async function refresh() {
  const state = await (await fetch("/api/state")).json();
  $("status").textContent = state.status;
  $("dot").className = "dot " + state.status;
  $("when").textContent = state.area
    ? `${state.area}${state.finished ? " · finished " + state.finished : ""}` : "";
  if (state.log.length) $("log").textContent = state.log.join("\\n");
  $("go").disabled = state.status === "RUNNING";
  $("go").textContent = state.status === "RUNNING" ? "Scanning…" : "Scan";
  $("foot").textContent = `Operator: ${state.operator} · dossiers in ${state.out_dir}`;
  const rows = (await (await fetch("/api/dossiers")).json()).dossiers;
  $("dossiers").innerHTML = rows.length ? `<table><thead><tr><th>Business</th>
    <th>Area</th><th>Stage</th><th>Open</th></tr></thead><tbody>` + rows.map(row => {
      if (row.broken) return `<tr><td>${row.name}</td><td>${row.area}</td>
        <td><span class="pill warn">evidence will not parse</span></td><td></td></tr>`;
      const flags = [row.published ? '<span class="pill">live</span>' : "",
        row.language_reviewed ? "" :
          `<span class="pill warn">${row.language} unreviewed</span>`].join(" ");
      const links = [row.has_briefing ?
          `<a href="/files/${row.relative}/BRIEFING.html">briefing</a>` : "",
        `<a href="/files/${row.relative}/index.html">site</a>`,
        row.has_comparison ?
          `<a href="/files/${row.relative}/COMPARISON.html">before/after</a>` : ""
        ].filter(Boolean).join(" · ");
      return `<tr><td>${row.name}</td><td>${row.area}</td>
        <td>${row.engagement} ${flags}</td><td>${links}</td></tr>`;
    }).join("") + "</tbody></table>" : '<p class="empty">None yet.</p>';
}

$("area").addEventListener("change", showNote);
$("go").addEventListener("click", async () => {
  $("msg").textContent = "";
  const body = {area: $("area").value, limit: Number($("limit").value),
    images: $("images").value, browser: $("browser").value, dry: !!$("dry").value};
  const response = await fetch("/api/scan", {method: "POST",
    headers: {"content-type": "application/json"}, body: JSON.stringify(body)});
  const data = await response.json();
  if (!data.started) $("msg").textContent = data.message;
  refresh();
});

loadAreas().then(refresh);
setInterval(refresh, 2000);
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    """The routes. There is no route that sends anything and none that publishes."""

    runner: Runner = None  # type: ignore[assignment]
    server_version = "Webatron"

    def log_message(self, fmt, *args):  # noqa: A003 - quieten the default access log
        pass

    def _send(self, code: int, body: bytes, kind: str = "application/json") -> None:
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        # A dashboard holding client contact details has no business in a cache or in
        # somebody else's frame.
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, payload: dict) -> None:
        self._send(code, json.dumps(payload, default=str).encode("utf-8"))

    def _serve_file(self, relative: str) -> None:
        """Files from the dossier directory, and provably nothing else."""

        root = self.runner.out_dir.resolve()
        target = (root / unquote(relative)).resolve()
        if not target.is_relative_to(root) or not target.is_file():
            # The traversal guard is a refusal rather than a 404 with a hint: the caller
            # asked for something outside the tree and there is nothing to negotiate.
            self._json(404, {"error": "no such file inside the dossier directory"})
            return
        kinds = {".html": "text/html; charset=utf-8", ".png": "image/png",
                 ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",
                 ".json": "application/json", ".md": "text/plain; charset=utf-8"}
        self._send(200, target.read_bytes(),
                   kinds.get(target.suffix.lower(), "application/octet-stream"))

    def do_GET(self) -> None:  # noqa: N802 - the stdlib spells it this way
        path = urlparse(self.path).path
        if path == "/":
            self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
        elif path == "/api/areas":
            self._json(200, {"areas": [
                {"name": area.name, "note": area.note, "also": area.also,
                 "group": "Republic of Ireland" if area.country == ireland.IE
                          else "Northern Ireland (UK rules)"}
                for area in ireland.areas()]})
        elif path == "/api/state":
            self._json(200, self.runner.state())
        elif path == "/api/dossiers":
            self._json(200, {"dossiers": self.runner.dossiers()})
        elif path.startswith("/files/"):
            self._serve_file(path[len("/files/"):])
        else:
            self._json(404, {"error": "no such route"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path != "/api/scan":
            self._json(404, {"error": "no such route"})
            return
        length = int(self.headers.get("Content-Length") or 0)
        try:
            options = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            self._json(400, {"started": False, "message": "that was not JSON"})
            return
        started, message = self.runner.start(**options)
        self._json(200 if started else 409, {"started": started, "message": message})


def serve(runner: Runner, port: int = DEFAULT_PORT) -> ThreadingHTTPServer:
    handler = type("BoundHandler", (Handler,), {"runner": runner})
    return ThreadingHTTPServer((HOST, port), handler)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="prospector.dashboard",
        description="A local page with a scan button. Binds to 127.0.0.1 only.")
    parser.add_argument("--operator", required=True,
                        help="the person the samples are signed by; the same rules as the "
                             "command line apply and an automation is refused")
    parser.add_argument("--out", default="dossiers")
    parser.add_argument("--register", default="data/prepared.json")
    parser.add_argument("--costs", default="data/costs.json")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args(argv)

    lowered = args.operator.strip().lower()
    if lowered in cli.REFUSED_OPERATORS or any(lowered.startswith(prefix)
                                               for prefix in cli.AUTOMATION_PREFIXES):
        print(f"REFUSED: --operator {args.operator!r} names an automation.")
        return 2

    runner = Runner(out_dir=Path(args.out), register=Path(args.register),
                    costs=Path(args.costs), operator=args.operator)
    server = serve(runner, args.port)
    print(f"Webatron on http://{HOST}:{args.port}  (loopback only — it holds contact "
          f"details and your rates)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
