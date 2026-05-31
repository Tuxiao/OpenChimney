from __future__ import annotations

import base64
import binascii
import mimetypes
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require_runner_key
from ..hermes_settings import ensure_hermes_setting, merged_hermes_config, runner_hermes_config
from ..models import Message, MessageAttachment, RunnerJob, RunnerJobEvent, RunnerNode
from ..schemas import (
    HermesRunnerConfigOut,
    RunnerClaimIn,
    RunnerCompleteIn,
    RunnerFailIn,
    RunnerJobEventIn,
    RunnerJobOut,
    RunnerNodeIn,
    RunnerNodeOut,
)

router = APIRouter(prefix="/api/runner", tags=["runner"])


def now() -> datetime:
    return datetime.utcnow()


def get_or_create_node(db: Session, node_key: str) -> RunnerNode:
    node = db.query(RunnerNode).filter(RunnerNode.node_key == node_key).one_or_none()
    if node is None:
        node = RunnerNode(node_key=node_key, status="online")
        db.add(node)
        db.flush()
    return node


def normalize_capabilities(capabilities: Any) -> dict[str, Any]:
    if isinstance(capabilities, dict):
        return capabilities
    if isinstance(capabilities, list):
        return {"items": capabilities}
    if capabilities is None:
        return {}
    return {"value": capabilities}


def add_job_event(
    db: Session,
    job: RunnerJob,
    event_type: str,
    message: Optional[str] = None,
    data_json: Optional[dict] = None,
) -> None:
    db.add(
        RunnerJobEvent(
            runner_job_id=job.id,
            event_type=event_type,
            message=message,
            data_json=data_json or {},
        )
    )


@router.post("/config/hermes", response_model=HermesRunnerConfigOut)
def hermes_config(
    db: Annotated[Session, Depends(get_db)],
    _runner_key: Annotated[None, Depends(require_runner_key)],
) -> dict[str, Any]:
    setting = ensure_hermes_setting(db)
    db.commit()
    db.refresh(setting)
    config = merged_hermes_config(setting.value_json)
    return runner_hermes_config(config, setting.updated_at)


@router.post("/heartbeat", response_model=RunnerNodeOut)
def heartbeat(
    payload: RunnerNodeIn,
    db: Annotated[Session, Depends(get_db)],
    _runner_key: Annotated[None, Depends(require_runner_key)],
) -> RunnerNode:
    node = get_or_create_node(db, payload.node_key)
    node.display_name = payload.display_name
    node.version = payload.version
    node.capabilities = normalize_capabilities(payload.capabilities)
    node.last_heartbeat_at = now()
    node.status = "online"
    db.commit()
    db.refresh(node)
    return node


@router.post("/claim", response_model=list[RunnerJobOut])
def claim(
    payload: RunnerClaimIn,
    db: Annotated[Session, Depends(get_db)],
    _runner_key: Annotated[None, Depends(require_runner_key)],
) -> list[RunnerJob]:
    return claim_jobs(db, payload)


@router.post("/jobs/claim")
def claim_next_job(
    payload: RunnerClaimIn,
    db: Annotated[Session, Depends(get_db)],
    _runner_key: Annotated[None, Depends(require_runner_key)],
) -> dict[str, Any]:
    payload.limit = 1
    jobs = claim_jobs(db, payload)
    return {"job": runner_job_payload(jobs[0]) if jobs else None}


def claim_jobs(db: Session, payload: RunnerClaimIn) -> list[RunnerJob]:
    db.execute(text("BEGIN IMMEDIATE"))
    node = get_or_create_node(db, payload.node_key)
    node.last_heartbeat_at = now()
    node.status = "online"
    node.capabilities = normalize_capabilities(payload.capabilities)
    jobs = (
        db.query(RunnerJob)
        .filter(
            RunnerJob.status == "queued",
            RunnerJob.next_run_at <= now(),
            RunnerJob.attempts < RunnerJob.max_attempts,
        )
        .order_by(RunnerJob.priority.asc(), RunnerJob.created_at.asc())
        .limit(payload.limit)
        .all()
    )
    for job in jobs:
        job.status = "running"
        job.runner_node_id = node.id
        job.attempts += 1
        job.claimed_at = now()
        job.heartbeat_at = job.claimed_at
        job.error_message = None
        add_job_event(db, job, "claimed", data_json={"node_key": payload.node_key})
    db.commit()
    for job in jobs:
        db.refresh(job)
    return jobs


def runner_job_payload(job: RunnerJob) -> dict[str, Any]:
    return {
        "id": job.id,
        "type": job.job_type,
        "payload": job.payload_json,
        "attempt": job.attempts,
        "status": job.status,
    }


@router.post("/jobs/{job_id}/heartbeat", response_model=RunnerJobOut)
def job_heartbeat(
    job_id: int,
    db: Annotated[Session, Depends(get_db)],
    _runner_key: Annotated[None, Depends(require_runner_key)],
) -> RunnerJob:
    job = db.get(RunnerJob, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Runner job not found")
    if job.status != "running":
        raise HTTPException(status.HTTP_409_CONFLICT, "Runner job is not running")
    job.heartbeat_at = now()
    add_job_event(db, job, "heartbeat")
    db.commit()
    db.refresh(job)
    return job


@router.post("/jobs/{job_id}/events", status_code=status.HTTP_201_CREATED)
def append_job_event(
    job_id: int,
    payload: RunnerJobEventIn,
    db: Annotated[Session, Depends(get_db)],
    _runner_key: Annotated[None, Depends(require_runner_key)],
) -> dict[str, Any]:
    job = db.get(RunnerJob, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Runner job not found")
    add_job_event(
        db,
        job,
        payload.event_type,
        message=payload.message,
        data_json=payload.data_json,
    )
    db.commit()
    return {"ok": True}


@router.post("/jobs/{job_id}/complete", response_model=RunnerJobOut)
def complete_job(
    job_id: int,
    payload: RunnerCompleteIn,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    _runner_key: Annotated[None, Depends(require_runner_key)],
) -> RunnerJob:
    job = db.get(RunnerJob, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Runner job not found")
    if job.status != "running":
        raise HTTPException(status.HTTP_409_CONFLICT, "Runner job is not running")
    job.status = "succeeded"
    job.result_json = payload.result_json
    job.completed_at = now()
    job.heartbeat_at = job.completed_at
    assistant_message = payload.result_json.get("assistant_message")
    context = job.payload_json.get("context")
    conversation_id = job.payload_json.get("conversation_id")
    if conversation_id is None and isinstance(context, dict):
        conversation_id = context.get("conversation_id")
    if (
        isinstance(assistant_message, dict)
        and conversation_id is not None
        and isinstance(assistant_message.get("content"), str)
    ):
        message = Message(
            conversation_id=int(conversation_id),
            role=str(assistant_message.get("role") or "assistant"),
            content=assistant_message["content"],
            metadata_json={
                "runner_job_id": job.id,
                "provider": payload.result_json.get("provider"),
                "model": payload.result_json.get("model"),
                "usage": payload.result_json.get("usage"),
            },
        )
        db.add(message)
        db.flush()
        for artifact in _decode_artifacts(payload.result_json.get("artifacts")):
            _store_message_artifact(request, db, message, artifact)
    if job.task is not None:
        job.task.status = "completed"
    add_job_event(db, job, "completed", data_json=payload.result_json)
    db.commit()
    db.refresh(job)
    return job


def _decode_artifacts(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []

    artifacts: list[dict[str, object]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        encoded = item.get("data_base64")
        if not isinstance(encoded, str) or not encoded:
            continue
        try:
            data = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError):
            continue
        content_type = item.get("content_type")
        artifacts.append(
            {
                "file_name": _safe_file_name(item.get("file_name") or item.get("name") or "artifact.bin"),
                "content_type": str(content_type).strip() if content_type else None,
                "data": data,
            }
        )
    return artifacts


def _store_message_artifact(
    request: Request,
    db: Session,
    message: Message,
    artifact: dict[str, object],
) -> MessageAttachment:
    file_name = str(artifact["file_name"])
    data = artifact["data"]
    if not isinstance(data, bytes):
        raise TypeError("artifact data must be bytes")
    content_type = artifact.get("content_type") or mimetypes.guess_type(file_name)[0]

    attachment = MessageAttachment(
        message_id=message.id,
        file_name=file_name,
        content_type=str(content_type) if content_type else None,
        url="",
        size_bytes=len(data),
    )
    db.add(attachment)
    db.flush()

    storage_root = Path(request.app.state.config.artifact_storage_dir).resolve()
    target_dir = storage_root / str(attachment.id)
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / file_name).write_bytes(data)
    attachment.url = f"/api/attachments/{attachment.id}/download"
    return attachment


def _safe_file_name(value: object) -> str:
    name = Path(str(value)).name.strip() or "artifact.bin"
    name = re.sub(r"[^A-Za-z0-9_.() -]+", "-", name).strip(" .")
    return name[:180] or "artifact.bin"


@router.post("/jobs/{job_id}/fail", response_model=RunnerJobOut)
def fail_job(
    job_id: int,
    payload: RunnerFailIn,
    db: Annotated[Session, Depends(get_db)],
    _runner_key: Annotated[None, Depends(require_runner_key)],
) -> RunnerJob:
    job = db.get(RunnerJob, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Runner job not found")
    if job.status != "running":
        raise HTTPException(status.HTTP_409_CONFLICT, "Runner job is not running")

    error = payload.error or {}
    error_message = payload.error_message or error.get("message") or "Runner job failed"
    retryable = error.get("retryable", True)
    data_json = payload.data_json or error

    job.error_message = error_message
    job.heartbeat_at = now()
    if retryable and job.attempts < job.max_attempts:
        job.status = "queued"
        job.runner_node_id = None
        job.next_run_at = now() + timedelta(seconds=payload.retry_after_seconds)
        add_job_event(
            db,
            job,
            "failed_retrying",
            message=error_message,
            data_json=data_json,
        )
    else:
        job.status = "failed"
        job.completed_at = now()
        if job.task is not None:
            job.task.status = "failed"
        add_job_event(
            db,
            job,
            "failed_final",
            message=error_message,
            data_json=data_json,
        )
    db.commit()
    db.refresh(job)
    return job
