from __future__ import annotations

from sqlalchemy import inspect, text

from app.version import PROJECT_VERSION


def test_schema_bootstrap_creates_required_tables(client):
    engine = client.app.state.engine
    tables = set(inspect(engine).get_table_names())

    assert {
        "users",
        "roles",
        "user_roles",
        "sessions",
        "members",
        "orders",
        "order_items",
        "tasks",
        "conversations",
        "messages",
        "message_attachments",
        "runner_nodes",
        "runner_jobs",
        "runner_job_events",
        "audit_logs",
        "app_settings",
    }.issubset(tables)


def test_sqlite_pragmas_are_enabled(client):
    with client.app.state.engine.connect() as connection:
        assert connection.execute(text("PRAGMA foreign_keys")).scalar() == 1
        assert connection.execute(text("PRAGMA busy_timeout")).scalar() == 5000
        assert connection.execute(text("PRAGMA journal_mode")).scalar() == "wal"


def test_health_reports_project_version(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["version"] == PROJECT_VERSION
