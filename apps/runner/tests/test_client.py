from __future__ import annotations

import json

import httpx
import pytest

from app.client import RunnerApiClient
from app.config import RunnerConfig


def test_runner_config_applies_database_hermes_settings() -> None:
    config = RunnerConfig.for_tests(agent_runtime="stub")

    runtime_config = config.with_hermes_settings(
        {
            "enabled": True,
            "model": "openai/gpt-4.1",
            "provider": "openai",
            "base_url": "https://models.example.com/v1",
            "api_key": "secret",
            "task_root": "/runner/jobs",
            "hermes_home": "/runner/hermes",
            "max_iterations": 10,
            "default_toolsets": ["safe", "web"],
            "allowed_toolsets": ["safe", "web"],
            "memory_mode": "project",
            "timeout_seconds": 120,
        }
    )

    assert runtime_config.agent_runtime == "hermes"
    assert runtime_config.hermes_model == "openai/gpt-4.1"
    assert runtime_config.hermes_provider == "openai"
    assert runtime_config.hermes_base_url == "https://models.example.com/v1"
    assert runtime_config.hermes_api_key == "secret"
    assert runtime_config.hermes_workspace_root == "/runner/jobs"
    assert runtime_config.hermes_home == "/runner/hermes"
    assert runtime_config.hermes_default_toolsets == ["safe", "web"]
    assert runtime_config.hermes_memory_mode == "project"
    assert runtime_config.hermes_timeout_seconds == 120


@pytest.mark.asyncio
async def test_client_uses_runner_key_and_configured_prefix() -> None:
    seen: list[tuple[str, str, dict[str, object]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode() or "{}")
        seen.append((request.method, request.url.path, body))
        assert request.headers["X-Runner-Key"] == "secret"
        return httpx.Response(200, json={"job": None})

    config = RunnerConfig.for_tests(runner_key="secret", api_prefix="/internal/runner")
    async with RunnerApiClient(config, transport=httpx.MockTransport(handler)) as client:
        job = await client.claim_job()

    assert job is None
    assert seen == [
        (
            "POST",
            "/internal/runner/jobs/claim",
            {"runner_id": "runner-test", "capabilities": ["ai.agent.v1", "ai.chat"]},
        )
    ]


@pytest.mark.asyncio
async def test_client_claims_direct_or_wrapped_job_payload() -> None:
    responses = [
        {"id": "job-a", "type": "ai.chat", "payload": {"prompt": "hello"}},
        {"job": {"job_id": "job-b", "job_type": "ai.chat", "payload": {}}},
    ]

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=responses.pop(0))

    config = RunnerConfig.for_tests()
    async with RunnerApiClient(config, transport=httpx.MockTransport(handler)) as client:
        first = await client.claim_job()
        second = await client.claim_job()

    assert first is not None
    assert first.id == "job-a"
    assert first.payload == {"prompt": "hello"}
    assert second is not None
    assert second.id == "job-b"


@pytest.mark.asyncio
async def test_client_fetches_hermes_config() -> None:
    seen: list[tuple[str, dict[str, object]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode() or "{}")
        seen.append((request.url.path, body))
        return httpx.Response(
            200,
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

    config = RunnerConfig.for_tests()
    async with RunnerApiClient(config, transport=httpx.MockTransport(handler)) as client:
        hermes_config = await client.fetch_hermes_config()

    assert hermes_config["api_key"] == "secret-model-key"
    assert seen == [("/api/runner/config/hermes", {"runner_id": "runner-test"})]


@pytest.mark.asyncio
async def test_client_fetches_hermes_config() -> None:
    seen: list[tuple[str, dict[str, object]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode() or "{}")
        seen.append((request.url.path, body))
        return httpx.Response(
            200,
            json={
                "enabled": True,
                "model": "openai/gpt-4.1",
                "provider": "openai",
                "base_url": "https://models.example.com/v1",
                "api_key": "secret",
                "task_root": "/runner/jobs",
                "hermes_home": "/runner/hermes",
                "max_iterations": 10,
                "default_toolsets": ["safe"],
                "allowed_toolsets": ["safe"],
                "memory_mode": "project",
                "timeout_seconds": 120,
            },
        )

    config = RunnerConfig.for_tests()
    async with RunnerApiClient(config, transport=httpx.MockTransport(handler)) as client:
        hermes_config = await client.fetch_hermes_config()

    assert seen == [("/api/runner/config/hermes", {"runner_id": "runner-test"})]
    assert hermes_config["model"] == "openai/gpt-4.1"
    assert hermes_config["api_key"] == "secret"


@pytest.mark.asyncio
async def test_client_reports_job_event() -> None:
    seen: list[tuple[str, dict[str, object]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.url.path, json.loads(request.content.decode() or "{}")))
        assert request.headers["X-Runner-Key"] == "secret"
        return httpx.Response(201, json={"ok": True})

    config = RunnerConfig.for_tests(runner_key="secret")
    async with RunnerApiClient(config, transport=httpx.MockTransport(handler)) as client:
        await client.report_job_event(
            "42",
            "hermes.thinking",
            message="Thinking",
            data={"phase": "model"},
        )

    assert seen == [
        (
            "/api/runner/jobs/42/events",
            {
                "runner_id": "runner-test",
                "event_type": "hermes.thinking",
                "message": "Thinking",
                "data_json": {"phase": "model"},
            },
        )
    ]
