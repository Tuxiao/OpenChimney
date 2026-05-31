from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user, has_super_admin_role
from ..models import Conversation, Message, Task, User
from ..schemas import ConversationIn, ConversationOut, ConversationPatch, MessageIn, MessageOut

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


def is_admin(user: User) -> bool:
    return has_super_admin_role(user)


def query_conversation(db: Session, user: User, conversation_id: int) -> Conversation:
    query = db.query(Conversation).filter(Conversation.id == conversation_id)
    if not is_admin(user):
        query = query.filter(Conversation.owner_user_id == user.id)
    conversation = query.one_or_none()
    if conversation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    return conversation


@router.get("", response_model=list[ConversationOut])
def list_conversations(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
) -> list[Conversation]:
    query = db.query(Conversation).order_by(Conversation.created_at.desc())
    if not is_admin(user):
        query = query.filter(Conversation.owner_user_id == user.id)
    return query.all()


@router.post("", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
def create_conversation(
    payload: ConversationIn,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
) -> Conversation:
    if payload.task_id is not None:
        task = db.get(Task, payload.task_id)
        if task is None or (task.owner_user_id != user.id and not is_admin(user)):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Task is not available")
    conversation = Conversation(owner_user_id=user.id, **payload.model_dump())
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.get("/{conversation_id}", response_model=ConversationOut)
def get_conversation(
    conversation_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
) -> Conversation:
    return query_conversation(db, user, conversation_id)


@router.patch("/{conversation_id}", response_model=ConversationOut)
def update_conversation(
    conversation_id: int,
    payload: ConversationPatch,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
) -> Conversation:
    conversation = query_conversation(db, user, conversation_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(conversation, key, value)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.post("/{conversation_id}/messages", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
def create_message(
    conversation_id: int,
    payload: MessageIn,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
) -> Message:
    conversation = query_conversation(db, user, conversation_id)
    message = Message(
        conversation_id=conversation.id,
        sender_user_id=user.id,
        role=payload.role,
        content=payload.content,
        metadata_json=payload.metadata_json,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message
