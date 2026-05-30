from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Job:
    id: str
    type: str
    payload: dict[str, Any] = field(default_factory=dict)
    attempt: int | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "Job":
        job_id = data.get("id") or data.get("job_id") or data.get("task_id")
        job_type = data.get("type") or data.get("job_type") or data.get("task_type")
        if not job_id:
            raise ValueError("Claimed job payload is missing id/job_id/task_id")
        if not job_type:
            raise ValueError("Claimed job payload is missing type/job_type/task_type")

        payload = data.get("payload") or {}
        if not isinstance(payload, dict):
            raise ValueError("Claimed job payload must be an object")

        attempt = data.get("attempt")
        if attempt is not None:
            attempt = int(attempt)

        return cls(id=str(job_id), type=str(job_type), payload=payload, attempt=attempt)


@dataclass(frozen=True)
class JobResult:
    output: dict[str, Any]


@dataclass(frozen=True)
class FailurePayload:
    code: str
    message: str
    retryable: bool = True
    details: dict[str, Any] = field(default_factory=dict)

    def to_api(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
            "details": self.details,
        }
