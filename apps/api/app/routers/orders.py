from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user, has_super_admin_role
from ..models import Member, Order, OrderItem, User
from ..schemas import OrderIn, OrderOut, OrderPatch

router = APIRouter(prefix="/api/orders", tags=["orders"])


def is_admin(user: User) -> bool:
    return has_super_admin_role(user)


def total_for(items: list[OrderItem]) -> float:
    return sum(item.quantity * item.unit_price for item in items)


def query_order(db: Session, user: User, order_id: int) -> Order:
    query = db.query(Order).filter(Order.id == order_id)
    if not is_admin(user):
        query = query.filter(Order.owner_user_id == user.id)
    order = query.one_or_none()
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    return order


@router.get("", response_model=list[OrderOut])
def list_orders(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
) -> list[Order]:
    query = db.query(Order).order_by(Order.created_at.desc())
    if not is_admin(user):
        query = query.filter(Order.owner_user_id == user.id)
    return query.all()


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderIn,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
) -> Order:
    if payload.member_id is not None:
        member = db.get(Member, payload.member_id)
        if member is None or (member.owner_user_id != user.id and not is_admin(user)):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Member is not available")

    order = Order(
        owner_user_id=user.id,
        member_id=payload.member_id,
        status=payload.status,
        currency=payload.currency,
    )
    order.items = [OrderItem(**item.model_dump()) for item in payload.items]
    order.total_amount = total_for(order.items)
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@router.get("/{order_id}", response_model=OrderOut)
def get_order(
    order_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
) -> Order:
    return query_order(db, user, order_id)


@router.patch("/{order_id}", response_model=OrderOut)
def update_order(
    order_id: int,
    payload: OrderPatch,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
) -> Order:
    order = query_order(db, user, order_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(order, key, value)
    db.commit()
    db.refresh(order)
    return order
