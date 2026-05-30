from __future__ import annotations

import argparse
import asyncio
import json
import sys

from .client import RunnerApiClient
from .config import RunnerConfig
from .logging_config import configure_logging
from .worker import RunnerWorker


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SQLite Service Kit REST task runner")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("run", help="Poll the API forever and execute jobs")
    subparsers.add_parser("once", help="Poll once and exit")
    subparsers.add_parser("config", help="Print resolved non-secret runner configuration")
    return parser


async def _run_forever(config: RunnerConfig) -> None:
    async with RunnerApiClient(config) as client:
        runtime_config = await _load_runtime_config(config, client)
        client.config = runtime_config
        worker = RunnerWorker(runtime_config, client)
        await worker.run_forever()


async def _run_once(config: RunnerConfig) -> int:
    async with RunnerApiClient(config) as client:
        runtime_config = await _load_runtime_config(config, client)
        client.config = runtime_config
        worker = RunnerWorker(runtime_config, client)
        did_work = await worker.run_once()
    return 0 if did_work else 3


async def _load_runtime_config(config: RunnerConfig, client: RunnerApiClient) -> RunnerConfig:
    hermes_config = await client.fetch_hermes_config()
    return config.with_hermes_settings(hermes_config)


def _print_config(config: RunnerConfig) -> None:
    payload = {
        "api_base_url": config.api_base_url,
        "api_prefix": config.api_prefix,
        "runner_id": config.runner_id,
        "capabilities": config.capabilities,
        "poll_interval_seconds": config.poll_interval_seconds,
        "empty_poll_interval_seconds": config.empty_poll_interval_seconds,
        "heartbeat_interval_seconds": config.heartbeat_interval_seconds,
        "job_heartbeat_interval_seconds": config.job_heartbeat_interval_seconds,
        "request_timeout_seconds": config.request_timeout_seconds,
        "max_backoff_seconds": config.max_backoff_seconds,
        "log_level": config.log_level,
        "agent_runtime": config.agent_runtime,
        "hermes_model": config.hermes_model,
        "hermes_provider": config.hermes_provider,
        "hermes_base_url": config.hermes_base_url,
        "hermes_api_key_configured": bool(config.hermes_api_key),
        "hermes_home": config.hermes_home,
        "hermes_workspace_root": config.hermes_workspace_root,
        "hermes_max_iterations": config.hermes_max_iterations,
        "hermes_default_toolsets": config.hermes_default_toolsets,
        "hermes_allowed_toolsets": config.hermes_allowed_toolsets,
        "hermes_memory_mode": config.hermes_memory_mode,
        "hermes_timeout_seconds": config.hermes_timeout_seconds,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    command = args.command or "run"

    try:
        config = RunnerConfig.from_env()
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    configure_logging(config.log_level)

    if command == "config":
        _print_config(config)
        return 0
    if command == "once":
        return asyncio.run(_run_once(config))
    if command == "run":
        try:
            asyncio.run(_run_forever(config))
        except KeyboardInterrupt:
            return 130
        return 0

    parser.error(f"Unknown command: {command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
