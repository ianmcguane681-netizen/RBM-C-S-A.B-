-- Two corrections to 0002, both of which make the database stop contradicting the code.
--
-- 1. Seven CHECK constraints spelled out ('arb', 'stocks', 'crypto'). More lanes are
--    planned, and every other place that listed the three has been reduced to one registry
--    read from `lib.reaping.LANES`. A CHECK constraint would have been the last one left,
--    and the worst placed: a lane that assembles, schedules, places and renders would fail
--    at the INSERT, after the money moved. Adding a lane is now a row in
--    operations.lanes rather than a migration.
--
-- 2. `capital_snapshots.cost_basis NUMERIC NOT NULL` and a `value_status` CHECK listing
--    only priced outcomes. `status.as_json` emits `cost_basis: null` with
--    `value_status: NOT_CONFIGURED` when no portfolio has been started, and LOST or
--    UNREADABLE when one vanished or would not parse — because a book nobody has started
--    is not a balance of zero. This schema could not store any of those states: NOT NULL
--    forces a number, and the only number available is the 0.0 that was just removed for
--    being a lie. A constraint that can only be satisfied by falsifying the value is not
--    integrity.

BEGIN;

CREATE TABLE IF NOT EXISTS operations.lanes (
    lane TEXT PRIMARY KEY,
    added_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO operations.lanes (lane) VALUES ('arb'), ('stocks'), ('crypto')
    ON CONFLICT (lane) DO NOTHING;

-- Unnamed column CHECKs take the form <table>_<column>_check. IF EXISTS so this is
-- idempotent and so a database that never had 0002's constraints is not an error.
ALTER TABLE operations.connector_checks   DROP CONSTRAINT IF EXISTS connector_checks_lane_check;
ALTER TABLE operations.reaper_runs        DROP CONSTRAINT IF EXISTS reaper_runs_lane_check;
ALTER TABLE operations.harvests           DROP CONSTRAINT IF EXISTS harvests_lane_check;
ALTER TABLE operations.executions         DROP CONSTRAINT IF EXISTS executions_lane_check;
ALTER TABLE operations.positions          DROP CONSTRAINT IF EXISTS positions_lane_check;
ALTER TABLE operations.capital_snapshots  DROP CONSTRAINT IF EXISTS capital_snapshots_lane_check;
ALTER TABLE operations.alerts             DROP CONSTRAINT IF EXISTS alerts_lane_check;

-- Referential integrity instead of a literal list. An unknown lane is still rejected;
-- what changed is that teaching the database a new one is an INSERT.
ALTER TABLE operations.connector_checks
    ADD CONSTRAINT connector_checks_lane_fkey FOREIGN KEY (lane) REFERENCES operations.lanes(lane);
ALTER TABLE operations.reaper_runs
    ADD CONSTRAINT reaper_runs_lane_fkey FOREIGN KEY (lane) REFERENCES operations.lanes(lane);
ALTER TABLE operations.harvests
    ADD CONSTRAINT harvests_lane_fkey FOREIGN KEY (lane) REFERENCES operations.lanes(lane);
ALTER TABLE operations.executions
    ADD CONSTRAINT executions_lane_fkey FOREIGN KEY (lane) REFERENCES operations.lanes(lane);
ALTER TABLE operations.positions
    ADD CONSTRAINT positions_lane_fkey FOREIGN KEY (lane) REFERENCES operations.lanes(lane);
ALTER TABLE operations.capital_snapshots
    ADD CONSTRAINT capital_snapshots_lane_fkey FOREIGN KEY (lane) REFERENCES operations.lanes(lane);
ALTER TABLE operations.alerts
    ADD CONSTRAINT alerts_lane_fkey FOREIGN KEY (lane) REFERENCES operations.lanes(lane);

-- A cost basis nobody could establish is NULL, and the status beside it says which kind of
-- nothing it was. Storing 0.0 for an absent book is the defect this repository is written
-- against, arriving through a NOT NULL constraint.
ALTER TABLE operations.capital_snapshots ALTER COLUMN cost_basis DROP NOT NULL;

ALTER TABLE operations.capital_snapshots
    DROP CONSTRAINT IF EXISTS capital_snapshots_value_status_check;
ALTER TABLE operations.capital_snapshots
    ADD CONSTRAINT capital_snapshots_value_status_check CHECK (value_status IN (
        'PRICED', 'PARTIALLY_UNPRICED', 'UNPRICED', 'EMPTY_BOOK',
        -- The three that 0002 could not represent.
        'NOT_CONFIGURED',   -- no book has been started. Not a balance of zero.
        'LOST',             -- a receipt claims entries and the store holds none.
        'UNREADABLE'        -- it exists and would not parse. Not the same as empty.
    ));

-- A figure is present or it is not, and the status must not disagree with it.
ALTER TABLE operations.capital_snapshots
    DROP CONSTRAINT IF EXISTS capital_snapshots_unknown_has_no_total;
ALTER TABLE operations.capital_snapshots
    ADD CONSTRAINT capital_snapshots_unknown_has_no_total CHECK (
        (value_status IN ('NOT_CONFIGURED', 'LOST', 'UNREADABLE')
            AND cost_basis IS NULL AND priced_value IS NULL)
        OR value_status NOT IN ('NOT_CONFIGURED', 'LOST', 'UNREADABLE')
    );

COMMIT;
