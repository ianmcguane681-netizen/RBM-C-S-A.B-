-- Operational read model for reapers, executions and the operator UI.
-- Apply after the board schema migration. The service role appends; dashboard roles read
-- only the deliberately narrow views at the bottom of this file.

BEGIN;

CREATE SCHEMA IF NOT EXISTS operations;

CREATE TABLE operations.connector_checks (
    check_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lane TEXT NOT NULL CHECK (lane IN ('arb', 'stocks', 'crypto')),
    connector TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN (
        'READY', 'CONFIGURED', 'NOT_CONFIGURED', 'UNREACHABLE', 'NOT_ATTEMPTED'
    )),
    detail TEXT NOT NULL DEFAULT '',
    checked_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE operations.reaper_runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lane TEXT CHECK (lane IS NULL OR lane IN ('arb', 'stocks', 'crypto')),
    dry_run BOOLEAN NOT NULL,
    status TEXT NOT NULL CHECK (status IN (
        'RUNNING', 'COMPLETED', 'REFUSED', 'COULD_NOT_LOOK', 'FAILED'
    )),
    looked BOOLEAN,
    requested_by TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    refusal TEXT NOT NULL DEFAULT '',
    error_code TEXT,
    CHECK ((status = 'RUNNING' AND completed_at IS NULL) OR status <> 'RUNNING')
);

CREATE TABLE operations.harvests (
    harvest_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES operations.reaper_runs(run_id),
    lane TEXT NOT NULL CHECK (lane IN ('arb', 'stocks', 'crypto')),
    subject TEXT NOT NULL,
    status TEXT NOT NULL,
    reason TEXT NOT NULL DEFAULT '',
    instruction JSONB,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (run_id, lane, subject)
);

CREATE TABLE operations.executions (
    execution_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    harvest_id UUID NOT NULL REFERENCES operations.harvests(harvest_id),
    lane TEXT NOT NULL CHECK (lane IN ('arb', 'stocks', 'crypto')),
    subject TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN (
        'PLACED', 'UNRESOLVED', 'NOT_PLACED', 'REFUSED'
    )),
    position_id TEXT,
    client_order_id TEXT,
    requested_quantity NUMERIC,
    filled_quantity NUMERIC,
    reason TEXT NOT NULL DEFAULT '',
    provider_payload JSONB,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (lane, client_order_id)
);

CREATE TABLE operations.positions (
    position_id TEXT PRIMARY KEY,
    lane TEXT NOT NULL CHECK (lane IN ('arb', 'stocks', 'crypto')),
    subject TEXT NOT NULL,
    stake NUMERIC NOT NULL CHECK (stake > 0),
    currency TEXT NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('MANUAL', 'BROKER', 'CHAIN')),
    status TEXT NOT NULL CHECK (status IN ('OPEN', 'SETTLED', 'VOID', 'UNKNOWN')),
    returned NUMERIC,
    opened_at TIMESTAMPTZ NOT NULL,
    resolved_at TIMESTAMPTZ,
    applied_to_breakers BOOLEAN NOT NULL DEFAULT false,
    note TEXT NOT NULL DEFAULT '',
    CHECK ((status IN ('OPEN', 'UNKNOWN') AND resolved_at IS NULL)
        OR (status IN ('SETTLED', 'VOID') AND resolved_at IS NOT NULL)),
    CHECK (status <> 'SETTLED' OR returned IS NOT NULL)
);

CREATE TABLE operations.capital_snapshots (
    snapshot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lane TEXT NOT NULL CHECK (lane IN ('arb', 'stocks', 'crypto')),
    currency TEXT NOT NULL,
    cost_basis NUMERIC NOT NULL,
    priced_value NUMERIC,
    value_status TEXT NOT NULL CHECK (value_status IN (
        'PRICED', 'PARTIALLY_UNPRICED', 'UNPRICED', 'EMPTY_BOOK'
    )),
    captured_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE operations.alerts (
    alert_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lane TEXT CHECK (lane IS NULL OR lane IN ('arb', 'stocks', 'crypto')),
    kind TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('INFO', 'WARNING', 'CRITICAL')),
    status TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'ACKNOWLEDGED', 'RESOLVED')),
    subject TEXT NOT NULL,
    detail TEXT NOT NULL,
    deduplication_key TEXT NOT NULL,
    raised_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    acknowledged_at TIMESTAMPTZ,
    acknowledged_by TEXT,
    resolved_at TIMESTAMPTZ,
    UNIQUE (deduplication_key, status),
    CHECK ((acknowledged_at IS NULL) = (acknowledged_by IS NULL))
);

CREATE TABLE operations.notification_deliveries (
    delivery_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id UUID NOT NULL REFERENCES operations.alerts(alert_id),
    channel TEXT NOT NULL CHECK (channel IN ('discord', 'email', 'slack')),
    status TEXT NOT NULL CHECK (status IN ('PENDING', 'SENT', 'FAILED')),
    provider_reference TEXT,
    attempted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    error_detail TEXT NOT NULL DEFAULT ''
);

-- No client role writes operational truth. All mutation goes through the backend service.
ALTER TABLE operations.connector_checks ENABLE ROW LEVEL SECURITY;
ALTER TABLE operations.reaper_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE operations.harvests ENABLE ROW LEVEL SECURITY;
ALTER TABLE operations.executions ENABLE ROW LEVEL SECURITY;
ALTER TABLE operations.positions ENABLE ROW LEVEL SECURITY;
ALTER TABLE operations.capital_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE operations.alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE operations.notification_deliveries ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON SCHEMA operations FROM anon, authenticated;
REVOKE ALL ON ALL TABLES IN SCHEMA operations FROM anon, authenticated;
GRANT USAGE ON SCHEMA operations TO service_role;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA operations TO service_role;

-- The UI receives deliberately limited projections. Provider payloads, connector details,
-- command actors and notification errors never cross this boundary.
CREATE OR REPLACE VIEW public.operator_recent_runs
WITH (security_invoker = true) AS
SELECT run_id, lane, dry_run, status, looked, started_at, completed_at, refusal
FROM operations.reaper_runs;

CREATE OR REPLACE VIEW public.operator_positions
WITH (security_invoker = true) AS
SELECT position_id, lane, subject, stake, currency, source, status, returned,
       opened_at, resolved_at, applied_to_breakers
FROM operations.positions;

CREATE OR REPLACE VIEW public.operator_alerts
WITH (security_invoker = true) AS
SELECT alert_id, lane, kind, severity, status, subject, detail, raised_at,
       acknowledged_at, resolved_at
FROM operations.alerts;

REVOKE ALL ON public.operator_recent_runs, public.operator_positions,
    public.operator_alerts FROM PUBLIC;
GRANT SELECT ON public.operator_recent_runs, public.operator_positions,
    public.operator_alerts TO anon, authenticated;

COMMIT;
