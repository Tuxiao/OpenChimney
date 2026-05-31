from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest
from fastapi.testclient import TestClient

from app.config import AppConfig
from app.main import create_app


@pytest.fixture()
def client(tmp_path: Path) -> Iterator[TestClient]:
    db_path = tmp_path / "api.sqlite3"
    app = create_app(
        AppConfig(
            database_url=f"sqlite:///{db_path}",
            runner_key="test-runner-key",
            default_admin_email="admin@example.com",
            default_admin_password="admin1234",
            super_admin_email="superadmin@example.com",
            super_admin_password="superadmin1234",
        )
    )
    with TestClient(app) as test_client:
        yield test_client


def register_user(client: TestClient, email: str = "user@example.com") -> str:
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": "password123", "display_name": "Test User"},
    )
    assert response.status_code == 201, response.text
    return response.json()["token"]["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def runner_headers() -> dict[str, str]:
    return {"X-Runner-Key": "test-runner-key"}
