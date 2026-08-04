const $ = (id) => document.getElementById(id);
const money = (value, currency = "EUR") => value == null ? "—" : new Intl.NumberFormat("en-IE", {style:"currency",currency,maximumFractionDigits:2}).format(value);
const safe = (value) => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const laneNames = {stocks:"Stocks",crypto:"Crypto",arb:"Arbitrage"};
const laneIcons = {stocks:"S",crypto:"₿",arb:"A"};
const offlineOverview = {generated_at:"OFFLINE PREVIEW",capital:{cost_basis:null,currency:"EUR",value_status:"NO LIVE API",is_complete:false},decisions:{open:null,limit:12,items:[]},engines:[{lane:"stocks",status:"NOT_CONNECTED"},{lane:"crypto",status:"NOT_CONNECTED"},{lane:"arb",status:"NOT_CONNECTED"}],money_lanes:["stocks","crypto","arb"].map(lane=>({lane,balance:null,currency:"EUR",breaker:{status:"UNKNOWN"},positions:{open:null}})),recent_runs:[]};
const offlineConnectors = {lanes:["stocks","crypto","arb"].map(lane=>({lane,status:"NOT_CONNECTED",missing:["Start the operator API for live state"]}))};

function divisionCard(engine, moneyLane) {
  const status = engine?.status || "NOT_CONFIGURED";
  const balance = moneyLane?.balance;
  const positions = moneyLane?.positions || {};
  return `<article class="division lane-${safe(engine.lane)}">
    <div class="division-head"><span class="division-icon">${laneIcons[engine.lane]}</span><div><h2>${laneNames[engine.lane]} Division</h2><div class="subtitle">Research · Controls · Execution</div></div></div>
    <div class="division-row"><div><label>RING-FENCE</label><b>${money(balance,moneyLane?.currency||"EUR")}</b></div><div><label>OPEN POSITIONS</label><b>${positions.open ?? "UNKNOWN"}</b></div></div>
    <div class="state ${status.toLowerCase()}">${safe(status)}</div>
    <a class="button secondary" href="/api/v1/overview">VIEW DIVISION STATE</a>
  </article>`;
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
  $("division-grid").innerHTML = engines.map(e => divisionCard(e, lanes.find(l=>l.lane===e.lane))).join("");
  $("reaper-list").innerHTML = engines.map(e => `<div><span>${laneNames[e.lane] || safe(e.lane)}</span><span class="status-pill ${e.status.toLowerCase()}">${safe(e.status)}</span></div>`).join("");
  $("safety-list").innerHTML = lanes.map(l => `<div><span>${laneNames[l.lane]} breaker</span><b>${safe(l.breaker?.status || "UNKNOWN")}</b></div>`).join("");
  $("system-posture").innerHTML = [`${engines.length} evidence engines registered`,`${lanes.length} governed money lanes`,`${decisions.open ?? "Unknown"} decisions awaiting attention`,capital.is_complete ? "Portfolio valuation complete" : "Incomplete valuation disclosed"].map(x=>`<li>${safe(x)}</li>`).join("");
  $("runs").innerHTML = data.recent_runs?.length ? data.recent_runs.map(r=>`<div class="run-row"><span>${safe(r.lane)}<small>${safe(r.status)}</small></span><time>${safe(r.at)}</time></div>`).join("") : `<div class="empty">No runs have been recorded yet.<br><small>This is not the same as a run finding nothing.</small></div>`;
  $("decisions").innerHTML = decisions.items?.length ? decisions.items.map(d=>`<div class="decision-row"><span>${safe(d.subject)}<small>${safe(d.lane)}</small></span><time>${safe(d.raised_at)}</time></div>`).join("") : `<div class="empty">Decision queue is empty.</div>`;
  $("generated").textContent = `STATE ${data.generated_at || "UNKNOWN"}`;
}

function renderConnectors(data) {
  $("connectors").innerHTML = data.lanes.map(l=>`<div class="connector-row"><span>${laneNames[l.lane]}<small>${safe(l.missing?.join(", ") || "All requirements present")}</small></span><b class="${l.status.toLowerCase()}">${safe(l.status)}</b></div>`).join("");
}

async function boot() {
  if (location.protocol === "file:") {
    renderOverview(offlineOverview); renderConnectors(offlineConnectors);
    $("connection").className = "connection error";
    $("connection").innerHTML = "<span></span> Offline layout preview · start python -m backend for live state";
    return;
  }
  try {
    const [overview, connectors] = await Promise.all([fetch("/api/v1/overview"),fetch("/api/v1/connectors")]);
    // 503 and 401 are not "no API". The lane data is behind the command key, and a page
    // reporting a running server as offline sends its reader to restart a service that is
    // already up. Name the actual cause; the refusal has a thing a person can go and do.
    if (overview.status === 503 || connectors.status === 503) throw new Error("API is running · PROVENA_COMMAND_KEY is not set on the server, so no lane data is served");
    if (overview.status === 401 || connectors.status === 401) throw new Error("API is running · this view needs the X-Provena-Command-Key header; the browser does not hold it");
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
