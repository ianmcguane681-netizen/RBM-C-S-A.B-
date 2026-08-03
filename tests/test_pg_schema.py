"""Postgres DDL must create referenced relations before their foreign keys."""
from tools.pg_schema import dependency_order


def test_dependency_order_puts_parent_before_alphabetically_earlier_child():
    rows = [
        ("audit_log", "CREATE TABLE audit_log (session_id TEXT REFERENCES review_sessions)"),
        ("review_sessions", "CREATE TABLE review_sessions (session_id TEXT PRIMARY KEY)"),
    ]

    assert [name for name, _ in dependency_order(rows)] == ["review_sessions", "audit_log"]


def test_dependency_order_handles_a_chain():
    rows = [
        ("links", "CREATE TABLE links (finding_id TEXT REFERENCES findings)"),
        ("findings", "CREATE TABLE findings (report_id TEXT REFERENCES reports)"),
        ("reports", "CREATE TABLE reports (id TEXT PRIMARY KEY)"),
    ]

    assert [name for name, _ in dependency_order(rows)] == ["reports", "findings", "links"]
