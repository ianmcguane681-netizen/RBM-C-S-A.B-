"""The Supabase schema exposes projections, never operational write authority."""
from pathlib import Path


SQL = Path("migrations/0002_operational_backend.sql").read_text(encoding="utf-8")


def test_every_operational_table_enables_row_security():
    tables = (
        "connector_checks", "reaper_runs", "harvests", "executions", "positions",
        "capital_snapshots", "alerts", "notification_deliveries",
    )
    for table in tables:
        assert f"ALTER TABLE operations.{table} ENABLE ROW LEVEL SECURITY;" in SQL


def test_dashboard_roles_have_no_operational_table_grants():
    assert "REVOKE ALL ON ALL TABLES IN SCHEMA operations FROM anon, authenticated;" in SQL
    assert "GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA operations TO service_role;" in SQL
    assert "GRANT INSERT" not in SQL.split("TO anon, authenticated")[0]


def test_public_views_do_not_expose_provider_payloads_or_command_actor():
    views = SQL[SQL.index("CREATE OR REPLACE VIEW public.operator_recent_runs"):]
    assert "provider_payload" not in views
    assert "requested_by" not in views
    assert "error_detail" not in views
