from __future__ import annotations

import asyncio
import logging
import random
import time
from collections.abc import Callable
from typing import Any

from .client import RunnerApiClient
from .config import RunnerConfig
from .models import FailurePayload, Job
from .providers import ProviderError, ProviderRegistry

logger = logging.getLogger(__name__)


class RunnerWorker:
    def __init__(
        self,
        config: RunnerConfig,
        client: RunnerApiClient,
        providers: ProviderRegistry | None = None,
        *,
        sleep: Callable[[float], object] | None = None,
    ) -> None:
        self.config = config
        self.client = client
        self.providers = providers or ProviderRegistry(config)
        self._sleep = sleep or asyncio.sleep
        self._last_runner_heartbeat = 0.0

    async def run_forever(self) -> None:
        failures = 0
        logger.info(
            "runner starting",
            extra={
                "_json_runner_id": self.config.runner_id,
                "_json_api_base_url": self.config.api_base_url,
                "_json_capabilities": self.config.capabilities,
            },
        )
        while True:
            try:
                did_work = await self.run_once()
                failures = 0
                delay = (
                    self.config.poll_interval_seconds
                    if did_work
                    else self.config.empty_poll_interval_seconds
                )
                await self._maybe_await_sleep(delay)
            except asyncio.CancelledError:
                logger.info("runner stopping", extra={"_json_runner_id": self.config.runner_id})
                raise
            except Exception:
                failures += 1
                delay = self._backoff_delay(failures)
                logger.exception(
                    "runner loop error",
                    extra={
                        "_json_runner_id": self.config.runner_id,
                        "_json_backoff_seconds": delay,
                    },
                )
                await self._maybe_await_sleep(delay)

    async def run_once(self) -> bool:
        await self._send_runner_heartbeat_if_due("idle")
        job = await self.client.claim_job()
        if job is None:
            logger.debug("no job available", extra={"_json_runner_id": self.config.runner_id})
            return False

        await self.execute_job(job)
        return True

    async def execute_job(self, job: Job) -> None:
        logger.info(
            "job claimed",
            extra={
                "_json_runner_id": self.config.runner_id,
                "_json_job_id": job.id,
                "_json_job_type": job.type,
                "_json_attempt": job.attempt,
            },
        )
        heartbeat_task = asyncio.create_task(self._renew_job_heartbeat_until_done(job.id))
        event_tasks: set[asyncio.Task[None]] = set()
        loop = asyncio.get_running_loop()

        def submit_event(event_type: str, message: str | None = None, data: dict[str, Any] | None = None) -> None:
            def create_task() -> None:
                task = asyncio.create_task(
                    self.client.report_job_event(
                        job.id,
                        event_type,
                        message=message,
                        data={"runner_id": self.config.runner_id, **(data or {})},
                    )
                )
                event_tasks.add(task)
                task.add_done_callback(event_tasks.discard)

            loop.call_soon_threadsafe(create_task)

        async def flush_event_tasks() -> None:
            await asyncio.sleep(0)
            if event_tasks:
                await asyncio.gather(*list(event_tasks), return_exceptions=True)

        try:
            await self.client.renew_job_heartbeat(job.id)
            await self.client.report_job_event(
                job.id,
                "runner.started",
                message="Runner started job",
                data={"runner_id": self.config.runner_id, "attempt": job.attempt, "job_type": job.type},
            )
            result = await self.providers.execute(job, event_sink=submit_event)
            await flush_event_tasks()
            await self.client.complete_job(job.id, result)
            logger.info(
                "job completed",
                extra={"_json_runner_id": self.config.runner_id, "_json_job_id": job.id},
            )
        except ProviderError as exc:
            submit_event(
                "runner.failed",
                str(exc),
                {"code": exc.code, "retryable": exc.retryable},
            )
            await flush_event_tasks()
            await self.client.fail_job(job.id, exc.to_failure())
            logger.warning(
                "job failed in provider",
                extra={
                    "_json_runner_id": self.config.runner_id,
                    "_json_job_id": job.id,
                    "_json_error_code": exc.code,
                    "_json_retryable": exc.retryable,
                },
            )
        except Exception as exc:
            failure = FailurePayload(
                code="runner_execution_error",
                message=str(exc) or exc.__class__.__name__,
                retryable=True,
                details={"exception_type": exc.__class__.__name__},
            )
            submit_event(
                "runner.failed",
                failure.message,
                {"code": failure.code, "retryable": failure.retryable},
            )
            await flush_event_tasks()
            try:
                await self.client.fail_job(job.id, failure)
            except Exception:
                logger.exception(
                    "failed to report job failure",
                    extra={"_json_runner_id": self.config.runner_id, "_json_job_id": job.id},
                )
                raise
            logger.exception(
                "job failed with retryable runner error",
                extra={"_json_runner_id": self.config.runner_id, "_json_job_id": job.id},
            )
        finally:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

    async def _send_runner_heartbeat_if_due(self, status: str) -> None:
        now = time.monotonic()
        if now - self._last_runner_heartbeat < self.config.heartbeat_interval_seconds:
            return
        await self.client.send_runner_heartbeat(status=status)
        self._last_runner_heartbeat = now
        logger.debug(
            "runner heartbeat sent",
            extra={"_json_runner_id": self.config.runner_id, "_json_status": status},
        )

    async def _renew_job_heartbeat_until_done(self, job_id: str) -> None:
        while True:
            await self._maybe_await_sleep(self.config.job_heartbeat_interval_seconds)
            try:
                await self.client.renew_job_heartbeat(job_id)
                logger.debug(
                    "job heartbeat renewed",
                    extra={"_json_runner_id": self.config.runner_id, "_json_job_id": job_id},
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception(
                    "job heartbeat renewal failed",
                    extra={"_json_runner_id": self.config.runner_id, "_json_job_id": job_id},
                )

    def _backoff_delay(self, failures: int) -> float:
        capped = min(self.config.max_backoff_seconds, 2 ** min(failures, 8))
        return min(self.config.max_backoff_seconds, capped + random.uniform(0, 0.25))

    async def _maybe_await_sleep(self, seconds: float) -> None:
        result = self._sleep(seconds)
        if hasattr(result, "__await__"):
            await result
