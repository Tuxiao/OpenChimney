from __future__ import annotations

import json

import httpx
import pytest

from app.client import RunnerApiClient
from app.config import RunnerConfig
from app.models import Job
from app.providers import ProviderRegistry
from app.worker import RunnerWorker


def test_runner_config_applies_remote_hermes_settings() -> None:
    config = RunnerConfig.for_tests(agent_runtime="stub")

    runtime_config = config.with_hermes_settings(
        {
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
        }
    )

    assert runtime_config.agent_runtime == "hermes"
    assert runtime_config.hermes_model == "openai/gpt-4.1"
    assert runtime_config.hermes_provider == "openai"
    assert runtime_config.hermes_base_url == "https://llm.example.test/v1"
    assert runtime_config.hermes_api_key == "secret-model-key"
    assert runtime_config.hermes_workspace_root == "/runner/tasks"
    assert runtime_config.hermes_home == "/runner/hermes-home"
    assert runtime_config.hermes_allowed_toolsets == ["safe", "web"]
    assert runtime_config.hermes_memory_mode == "project"


@pytest.mark.asyncio
async def test_worker_claims_chat_job_and_completes_with_assistant_message() -> None:
    events: list[tuple[str, dict[str, object]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode() or "{}")
        events.append((request.url.path, body))
        assert request.headers["X-Runner-Key"] == "test-runner-key"

        if request.url.path == "/api/runner/heartbeat":
            return httpx.Response(200, json={"ok": True})
        if request.url.path == "/api/runner/jobs/claim":
            return httpx.Response(
                200,
                json={
                    "job": {
                        "id": "job-1",
                        "type": "ai.chat",
                        "payload": {
                            "messages": [{"role": "user", "content": "Summarize this"}]
                        },
                        "attempt": 1,
                    }
                },
            )
        if request.url.path == "/api/runner/jobs/job-1/heartbeat":
            return httpx.Response(200, json={"ok": True})
        if request.url.path == "/api/runner/jobs/job-1/complete":
            return httpx.Response(200, json={"ok": True})
        raise AssertionError(f"Unexpected path {request.url.path}")

    config = RunnerConfig.for_tests()
    async with RunnerApiClient(config, transport=httpx.MockTransport(handler)) as client:
        worker = RunnerWorker(config, client)
        did_work = await worker.run_once()

    assert did_work is True
    paths = [path for path, _body in events]
    assert paths == [
        "/api/runner/heartbeat",
        "/api/runner/jobs/claim",
        "/api/runner/jobs/job-1/heartbeat",
        "/api/runner/jobs/job-1/complete",
    ]

    complete_body = events[-1][1]
    result = complete_body["result"]
    assert complete_body["runner_id"] == "runner-test"
    assert result["provider"] == "stub"
    assert result["assistant_message"]["role"] == "assistant"
    assert "Summarize this" in result["assistant_message"]["content"]


@pytest.mark.asyncio
async def test_worker_reports_provider_error_to_fail_endpoint() -> None:
    events: list[tuple[str, dict[str, object]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode() or "{}")
        events.append((request.url.path, body))
        if request.url.path == "/api/runner/jobs/bad-job/heartbeat":
            return httpx.Response(200, json={"ok": True})
        if request.url.path == "/api/runner/jobs/bad-job/fail":
            return httpx.Response(200, json={"ok": True})
        raise AssertionError(f"Unexpected path {request.url.path}")

    config = RunnerConfig.for_tests()
    job = Job(id="bad-job", type="unknown.task", payload={})
    async with RunnerApiClient(config, transport=httpx.MockTransport(handler)) as client:
        worker = RunnerWorker(config, client)
        await worker.execute_job(job)

    assert [path for path, _body in events] == [
        "/api/runner/jobs/bad-job/heartbeat",
        "/api/runner/jobs/bad-job/fail",
    ]
    error = events[-1][1]["error"]
    assert error["code"] == "unsupported_job_type"
    assert error["retryable"] is False


@pytest.mark.asyncio
async def test_worker_reports_unexpected_errors_as_retryable_failures() -> None:
    events: list[tuple[str, dict[str, object]]] = []

    class BrokenProviders:
        async def execute(self, _job: Job) -> object:
            raise RuntimeError("temporary outage")

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode() or "{}")
        events.append((request.url.path, body))
        if request.url.path == "/api/runner/jobs/job-2/heartbeat":
            return httpx.Response(200, json={"ok": True})
        if request.url.path == "/api/runner/jobs/job-2/fail":
            return httpx.Response(200, json={"ok": True})
        raise AssertionError(f"Unexpected path {request.url.path}")

    config = RunnerConfig.for_tests()
    job = Job(id="job-2", type="ai.chat", payload={})
    async with RunnerApiClient(config, transport=httpx.MockTransport(handler)) as client:
        worker = RunnerWorker(config, client, providers=BrokenProviders())
        await worker.execute_job(job)

    error = events[-1][1]["error"]
    assert error["code"] == "runner_execution_error"
    assert error["retryable"] is True
    assert error["message"] == "temporary outage"


@pytest.mark.asyncio
async def test_worker_runs_ai_agent_job_through_hermes_runtime(tmp_path) -> None:
    events: list[tuple[str, dict[str, object]]] = []
    constructed: list[dict[str, object]] = []
    calls: list[dict[str, object]] = []

    class FakeAgent:
        def __init__(self, **kwargs: object) -> None:
            constructed.append(kwargs)

        def run_conversation(self, **kwargs: object) -> dict[str, object]:
            calls.append(kwargs)
            return {
                "final_response": "Hermes researched the topic.",
                "messages": [],
                "iterations": 3,
                "usage": {"input_tokens": 10, "output_tokens": 5},
            }

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode() or "{}")
        events.append((request.url.path, body))
        if request.url.path == "/api/runner/heartbeat":
            return httpx.Response(200, json={"ok": True})
        if request.url.path == "/api/runner/jobs/claim":
            return httpx.Response(
                200,
                json={
                    "job": {
                        "id": "agent-1",
                        "type": "ai.agent.v1",
                        "payload": {
                            "runtime": "hermes",
                            "task_kind": "research.deep",
                            "instruction": "Research SQLite backup practices.",
                            "context": {"tenant_id": "tenant-a", "task_id": 42, "conversation_id": 9},
                            "messages": [
                                {"role": "user", "content": "Previous question"},
                                {"role": "assistant", "content": "Previous answer"},
                                {"role": "user", "content": "Need a research brief"},
                            ],
                            "toolsets": ["safe"],
                            "limits": {"max_iterations": 4, "timeout_seconds": 30},
                        },
                        "attempt": 1,
                    }
                },
            )
        if request.url.path == "/api/runner/jobs/agent-1/heartbeat":
            return httpx.Response(200, json={"ok": True})
        if request.url.path == "/api/runner/jobs/agent-1/complete":
            return httpx.Response(200, json={"ok": True})
        raise AssertionError(f"Unexpected path {request.url.path}")

    config = RunnerConfig.for_tests(
        agent_runtime="hermes",
        hermes_provider="openai",
        hermes_base_url="https://models.example.com/v1",
        hermes_api_key="secret-model-key",
        hermes_home=str(tmp_path / "hermes"),
        hermes_workspace_root=str(tmp_path / "workspaces"),
        hermes_memory_mode="tenant",
    )
    providers = ProviderRegistry(config, agent_factory=FakeAgent)
    async with RunnerApiClient(config, transport=httpx.MockTransport(handler)) as client:
        worker = RunnerWorker(config, client, providers=providers)
        did_work = await worker.run_once()

    assert did_work is True
    assert constructed[0]["quiet_mode"] is True
    assert constructed[0]["enabled_toolsets"] == ["safe"]
    assert constructed[0]["skip_memory"] is False
    assert constructed[0]["skip_context_files"] is False
    assert constructed[0]["max_iterations"] == 4
    assert constructed[0]["provider"] == "openai"
    assert constructed[0]["base_url"] == "https://models.example.com/v1"
    assert constructed[0]["api_key"] == "secret-model-key"
    assert constructed[0]["session_id"] == "conversation-9"
    assert constructed[0]["pass_session_id"] is True
    assert calls[0]["task_id"] == "task-42"
    assert calls[0]["conversation_history"] == [
        {"role": "user", "content": "Previous question"},
        {"role": "assistant", "content": "Previous answer"},
    ]
    assert calls[0]["persist_user_message"] == "Need a research brief"
    assert "Research SQLite backup practices" in calls[0]["user_message"]

    complete_body = events[-1][1]
    result = complete_body["result"]
    assert result["provider"] == "hermes"
    assert result["runtime"] == "hermes-agent"
    assert result["assistant_message"]["content"] == "Hermes researched the topic."
    assert result["metadata"]["task_kind"] == "research.deep"
    assert result["metadata"]["iterations"] == 3
    assert result["metadata"]["workspace_id"] == "task-42"
    assert result["metadata"]["session_id"] == "conversation-9"
    workspace = tmp_path / "workspaces" / "task-42"
    assert (workspace / ".hermes.md").exists()
    assert (workspace / "AGENTS.md").exists()
    assert (workspace / "artifacts").is_dir()
    assert (workspace / "logs").is_dir()
    assert (workspace / "tmp").is_dir()
    manifest = json.loads((workspace / "workspace.json").read_text())
    assert manifest["workspace_id"] == "task-42"
    assert manifest["session_id"] == "conversation-9"
    assert manifest["last_job_id"] == "agent-1"
    assert manifest["context"]["task_id"] == 42
    assert (tmp_path / "hermes" / "tenants" / "tenant-a").exists()


@pytest.mark.asyncio
async def test_worker_rejects_forbidden_hermes_toolset(tmp_path) -> None:
    events: list[tuple[str, dict[str, object]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode() or "{}")
        events.append((request.url.path, body))
        if request.url.path == "/api/runner/jobs/agent-bad/heartbeat":
            return httpx.Response(200, json={"ok": True})
        if request.url.path == "/api/runner/jobs/agent-bad/fail":
            return httpx.Response(200, json={"ok": True})
        raise AssertionError(f"Unexpected path {request.url.path}")

    config = RunnerConfig.for_tests(
        agent_runtime="hermes",
        hermes_home=str(tmp_path / "hermes"),
        hermes_workspace_root=str(tmp_path / "workspaces"),
    )
    job = Job(
        id="agent-bad",
        type="ai.agent.v1",
        payload={
            "instruction": "Run a command",
            "task_kind": "research.deep",
            "toolsets": ["terminal"],
        },
    )

    async with RunnerApiClient(config, transport=httpx.MockTransport(handler)) as client:
        worker = RunnerWorker(config, client)
        await worker.execute_job(job)

    error = events[-1][1]["error"]
    assert error["code"] == "invalid_agent_toolset"
    assert error["retryable"] is False
    assert error["details"]["illegal_toolsets"] == ["terminal"]


@pytest.mark.asyncio
async def test_worker_rejects_ai_agent_without_instruction(tmp_path) -> None:
    events: list[tuple[str, dict[str, object]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode() or "{}")
        events.append((request.url.path, body))
        if request.url.path == "/api/runner/jobs/agent-missing/heartbeat":
            return httpx.Response(200, json={"ok": True})
        if request.url.path == "/api/runner/jobs/agent-missing/fail":
            return httpx.Response(200, json={"ok": True})
        raise AssertionError(f"Unexpected path {request.url.path}")

    config = RunnerConfig.for_tests(
        agent_runtime="hermes",
        hermes_home=str(tmp_path / "hermes"),
        hermes_workspace_root=str(tmp_path / "workspaces"),
    )
    job = Job(id="agent-missing", type="ai.agent.v1", payload={"task_kind": "research.deep"})

    async with RunnerApiClient(config, transport=httpx.MockTransport(handler)) as client:
        worker = RunnerWorker(config, client)
        await worker.execute_job(job)

    error = events[-1][1]["error"]
    assert error["code"] == "invalid_agent_payload"
    assert error["retryable"] is False
