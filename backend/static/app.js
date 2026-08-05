const $ = (id) => document.getElementById(id);
const money = (value, currency = "EUR") => value == null ? "—" : new Intl.NumberFormat("en-IE", {style:"currency",currency,maximumFractionDigits:2}).format(value);
const safe = (value) => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
// Presentation only. A lane the UI has no label for still renders, titled from its own id
// and iconed with its first letter, because more lanes are planned and a dashboard that
// prints "undefined Division" for a live money lane is worse than one that prints "Flipper".
// Nothing here decides which lanes exist; that comes from the API.
const laneLabels = {stocks:"Stocks",crypto:"Crypto",arb:"Arbitrage"};
const laneGlyphs = {stocks:"S",crypto:"₿",arb:"A"};
const titleCase = (id) => String(id ?? "").replace(/[-_]/g," ").replace(/\b\w/g,c=>c.toUpperCase());
const laneName = (id) => laneLabels[id] || titleCase(id) || "UNKNOWN LANE";
const laneIcon = (id) => laneGlyphs[id] || (String(id ?? "?")[0] || "?").toUpperCase();
const offlineOverview = {generated_at:"OFFLINE PREVIEW",capital:{cost_basis:null,currency:"EUR",value_status:"NO LIVE API",is_complete:false},decisions:{open:null,limit:12,items:[]},engines:[{lane:"stocks",status:"NOT_CONNECTED"},{lane:"crypto",status:"NOT_CONNECTED"},{lane:"arb",status:"NOT_CONNECTED"}],money_lanes:["stocks","crypto","arb"].map(lane=>({lane,balance:null,currency:"EUR",breaker:{status:"UNKNOWN"},positions:{open:null}})),recent_runs:[]};
const offlineConnectors = {lanes:["stocks","crypto","arb"].map(lane=>({lane,status:"NOT_CONNECTED",missing:["Start the operator API for live state"]}))};

function divisionCard(engine, moneyLane) {
  const status = engine?.status || "NOT_CONFIGURED";
  const balance = moneyLane?.balance;
  const positions = moneyLane?.positions || {};
  return `<article class="division lane-${safe(engine.lane)}">
    <div class="division-head"><span class="division-icon">${laneIcon(engine.lane)}</span><div><h2>${safe(laneName(engine.lane))} Division</h2><div class="subtitle">Research · Controls · Execution</div></div></div>
    <div class="division-row"><div><label>RING-FENCE</label><b>${money(balance,moneyLane?.currency||"EUR")}</b></div><div><label>OPEN POSITIONS</label><b>${positions.open ?? "UNKNOWN"}</b></div></div>
    <div class="state ${status.toLowerCase()}">${safe(status)}</div>
    <a class="button secondary" href="/api/v1/overview">VIEW DIVISION STATE</a>
  </article>`;
}

// --- the three sections added when the journal, the quota and realised P&L landed ------

// A realised figure is the honest half of a picture whose other half may be missing, so
// the badge travels with the number. A lane showing +39.00 with a position still open and
// an UNKNOWN outstanding has not made 39.00; it has made it on the part that finished.
function realisedRow(lane) {
  const r = lane.realised || {};
  const partial = r.status === "PARTIAL";
  const label = {COMPLETE:"whole book", PARTIAL:"part only", NOTHING_SETTLED:"nothing settled",
                 UNREADABLE:"unreadable", NOT_CONFIGURED:"no ledger"}[r.status] || r.status || "UNKNOWN";
  const figure = r.realised_profit == null ? "—" : money(r.realised_profit, r.currency || lane.currency || "EUR");
  const tone = r.realised_profit == null ? "" : (r.realised_profit >= 0 ? "up" : "down");
  const caveat = partial
    ? `${r.still_open ?? 0} open · ${r.unknown ?? 0} unknown not counted`
    : (r.void ? `${r.void} void excluded` : label);
  return `<div class="realised-row"><span>${safe(laneName(lane.lane))}<small>${safe(caveat)}</small></span>` +
         `<b class="${tone}">${figure}</b></div>`;
}

function renderRealised(lanes) {
  $("realised-list").innerHTML = lanes.length
    ? lanes.map(realisedRow).join("")
    : `<div class="empty">No money lane is configured.</div>`;

  // The headline tile, and three separate reasons to withhold it.
  //
  // The third was found by running mock numbers through this page: the arb lane rings
  // its fence in EUR and the stocks lane in USD, and the first version added 39.00 to
  // -77.00 and printed -EUR 38.00. That is not a conversion, it is two different units
  // added together, and no price source here can convert them. A total across mixed
  // currencies is not a number — the per-lane rows below are the answer, and the tile
  // says so rather than inventing a rate.
  const contributing = lanes.filter(l => typeof l.realised?.realised_profit === "number");
  const unreadable = lanes.some(l => l.realised?.status === "UNREADABLE");
  const partial = lanes.some(l => l.realised?.status === "PARTIAL");
  const currencies = new Set(contributing.map(l => l.realised.currency || l.currency || "EUR"));

  if (unreadable || !contributing.length) {
    $("realised-total").textContent = "—";
    $("realised-total").className = "";
    $("realised-state").textContent = unreadable ? "A ledger could not be read" : "Nothing has settled";
    return;
  }
  if (currencies.size > 1) {
    $("realised-total").textContent = "—";
    $("realised-total").className = "";
    $("realised-state").textContent =
      `${[...currencies].join(" and ")} cannot be added · see the per-lane figures`;
    return;
  }
  const total = contributing.reduce((a, l) => a + l.realised.realised_profit, 0);
  $("realised-total").textContent = money(total, [...currencies][0]);
  $("realised-total").className = total >= 0 ? "up" : "down";
  $("realised-state").textContent = partial
    ? "PARTIAL · open and unknown positions are not in this"
    : "Covers every settled position";
}

// Running out of quota reads as no arbs, so the count is a safety control and sits with
// them. UNKNOWN is not nought: it means nothing has measured it yet.
function renderQuota(lanes) {
  const arb = lanes.find(l => l.lane === "arb");
  const q = arb?.quota;
  if (!q) { $("quota").innerHTML = `<div><span>Odds API</span><b>UNKNOWN</b></div>`; return; }
  const remaining = q.status === "KNOWN" ? q.remaining : null;
  const low = remaining != null && remaining <= (q.floor ?? 25);
  $("quota").innerHTML =
    `<div><span>Requests remaining</span><b class="${low ? "down" : ""}">${remaining ?? "UNKNOWN"}</b></div>` +
    `<div><span>Spending floor</span><b>${q.floor ?? "—"}</b></div>` +
    (q.burn ? `<div><span>At this cadence</span><b class="${q.fits ? "" : "down"}">${safe(q.burn)}</b></div>` : "");
}

// EMPTY and UNREADABLE are different facts, and the difference matters most here: a system
// running for weeks must not read as one that has never run.
function renderHistory(history) {
  const tag = $("journal-tag");
  if (!history || history.status === "UNREADABLE") {
    tag.textContent = "UNREADABLE";
    $("reap-history").innerHTML =
      `<div class="empty">The run journal could not be opened.<br>` +
      `<small>This is not a system that has never run; it is one whose record cannot be read.</small></div>`;
    return;
  }
  const runs = history.runs || [];
  tag.textContent = `${history.counts?.reaper_runs ?? 0} RUNS`;
  if (!runs.length) {
    $("reap-history").innerHTML =
      `<div class="empty">No run has been recorded yet.<br>` +
      `<small>This is not the same as a run that found nothing.</small></div>`;
    return;
  }
  $("reap-history").innerHTML = runs.map(r => {
    const blind = r.status === "COULD_NOT_LOOK";
    return `<div class="run-row"><span>${safe(laneName(r.lane) || "all lanes")}` +
           `<small class="${blind ? "down" : ""}">${safe(r.status)}` +
           `${r.reason ? " · " + safe(r.reason) : ""}</small></span>` +
           `<time>${safe(r.at)}</time></div>`;
  }).join("");
}

function renderOverview(data) {
  const capital = data.capital || {}, decisions = data.decisions || {}, engines = data.engines || [], lanes = data.money_lanes || [];
  $("capital-cost").textContent = money(capital.cost_basis, capital.currency || "EUR");
  $("capital-state").textContent = capital.value_status || "UNKNOWN";
  $("side-capital").textContent = money(capital.cost_basis, capital.currency || "EUR");
  $("valuation-note").textContent = capital.value_status === "PRICED" ? "Current valuation complete" : `${capital.value_status || "UNKNOWN"} · no unsupported valuation shown`;
  $("decision-count").textContent = decisions.open ?? "—";
  $("decision-limit").textContent = `Queue capacity ${decisions.limit ?? "unknown"}`;
  const positionValues = lanes.map(l => l.positions?.open).filter(Number.isFinite);
  $("position-count").textContent = positionValues.length === lanes.length ? positionValues.reduce((a,b)=>a+b,0) : "—";
  $("position-state").textContent = positionValues.length === lanes.length ? "Across configured ledgers" : "One or more ledgers unknown";
  const ready = engines.filter(e => e.status === "READY").length;
  $("engine-count").textContent = `${ready}/${engines.length}`;
  $("engine-state").textContent = ready === engines.length ? "All evidence sources ready" : "Attention required";
  // The badge was the literal "3 LANES" in the HTML. It had an id and nothing ever
  // set it, so a fourth lane made the page state a count contradicted by the list
  // directly beneath it.
  $("reaper-total").textContent = `${engines.length} LANE${engines.length === 1 ? "" : "S"}`;
  $("division-grid").innerHTML = engines.map(e => divisionCard(e, lanes.find(l=>l.lane===e.lane))).join("");
  $("reaper-list").innerHTML = engines.map(e => `<div><span>${safe(laneName(e.lane))}</span><span class="status-pill ${e.status.toLowerCase()}">${safe(e.status)}</span></div>`).join("");
  $("safety-list").innerHTML = lanes.map(l => `<div><span>${safe(laneName(l.lane))} breaker</span><b>${safe(l.breaker?.status || "UNKNOWN")}</b></div>`).join("");
  $("system-posture").innerHTML = [`${engines.length} evidence engines registered`,`${lanes.length} governed money lanes`,`${decisions.open ?? "Unknown"} decisions awaiting attention`,capital.is_complete ? "Portfolio valuation complete" : "Incomplete valuation disclosed"].map(x=>`<li>${safe(x)}</li>`).join("");
  $("runs").innerHTML = data.recent_runs?.length ? data.recent_runs.map(r=>`<div class="run-row"><span>${safe(r.lane)}<small>${safe(r.status)}</small></span><time>${safe(r.at)}</time></div>`).join("") : `<div class="empty">No runs have been recorded yet.<br><small>This is not the same as a run finding nothing.</small></div>`;
  $("decisions").innerHTML = decisions.items?.length ? decisions.items.map(d=>`<div class="decision-row"><span>${safe(d.subject)}<small>${safe(d.lane)}</small></span><time>${safe(d.raised_at)}</time></div>`).join("") : `<div class="empty">Decision queue is empty.</div>`;
  renderRealised(lanes);
  renderQuota(lanes);
  renderHistory(data.reap_history);
  $("generated").textContent = `STATE ${data.generated_at || "UNKNOWN"}`;
}

function renderConnectors(data) {
  $("connectors").innerHTML = data.lanes.map(l=>`<div class="connector-row"><span>${safe(laneName(l.lane))}<small>${safe(l.missing?.join(", ") || "All requirements present")}</small></span><b class="${l.status.toLowerCase()}">${safe(l.status)}</b></div>`).join("");
}

// The VIEW key only, never the command key. sessionStorage rather than localStorage so it
// dies with the tab, and read-only so that what an XSS could steal is the ability to see
// what the CLI already prints rather than the ability to run a lane.
const VIEW_KEY = "provena-view-key";
const viewKey = () => sessionStorage.getItem(VIEW_KEY) || "";
const authed = () => viewKey() ? {"X-Provena-View-Key": viewKey()} : {};

function askForViewKey() {
  const entered = window.prompt(
    "This dashboard needs the read-only view key (PROVENA_VIEW_KEY on the server).\n\n" +
    "Do NOT paste the command key here — that one runs lanes, and nothing that can move " +
    "money belongs in a browser."
  );
  if (entered === null) return false;
  sessionStorage.setItem(VIEW_KEY, entered.trim());
  return true;
}

function keyPrompt(message) {
  $("connection").className = "connection error";
  $("connection").innerHTML = `<span></span> ${safe(message)} · <a href="#" id="enter-key">enter view key</a>`;
  $("enter-key").onclick = (event) => { event.preventDefault(); if (askForViewKey()) boot(); };
}

async function boot() {
  if (location.protocol === "file:") {
    renderOverview(offlineOverview); renderConnectors(offlineConnectors);
    $("connection").className = "connection error";
    $("connection").innerHTML = "<span></span> Offline layout preview · start python -m backend for live state";
    return;
  }
  try {
    const options = {headers: authed()};
    const [overview, connectors] = await Promise.all([fetch("/api/v1/overview",options),fetch("/api/v1/connectors",options)]);
    // 503 and 401 are not "no API". The lane data is behind a key, and a page reporting a
    // running server as offline sends its reader to restart a service that is already up.
    // Name the actual cause; the refusal has a thing a person can go and do.
    if (overview.status === 503 || connectors.status === 503) {
      renderOverview(offlineOverview); renderConnectors(offlineConnectors);
      $("connection").className = "connection error";
      $("connection").innerHTML = "<span></span> API is running · no key is set on the server, so no lane data is served. Set PROVENA_VIEW_KEY";
      return;
    }
    if (overview.status === 401 || connectors.status === 401) {
      sessionStorage.removeItem(VIEW_KEY);
      renderOverview(offlineOverview); renderConnectors(offlineConnectors);
      keyPrompt("API is running · this view needs the read-only key");
      return;
    }
    if (!overview.ok || !connectors.ok) throw new Error(`API returned ${overview.status}/${connectors.status}`);
    renderOverview(await overview.json()); renderConnectors(await connectors.json());
    $("connection").className = "connection online"; $("connection").innerHTML = "<span></span> Operator API connected";
  } catch (error) {
    // Static hosts have no Python API. Render a truthful layout rather than leaving loading
    // skeletons forever; zero is never substituted for state that could not be retrieved.
    renderOverview(offlineOverview); renderConnectors(offlineConnectors);
    $("connection").className = "connection error";
    $("connection").innerHTML = `<span></span> Offline layout preview · ${safe(error.message)}`;
  }
}
boot();
