from __future__ import annotations

from .conftest import auth_headers, register_user, runner_headers


def create_task_with_runner_job(client, token: str) -> int:
    task = client.post(
        "/api/tasks",
        headers=auth_headers(token),
        json={"title": "Draft reply", "description": "Use runner"},
    )
    assert task.status_code == 201, task.text
    task_id = task.json()["id"]

    message = client.post(
        f"/api/tasks/{task_id}/messages",
        headers=auth_headers(token),
        json={"content": "Please process this task."},
    )
    assert message.status_code == 201, message.text
    return message.json()["runner_job_id"]


def claim_one(client, node_key: str = "node-a"):
    response = client.post(
        "/api/runner/claim",
        headers=runner_headers(),
        json={"node_key": node_key, "limit": 1},
    )
    assert response.status_code == 200, response.text
    jobs = response.json()
    assert len(jobs) == 1
    return jobs[0]


def test_runner_claim_and_complete(client):
    token = register_user(client)
    job_id = create_task_with_runner_job(client, token)

    heartbeat = client.post(
        "/api/runner/heartbeat",
        headers=runner_headers(),
        json={"node_key": "node-a", "display_name": "Node A", "version": "test"},
    )
    assert heartbeat.status_code == 200, heartbeat.text

    claimed = claim_one(client)
    assert claimed["id"] == job_id
    assert claimed["status"] == "running"
    assert claimed["attempts"] == 1

    completed = client.post(
        f"/api/runner/jobs/{job_id}/complete",
        headers=runner_headers(),
        json={"result_json": {"ok": True}},
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "succeeded"


def test_runner_wire_format_claim_and_complete_writes_assistant_message(client):
    token = register_user(client, "wire@example.com")
    job_id = create_task_with_runner_job(client, token)

    claimed = client.post(
        "/api/runner/jobs/claim",
        headers=runner_headers(),
        json={"runner_id": "wire-runner", "capabilities": ["ai.agent.v1", "ai.chat"]},
    )
    assert claimed.status_code == 200, claimed.text
    job = claimed.json()["job"]
    assert job["id"] == job_id
    assert job["type"] == "ai.agent.v1"
    assert job["payload"]["runtime"] == "hermes"
    assert job["payload"]["task_kind"] == "ai.chat"
    assert job["payload"]["workspace_id"] == f"task-{job['payload']['task_id']}"
    assert job["payload"]["session_id"] == f"conversation-{job['payload']['conversation_id']}"
    assert job["payload"]["resume"] is True
    assert job["payload"]["context"]["conversation_id"] is not None
    assert job["payload"]["messages"][-1]["content"] == "Please process this task."

    completed = client.post(
        f"/api/runner/jobs/{job_id}/complete",
        headers=runner_headers(),
        json={
            "runner_id": "wire-runner",
            "result": {
                "provider": "stub",
                "model": "stub-ai-chat",
                "assistant_message": {
                    "role": "assistant",
                    "content": "Stub assistant response.",
                },
            },
        },
    )
    assert completed.status_code == 200, completed.text

    conversations = client.get("/api/conversations", headers=auth_headers(token))
    assert conversations.status_code == 200, conversations.text
    messages = conversations.json()[0]["messages"]
    assert messages[-1]["role"] == "assistant"
    assert messages[-1]["content"] == "Stub assistant response."


def test_runner_fail_retries_until_final_failure(client):
    token = register_user(client, "retry@example.com")
    job_id = create_task_with_runner_job(client, token)

    first = claim_one(client, "node-retry")
    assert first["id"] == job_id

    retry = client.post(
        f"/api/runner/jobs/{job_id}/fail",
        headers=runner_headers(),
        json={"error_message": "temporary", "retry_after_seconds": 0},
    )
    assert retry.status_code == 200, retry.text
    assert retry.json()["status"] == "queued"
    assert retry.json()["attempts"] == 1

    second = claim_one(client, "node-retry")
    assert second["attempts"] == 2
    retry_again = client.post(
        f"/api/runner/jobs/{job_id}/fail",
        headers=runner_headers(),
        json={"error_message": "still temporary", "retry_after_seconds": 0},
    )
    assert retry_again.status_code == 200, retry_again.text
    assert retry_again.json()["status"] == "queued"

    third = claim_one(client, "node-retry")
    assert third["attempts"] == 3
    final = client.post(
        f"/api/runner/jobs/{job_id}/fail",
        headers=runner_headers(),
        json={"error_message": "permanent", "retry_after_seconds": 0},
    )
    assert final.status_code == 200, final.text
    assert final.json()["status"] == "failed"
    assert final.json()["attempts"] == 3


def test_runner_key_is_required(client):
    response = client.post("/api/runner/claim", json={"node_key": "node-a", "limit": 1})
    assert response.status_code == 401


def test_admin_can_save_hermes_config_and_runner_can_read_secret(client):
    login = client.post(
        "/api/auth/login",
        json={"email": "superadmin@example.com", "password": "superadmin1234"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["token"]["access_token"]

    current = client.get("/api/admin/hermes-config", headers=auth_headers(token))
    assert current.status_code == 200, current.text
    assert current.json()["model"] == "anthropic/claude-sonnet-4.6"
    assert current.json()["api_key_configured"] is False
    assert "api_key" not in current.json()

    saved = client.put(
        "/api/admin/hermes-config",
        headers=auth_headers(token),
        json={
            "enabled": True,
            "model": "openai/gpt-4.1",
            "provider": "openai",
            "base_url": "https://llm.example.test/v1",
            "api_key": "secret-model-key",
            "task_root": "/runner/tasks",
            "hermes_home": "/runner/hermes-home",
            "max_iterations": 12,
            "default_toolsets": ["safe"],
            "allowed_toolsets": ["safe", "web"],
            "memory_mode": "project",
            "timeout_seconds": 180,
        },
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["api_key_configured"] is True
    assert "api_key" not in saved.json()

    runner_config = client.post(
        "/api/runner/config/hermes",
        headers=runner_headers(),
        json={"runner_id": "runner-a"},
    )
    assert runner_config.status_code == 200, runner_config.text
    payload = runner_config.json()
    assert payload["model"] == "openai/gpt-4.1"
    assert payload["provider"] == "openai"
    assert payload["base_url"] == "https://llm.example.test/v1"
    assert payload["api_key"] == "secret-model-key"
    assert payload["task_root"] == "/runner/tasks"


def test_admin_can_save_hermes_config_and_runner_can_read_secret(client):
    login = client.post(
        "/api/auth/login",
        json={"email": "superadmin@example.com", "password": "superadmin1234"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["token"]["access_token"]

    current = client.get("/api/admin/hermes-config", headers=auth_headers(token))
    assert current.status_code == 200, current.text
    assert current.json()["model"] == "anthropic/claude-sonnet-4.6"
    assert current.json()["api_key_configured"] is False
    assert "api_key" not in current.json()

    update = client.put(
        "/api/admin/hermes-config",
        headers=auth_headers(token),
        json={
            "enabled": True,
            "model": "openai/gpt-4.1",
            "provider": "openai",
            "base_url": "https://models.example.com/v1",
            "api_key": "secret-model-key",
            "task_root": "/runner/jobs",
            "hermes_home": "/runner/hermes-home",
            "max_iterations": 12,
            "default_toolsets": ["safe", "web"],
            "allowed_toolsets": ["safe", "web"],
            "memory_mode": "project",
            "timeout_seconds": 180,
        },
    )
    assert update.status_code == 200, update.text
    public_config = update.json()
    assert public_config["api_key_configured"] is True
    assert "api_key" not in public_config
    assert public_config["task_root"] == "/runner/jobs"

    runner_config = client.post(
        "/api/runner/config/hermes",
        headers=runner_headers(),
        json={"runner_id": "runner-config-test"},
    )
    assert runner_config.status_code == 200, runner_config.text
    runner_body = runner_config.json()
    assert runner_body["model"] == "openai/gpt-4.1"
    assert runner_body["provider"] == "openai"
    assert runner_body["base_url"] == "https://models.example.com/v1"
    assert runner_body["api_key"] == "secret-model-key"
    assert runner_body["task_root"] == "/runner/jobs"
