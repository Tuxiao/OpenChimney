from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user, has_super_admin_role
from ..models import Conversation, Message, RunnerJob, Task, User
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
            "toolsets": [],
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
    db.commit()
    db.refresh(message)
    db.refresh(job)
    return TaskMessageOut(message=message, runner_job_id=job.id)
