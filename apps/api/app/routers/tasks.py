from __future__ import annotations

import asyncio
import json
import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user, has_super_admin_role
from ..models import Conversation, Message, MessageAttachment, RunnerJob, RunnerJobEvent, Task, User
from ..schemas import MessageIn, TaskIn, TaskMessageOut, TaskOut, TaskPatch

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def is_admin(user: User) -> bool:
    return has_super_admin_role(user)


def query_task(db: Session, user: User, task_id: int) -> Task:
    query = db.query(Task).filter(Task.id == task_id)
    if not is_admin(user):
        query = query.filter(Task.owner_user_id == user.id)
    task = query.one_or_none()
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    return task


@router.get("", response_model=list[TaskOut])
def list_tasks(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
) -> list[Task]:
    query = db.query(Task).order_by(Task.created_at.desc())
    if not is_admin(user):
        query = query.filter(Task.owner_user_id == user.id)
    return query.all()


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskIn,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
) -> Task:
    task = Task(owner_user_id=user.id, **payload.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("/{task_id}", response_model=TaskOut)
def get_task(
    task_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
) -> Task:
    return query_task(db, user, task_id)


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: int,
    payload: TaskPatch,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
) -> Task:
    task = query_task(db, user, task_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, key, value)
    db.commit()
    db.refresh(task)
    return task


@router.post("/{task_id}/messages", response_model=TaskMessageOut, status_code=status.HTTP_201_CREATED)
def create_task_message(
    task_id: int,
    payload: MessageIn,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
) -> TaskMessageOut:
    task = query_task(db, user, task_id)
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.task_id == task.id,
            Conversation.owner_user_id == task.owner_user_id,
            Conversation.status == "open",
        )
        .order_by(Conversation.created_at.asc())
        .first()
    )
    if conversation is None:
        conversation = Conversation(
            owner_user_id=task.owner_user_id,
            task_id=task.id,
            title=task.title,
            status="open",
        )
        db.add(conversation)
        db.flush()

    message = Message(
        conversation_id=conversation.id,
        sender_user_id=user.id,
        role=payload.role,
        content=payload.content,
        metadata_json=payload.metadata_json,
    )
    db.add(message)
    db.flush()
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.asc(), Message.id.asc())
        .all()
    )

    task.status = "queued"
    job = RunnerJob(
        task_id=task.id,
        job_type="ai.agent.v1",
        status="queued",
        payload_json={
            "runtime": "hermes",
            "task_kind": "ai.chat",
            "instruction": "Reply to the latest user message in this task conversation.",
            "task_id": task.id,
            "conversation_id": conversation.id,
            "message_id": message.id,
            "workspace_id": f"task-{task.id}",
            "session_id": f"conversation-{conversation.id}",
            "resume": True,
            "context": {
                "task_id": task.id,
                "conversation_id": conversation.id,
                "message_id": message.id,
                "user_id": user.id,
            },
            "output_schema": "assistant_message.v1",
            "messages": [
                {
                    "role": existing_message.role,
                    "content": existing_message.content,
                }
                for existing_message in messages
            ],
        },
    )
    db.add(job)
    db.flush()
    db.add(
        RunnerJobEvent(
            runner_job_id=job.id,
            event_type="queued",
            message="Task queued from user console",
            data_json={"message_id": message.id, "conversation_id": conversation.id},
        )
    )
    db.commit()
    db.refresh(message)
    db.refresh(job)
    return TaskMessageOut(message=message, runner_job_id=job.id)


@router.get("/{task_id}/events")
async def stream_task_events(
    task_id: int,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
    once: bool = Query(False),
) -> StreamingResponse:
    query_task(db, user, task_id)
    viewer_id = user.id
    viewer_is_admin = is_admin(user)

    async def event_stream():
        last_event_id = 0
        last_message_id = 0
        last_task_updated_at: str | None = None
        last_ping_at = time.monotonic()

        while True:
            if await request.is_disconnected():
                break

            emitted = False
            with request.app.state.SessionLocal() as stream_db:
                task = _stream_visible_task(stream_db, task_id, viewer_id, viewer_is_admin)
                if task is None:
                    yield _sse("error", {"message": "Task not found"})
                    break

                task_updated_at = _iso(task.updated_at)
                if task_updated_at != last_task_updated_at:
                    last_task_updated_at = task_updated_at
                    emitted = True
                    yield _sse("task", {"task": _serialize_task(task)})

                event_rows = (
                    stream_db.query(RunnerJobEvent)
                    .join(RunnerJob, RunnerJobEvent.runner_job_id == RunnerJob.id)
                    .filter(RunnerJob.task_id == task_id, RunnerJobEvent.id > last_event_id)
                    .order_by(RunnerJobEvent.id.asc())
                    .limit(100)
                    .all()
                )
                for row in event_rows:
                    last_event_id = max(last_event_id, row.id)
                    emitted = True
                    yield _sse("runner_event", {"event": _serialize_runner_event(row)})

                message_rows = (
                    stream_db.query(Message)
                    .join(Conversation, Message.conversation_id == Conversation.id)
                    .filter(Conversation.task_id == task_id, Message.id > last_message_id)
                    .order_by(Message.id.asc())
                    .limit(100)
                    .all()
                )
                for row in message_rows:
                    last_message_id = max(last_message_id, row.id)
                    emitted = True
                    yield _sse("message", {"message": _serialize_message(row)})

            now_monotonic = time.monotonic()
            if not emitted and now_monotonic - last_ping_at >= 10:
                last_ping_at = now_monotonic
                yield _sse("ping", {"at": now_monotonic})
            if once:
                break
            await asyncio.sleep(0.6)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _stream_visible_task(db: Session, task_id: int, user_id: int, is_super_admin: bool) -> Task | None:
    query = db.query(Task).filter(Task.id == task_id)
    if not is_super_admin:
        query = query.filter(Task.owner_user_id == user_id)
    return query.one_or_none()


def _sse(event: str, payload: dict) -> str:
    data = json.dumps(payload, ensure_ascii=False, default=str)
    return f"event: {event}\ndata: {data}\n\n"


def _iso(value: object) -> str | None:
    return value.isoformat() if hasattr(value, "isoformat") else None


def _serialize_task(task: Task) -> dict[str, object]:
    return {
        "id": task.id,
        "owner_user_id": task.owner_user_id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "priority": task.priority,
        "due_at": _iso(task.due_at),
        "created_at": _iso(task.created_at),
        "updated_at": _iso(task.updated_at),
    }


def _serialize_runner_event(event: RunnerJobEvent) -> dict[str, object]:
    return {
        "id": event.id,
        "runner_job_id": event.runner_job_id,
        "event_type": event.event_type,
        "message": event.message,
        "data_json": event.data_json,
        "created_at": _iso(event.created_at),
    }


def _serialize_message(message: Message) -> dict[str, object]:
    return {
        "id": message.id,
        "conversation_id": message.conversation_id,
        "sender_user_id": message.sender_user_id,
        "role": message.role,
        "content": message.content,
        "metadata_json": message.metadata_json,
        "attachments": [_serialize_attachment(attachment) for attachment in message.attachments],
        "created_at": _iso(message.created_at),
    }


def _serialize_attachment(attachment: MessageAttachment) -> dict[str, object]:
    return {
        "id": attachment.id,
        "file_name": attachment.file_name,
        "content_type": attachment.content_type,
        "url": attachment.url,
        "size_bytes": attachment.size_bytes,
        "created_at": _iso(attachment.created_at),
    }
