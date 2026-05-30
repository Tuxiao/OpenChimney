from __future__ import annotations

import os
import socket
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Any


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return float(value)


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return int(value)


def _list_env(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return [part.strip() for part in value.split(",") if part.strip()]


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _list_setting(value: object, default: list[str]) -> list[str]:
    if value is None:
        return list(default)
    if isinstance(value, list):
        return [str(part).strip() for part in value if str(part).strip()]
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return list(default)


def _int_setting(value: object, default: int) -> int:
    if value is None or value == "":
        return default
    return int(value)


def _float_setting(value: object, default: float) -> float:
    if value is None or value == "":
        return default
    return float(value)


@dataclass(frozen=True)
class RunnerConfig:
    api_base_url: str
    runner_key: str
    runner_id: str = field(default_factory=lambda: socket.gethostname())
    api_prefix: str = "/api/runner"
    poll_interval_seconds: float = 2.0
    empty_poll_interval_seconds: float = 5.0
    heartbeat_interval_seconds: float = 30.0
    job_heartbeat_interval_seconds: float = 10.0
    request_timeout_seconds: float = 15.0
    max_backoff_seconds: float = 60.0
    capabilities: list[str] = field(default_factory=lambda: ["ai.agent.v1", "ai.chat"])
    log_level: str = "INFO"
    agent_runtime: str = "hermes"
    hermes_model: str = "anthropic/claude-sonnet-4.6"
    hermes_provider: str | None = None
    hermes_base_url: str | None = None
    hermes_api_key: str | None = None
    hermes_home: str = "/runner/.hermes"
    hermes_workspace_root: str = "/runner/workspaces"
    hermes_max_iterations: int = 20
    hermes_default_toolsets: list[str] = field(default_factory=lambda: ["safe"])
    hermes_allowed_toolsets: list[str] = field(
        default_factory=lambda: ["safe", "web", "search", "vision", "image_gen", "mcp-sqlite-service"]
    )
    hermes_memory_mode: str = "tenant"
    hermes_timeout_seconds: float = 300.0

    @classmethod
    def from_env(cls) -> "RunnerConfig":
        api_base_url = os.getenv("RUNNER_API_BASE_URL")
        runner_key = os.getenv("RUNNER_KEY") or os.getenv("RUNNER_API_KEY")
        missing = [
            name
            for name, value in {
                "RUNNER_API_BASE_URL": api_base_url,
                "RUNNER_KEY or RUNNER_API_KEY": runner_key,
            }.items()
            if not value
        ]
        if missing:
            joined = ", ".join(missing)
            raise ValueError(f"Missing required environment variable(s): {joined}")

        return cls(
            api_base_url=api_base_url.rstrip("/"),
            runner_key=runner_key,
            runner_id=os.getenv("RUNNER_ID") or os.getenv("RUNNER_NAME") or socket.gethostname(),
            api_prefix="/" + (os.getenv("RUNNER_API_PREFIX", "/api/runner").strip("/")),
            poll_interval_seconds=_float_env("RUNNER_POLL_INTERVAL_SECONDS", 2.0),
            empty_poll_interval_seconds=_float_env("RUNNER_EMPTY_POLL_INTERVAL_SECONDS", 5.0),
            heartbeat_interval_seconds=_float_env("RUNNER_HEARTBEAT_INTERVAL_SECONDS", 30.0),
            job_heartbeat_interval_seconds=_float_env(
                "RUNNER_JOB_HEARTBEAT_INTERVAL_SECONDS",
                _float_env("RUNNER_JOB_HEARTBEAT_SECONDS", 10.0),
            ),
            request_timeout_seconds=_float_env("RUNNER_REQUEST_TIMEOUT_SECONDS", 15.0),
            max_backoff_seconds=_float_env("RUNNER_MAX_BACKOFF_SECONDS", 60.0),
            capabilities=_list_env("RUNNER_CAPABILITIES", ["ai.agent.v1", "ai.chat"]),
            log_level=os.getenv("RUNNER_LOG_LEVEL", "INFO").upper(),
            agent_runtime=os.getenv("RUNNER_AGENT_RUNTIME", "hermes").strip().lower(),
            hermes_model=os.getenv("HERMES_MODEL", "anthropic/claude-sonnet-4.6"),
            hermes_provider=_optional_text(os.getenv("HERMES_PROVIDER")),
            hermes_base_url=_optional_text(os.getenv("HERMES_BASE_URL")),
            hermes_api_key=_optional_text(os.getenv("HERMES_API_KEY")),
            hermes_home=os.getenv("HERMES_HOME", "/runner/.hermes"),
            hermes_workspace_root=os.getenv("HERMES_WORKSPACE_ROOT", "/runner/workspaces"),
            hermes_max_iterations=_int_env("HERMES_MAX_ITERATIONS", 20),
            hermes_default_toolsets=_list_env("HERMES_DEFAULT_TOOLSETS", ["safe"]),
            hermes_allowed_toolsets=_list_env(
                "HERMES_ALLOWED_TOOLSETS",
                ["safe", "web", "search", "vision", "image_gen", "mcp-sqlite-service"],
            ),
            hermes_memory_mode=os.getenv("HERMES_MEMORY_MODE", "tenant").strip().lower(),
            hermes_timeout_seconds=_float_env("HERMES_TIMEOUT_SECONDS", 300.0),
        )

    @classmethod
    def for_tests(
        cls,
        *,
        api_base_url: str = "https://api.test",
        runner_key: str = "test-runner-key",
        runner_id: str = "runner-test",
        api_prefix: str = "/api/runner",
        **overrides: object,
    ) -> "RunnerConfig":
        data = {
            "api_base_url": api_base_url.rstrip("/"),
            "runner_key": runner_key,
            "runner_id": runner_id,
            "api_prefix": "/" + api_prefix.strip("/"),
            "poll_interval_seconds": 0.01,
            "empty_poll_interval_seconds": 0.01,
            "heartbeat_interval_seconds": 999.0,
            "job_heartbeat_interval_seconds": 999.0,
            "request_timeout_seconds": 1.0,
            "max_backoff_seconds": 0.05,
            "capabilities": ["ai.agent.v1", "ai.chat"],
            "log_level": "DEBUG",
            "agent_runtime": "stub",
            "hermes_model": "anthropic/claude-sonnet-4.6",
            "hermes_provider": None,
            "hermes_base_url": None,
            "hermes_api_key": None,
            "hermes_home": "/tmp/sqlite-service-runner-hermes",
            "hermes_workspace_root": "/tmp/sqlite-service-runner-workspaces",
            "hermes_max_iterations": 20,
            "hermes_default_toolsets": ["safe"],
            "hermes_allowed_toolsets": [
                "safe",
                "web",
                "search",
                "vision",
                "image_gen",
                "mcp-sqlite-service",
            ],
            "hermes_memory_mode": "off",
            "hermes_timeout_seconds": 300.0,
        }
        data.update(overrides)
        return cls(**data)

    def with_hermes_settings(self, settings: Mapping[str, Any]) -> "RunnerConfig":
        enabled = bool(settings.get("enabled", self.agent_runtime != "stub"))
        model = _optional_text(settings.get("model")) or self.hermes_model
        task_root = _optional_text(settings.get("task_root")) or self.hermes_workspace_root
        hermes_home = _optional_text(settings.get("hermes_home")) or self.hermes_home
        memory_mode = (_optional_text(settings.get("memory_mode")) or self.hermes_memory_mode).lower()

        return replace(
            self,
            agent_runtime="hermes" if enabled else "stub",
            hermes_model=model,
            hermes_provider=_optional_text(settings.get("provider")) or self.hermes_provider,
            hermes_base_url=_optional_text(settings.get("base_url")) or self.hermes_base_url,
            hermes_api_key=_optional_text(settings.get("api_key")) or self.hermes_api_key,
            hermes_home=hermes_home,
            hermes_workspace_root=task_root,
            hermes_max_iterations=_int_setting(settings.get("max_iterations"), self.hermes_max_iterations),
            hermes_default_toolsets=_list_setting(
                settings.get("default_toolsets"),
                self.hermes_default_toolsets,
            ),
            hermes_allowed_toolsets=_list_setting(
                settings.get("allowed_toolsets"),
                self.hermes_allowed_toolsets,
            ),
            hermes_memory_mode=memory_mode,
            hermes_timeout_seconds=_float_setting(settings.get("timeout_seconds"), self.hermes_timeout_seconds),
        )
