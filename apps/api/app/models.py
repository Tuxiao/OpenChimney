from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def now_utc() -> datetime:
    return datetime.utcnow()


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=now_utc, onupdate=now_utc, nullable=False
    )


class UserRole(Base):
    __tablename__ = "user_roles"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[Optional[str]] = mapped_column(String(320), unique=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(32), unique=True, index=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(120))
    password_hash: Mapped[Optional[str]] = mapped_column(String(255))
    password_set_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    roles: Mapped[list["Role"]] = relationship(
        secondary="user_roles", back_populates="users", lazy="selectin"
    )
    sessions: Mapped[list["SessionToken"]] = relationship(back_populates="user")

    @property
    def has_password(self) -> bool:
        return bool(self.password_hash)

    @property
    def requires_password_setup(self) -> bool:
        return not self.has_password


class Role(TimestampMixin, Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255))

    users: Mapped[list[User]] = relationship(
        secondary="user_roles", back_populates="roles", lazy="selectin"
    )


class SessionToken(TimestampMixin, Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    user_agent: Mapped[Optional[str]] = mapped_column(String(255))
    ip_address: Mapped[Optional[str]] = mapped_column(String(80))

    user: Mapped[User] = relationship(back_populates="sessions")


class PhoneLoginCode(TimestampMixin, Base):
    __tablename__ = "phone_login_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    phone: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Member(TimestampMixin, Base):
    __tablename__ = "members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(320), index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(40), default="active", nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    orders: Mapped[list["Order"]] = relationship(back_populates="member")


class Order(TimestampMixin, Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    member_id: Mapped[Optional[int]] = mapped_column(ForeignKey("members.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(40), default="draft", nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(12), default="USD", nullable=False)
    total_amount: Mapped[float] = mapped_column(Float, default=0, nullable=False)

    member: Mapped[Optional[Member]] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )


class OrderItem(TimestampMixin, Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    sku: Mapped[Optional[str]] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, default=0, nullable=False)

    order: Mapped[Order] = relationship(back_populates="items")


class Task(TimestampMixin, Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="open", nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(20), default="normal", nullable=False)
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    conversations: Mapped[list["Conversation"]] = relationship(back_populates="task")
    runner_jobs: Mapped[list["RunnerJob"]] = relationship(back_populates="task")


class Conversation(TimestampMixin, Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    task_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tasks.id", ondelete="SET NULL"), index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="open", nullable=False)

    task: Mapped[Optional[Task]] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", lazy="selectin"
    )


class Message(TimestampMixin, Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sender_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    role: Mapped[str] = mapped_column(String(40), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
    attachments: Mapped[list["MessageAttachment"]] = relationship(
        back_populates="message", cascade="all, delete-orphan", lazy="selectin"
    )


class MessageAttachment(TimestampMixin, Base):
    __tablename__ = "message_attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[Optional[str]] = mapped_column(String(120))
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer)

    message: Mapped[Message] = relationship(back_populates="attachments")


class RunnerNode(TimestampMixin, Base):
    __tablename__ = "runner_nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    node_key: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(160))
    version: Mapped[Optional[str]] = mapped_column(String(80))
    capabilities: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    last_heartbeat_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="online", nullable=False)

    jobs: Mapped[list["RunnerJob"]] = relationship(back_populates="runner_node")


class RunnerJob(TimestampMixin, Base):
    __tablename__ = "runner_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tasks.id", ondelete="SET NULL"), index=True)
    runner_node_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("runner_nodes.id", ondelete="SET NULL"), index=True
    )
    job_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), default="queued", nullable=False, index=True)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    result_json: Mapped[Optional[dict]] = mapped_column(JSON)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    next_run_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, nullable=False, index=True)
    claimed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    heartbeat_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    task: Mapped[Optional[Task]] = relationship(back_populates="runner_jobs")
    runner_node: Mapped[Optional[RunnerNode]] = relationship(back_populates="jobs")
    events: Mapped[list["RunnerJobEvent"]] = relationship(
        back_populates="job", cascade="all, delete-orphan", lazy="selectin"
    )


class RunnerJobEvent(TimestampMixin, Base):
    __tablename__ = "runner_job_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    runner_job_id: Mapped[int] = mapped_column(
        ForeignKey("runner_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text)
    data_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    job: Mapped[RunnerJob] = relationship(back_populates="events")


class AuditLog(TimestampMixin, Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    entity_type: Mapped[Optional[str]] = mapped_column(String(80))
    entity_id: Mapped[Optional[int]] = mapped_column(Integer)
    ip_address: Mapped[Optional[str]] = mapped_column(String(80))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class AppSetting(TimestampMixin, Base):
    __tablename__ = "app_settings"
    __table_args__ = (UniqueConstraint("key", name="uq_app_settings_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(120), nullable=False)
    value_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


def count_for(model):
    return func.count(model.id)
