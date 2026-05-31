from __future__ import annotations

from typing import Any

import httpx

from .config import RunnerConfig
from .models import FailurePayload, Job, JobResult


class RunnerApiError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class RunnerApiClient:
    def __init__(
        self,
        config: RunnerConfig,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.config = config
        self._client = httpx.AsyncClient(
            base_url=config.api_base_url,
            timeout=config.request_timeout_seconds,
            trust_env=False,
            headers={
                "X-Runner-Key": config.runner_key,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            transport=transport,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "RunnerApiClient":
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    async def send_runner_heartbeat(self, *, status: str = "idle") -> None:
        await self._post(
            "/heartbeat",
            json={
                "runner_id": self.config.runner_id,
                "version": self.config.version,
                "status": status,
                "capabilities": self.config.capabilities,
            },
        )

    async def fetch_hermes_config(self) -> dict[str, Any]:
        response = await self._post(
            "/config/hermes",
            json={"runner_id": self.config.runner_id},
        )
        data = self._json(response)
        if not isinstance(data, dict):
            raise RunnerApiError("Hermes config response must be an object")
        return data

    async def claim_job(self) -> Job | None:
        response = await self._post(
            "/jobs/claim",
            json={
                "runner_id": self.config.runner_id,
                "capabilities": self.config.capabilities,
            },
        )
        if response.status_code == 204 or not response.content:
            return None

        data = self._json(response)
        if data is None:
            return None
        if isinstance(data, dict) and data.get("job") is None and "job" in data:
            return None
        if isinstance(data, dict) and "job" in data:
            data = data["job"]
        if not isinstance(data, dict):
            raise RunnerApiError("Claim response must be an object or null")
        return Job.from_api(data)

    async def renew_job_heartbeat(self, job_id: str) -> None:
        await self._post(
            f"/jobs/{job_id}/heartbeat",
            json={"runner_id": self.config.runner_id},
        )

    async def report_job_event(
        self,
        job_id: str,
        event_type: str,
        *,
        message: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> None:
        await self._post(
            f"/jobs/{job_id}/events",
            json={
                "runner_id": self.config.runner_id,
                "event_type": event_type,
                "message": message,
                "data_json": data or {},
            },
        )

    async def complete_job(self, job_id: str, result: JobResult) -> None:
        await self._post(
            f"/jobs/{job_id}/complete",
            json={"runner_id": self.config.runner_id, "result": result.output},
        )

    async def fail_job(self, job_id: str, failure: FailurePayload) -> None:
        await self._post(
            f"/jobs/{job_id}/fail",
            json={"runner_id": self.config.runner_id, "error": failure.to_api()},
        )

    async def _post(self, path: str, *, json: dict[str, Any]) -> httpx.Response:
        url = f"{self.config.api_prefix}{path}"
        try:
            response = await self._client.post(url, json=json)
        except httpx.HTTPError as exc:
            raise RunnerApiError(f"API request failed: {exc}") from exc

        if response.status_code >= 400:
            raise RunnerApiError(
                f"API request failed with HTTP {response.status_code}",
                status_code=response.status_code,
            )
        return response

    @staticmethod
    def _json(response: httpx.Response) -> object:
        try:
            return response.json()
        except ValueError as exc:
            raise RunnerApiError("API response was not valid JSON") from exc
