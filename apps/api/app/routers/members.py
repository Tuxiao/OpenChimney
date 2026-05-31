from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user, has_super_admin_role
from ..models import Member, User
from ..schemas import MemberIn, MemberOut, MemberPatch

router = APIRouter(prefix="/api/members", tags=["members"])


def query_member(db: Session, user: User, member_id: int) -> Member:
    query = db.query(Member).filter(Member.id == member_id)
    if not has_super_admin_role(user):
        query = query.filter(Member.owner_user_id == user.id)
    member = query.one_or_none()
    if member is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    return member


@router.get("", response_model=list[MemberOut])
def list_members(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
) -> list[Member]:
    query = db.query(Member).order_by(Member.created_at.desc())
    if not has_super_admin_role(user):
        query = query.filter(Member.owner_user_id == user.id)
    return query.all()


@router.post("", response_model=MemberOut, status_code=status.HTTP_201_CREATED)
def create_member(
    payload: MemberIn,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
) -> Member:
    member = Member(owner_user_id=user.id, **payload.model_dump())
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.get("/{member_id}", response_model=MemberOut)
def get_member(
    member_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
) -> Member:
    return query_member(db, user, member_id)


@router.patch("/{member_id}", response_model=MemberOut)
def update_member(
    member_id: int,
    payload: MemberPatch,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
) -> Member:
    member = query_member(db, user, member_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(member, key, value)
    db.commit()
    db.refresh(member)
    return member


@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member(
    member_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
) -> None:
    member = query_member(db, user, member_id)
    db.delete(member)
    db.commit()
