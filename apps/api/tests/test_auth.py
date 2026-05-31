from __future__ import annotations

from .conftest import auth_headers


def test_register_me_logout_flow(client):
    response = client.post(
        "/api/auth/register",
        json={"email": "new@example.com", "password": "password123", "display_name": "New"},
    )
    assert response.status_code == 201, response.text
    token = response.json()["token"]["access_token"]

    me = client.get("/api/auth/me", headers=auth_headers(token))
    assert me.status_code == 200
    assert me.json()["email"] == "new@example.com"
    assert [role["name"] for role in me.json()["roles"]] == ["user"]

    logout = client.post("/api/auth/logout", headers=auth_headers(token))
    assert logout.status_code == 204

    after_logout = client.get("/api/auth/me", headers=auth_headers(token))
    assert after_logout.status_code == 401


def test_seeded_default_admin_email_is_not_super_admin(client):
    login = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "admin1234"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["token"]["access_token"]
    assert [role["name"] for role in login.json()["user"]["roles"]] == ["user"]

    overview = client.get("/api/admin/overview", headers=auth_headers(token))
    assert overview.status_code == 403


def test_seeded_super_admin_can_access_overview(client):
    login = client.post(
        "/api/auth/login",
        json={"email": "superadmin@example.com", "password": "superadmin1234"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["token"]["access_token"]
    assert {role["name"] for role in login.json()["user"]["roles"]} == {
        "user",
        "super_admin",
    }

    overview = client.get("/api/admin/overview", headers=auth_headers(token))
    assert overview.status_code == 200
    assert overview.json()["users"] >= 1


def test_phone_sms_login_auto_registers_and_sets_password(client):
    code_response = client.post("/api/auth/phone/request-code", json={"phone": "+1 (555) 123-4567"})
    assert code_response.status_code == 200, code_response.text
    payload = code_response.json()
    assert payload["phone"] == "+15551234567"
    assert len(payload["dev_code"]) == 6

    login = client.post(
        "/api/auth/phone/verify-code",
        json={"phone": "+1 (555) 123-4567", "code": payload["dev_code"]},
    )
    assert login.status_code == 200, login.text
    body = login.json()
    assert body["is_new_user"] is True
    assert body["requires_password_setup"] is True
    assert body["user"]["phone"] == "+15551234567"
    token = body["token"]["access_token"]

    set_password = client.post(
        "/api/auth/set-password",
        headers=auth_headers(token),
        json={"password": "password123"},
    )
    assert set_password.status_code == 200, set_password.text
    assert set_password.json()["has_password"] is True
    assert set_password.json()["requires_password_setup"] is False

    password_login = client.post(
        "/api/auth/phone/login",
        json={"phone": "+15551234567", "password": "password123"},
    )
    assert password_login.status_code == 200, password_login.text
    assert password_login.json()["requires_password_setup"] is False


def test_phone_password_login_rejects_sms_only_account(client):
    code_response = client.post("/api/auth/phone/request-code", json={"phone": "+86 138 0000 0000"})
    code = code_response.json()["dev_code"]
    login = client.post(
        "/api/auth/phone/verify-code",
        json={"phone": "+8613800000000", "code": code},
    )
    assert login.status_code == 200

    password_login = client.post(
        "/api/auth/phone/login",
        json={"phone": "+8613800000000", "password": "password123"},
    )
    assert password_login.status_code == 401
