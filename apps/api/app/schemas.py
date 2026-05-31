from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import AliasChoices, BaseModel, Field, field_validator


class ORMModel(BaseModel):
    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime


class RoleOut(ORMModel):
    id: int
    name: str


class UserOut(ORMModel):
    id: int
    email: Optional[str] = None
    phone: Optional[str] = None
    display_name: Optional[str] = None
    is_active: bool
    roles: list[RoleOut] = []
    has_password: bool = False
    requires_password_setup: bool = False


class RegisterIn(BaseModel):
    email: str
    password: str = Field(min_length=8)
    display_name: Optional[str] = None


class LoginIn(BaseModel):
    email: str
    password: str


class AuthOut(BaseModel):
    user: UserOut
    token: TokenResponse
    is_new_user: bool = False
    requires_password_setup: bool = False


class PhoneCodeRequestIn(BaseModel):
    phone: str = Field(min_length=5, max_length=32)


class PhoneCodeRequestOut(BaseModel):
    phone: str
    expires_at: datetime
    dev_code: str


class PhoneCodeVerifyIn(BaseModel):
    phone: str = Field(min_length=5, max_length=32)
    code: str = Field(min_length=4, max_length=12)


class PhonePasswordLoginIn(BaseModel):
    phone: str = Field(min_length=5, max_length=32)
    password: str = Field(min_length=8)


class SetPasswordIn(BaseModel):
    password: str = Field(min_length=8)


class MemberIn(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    status: str = "active"
    notes: Optional[str] = None


class MemberPatch(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class MemberOut(MemberIn, ORMModel):
    id: int
    owner_user_id: int
    created_at: datetime
    updated_at: datetime


class OrderItemIn(BaseModel):
    sku: Optional[str] = None
    description: str
    quantity: int = Field(default=1, ge=1)
    unit_price: float = Field(default=0, ge=0)


class OrderItemOut(OrderItemIn, ORMModel):
    id: int


class OrderIn(BaseModel):
    member_id: Optional[int] = None
    status: str = "draft"
    currency: str = "USD"
    items: list[OrderItemIn] = []


class OrderPatch(BaseModel):
    status: Optional[str] = None
    currency: Optional[str] = None


class OrderOut(ORMModel):
    id: int
    owner_user_id: int
    member_id: Optional[int]
    status: str
    currency: str
    total_amount: float
    items: list[OrderItemOut] = []
    created_at: datetime
    updated_at: datetime


class TaskIn(BaseModel):
    title: str
    description: Optional[str] = None
    status: str = "open"
    priority: str = "normal"
    due_at: Optional[datetime] = None


class TaskPatch(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_at: Optional[datetime] = None


class TaskOut(TaskIn, ORMModel):
    id: int
    owner_user_id: int
    created_at: datetime
    updated_at: datetime


class ConversationIn(BaseModel):
    title: str
    task_id: Optional[int] = None
    status: str = "open"


class ConversationPatch(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None


class MessageIn(BaseModel):
    content: str
    role: str = "user"
    metadata_json: dict[str, Any] = {}


class MessageAttachmentOut(ORMModel):
    id: int
    file_name: str
    content_type: Optional[str] = None
    url: str
    size_bytes: Optional[int] = None
    created_at: datetime


class MessageOut(ORMModel):
    id: int
    conversation_id: int
    sender_user_id: Optional[int]
    role: str
    content: str
    metadata_json: dict[str, Any]
    attachments: list[MessageAttachmentOut] = []
    created_at: datetime


class ConversationOut(ORMModel):
    id: int
    owner_user_id: int
    task_id: Optional[int]
    title: str
    status: str
    messages: list[MessageOut] = []
    created_at: datetime
    updated_at: datetime


class TaskMessageOut(BaseModel):
    message: MessageOut
    runner_job_id: int


class AdminOverviewOut(BaseModel):
    users: int
    members: int
    orders: int
    tasks: int
    queued_jobs: int
    running_jobs: int
    failed_jobs: int


class HermesConfigIn(BaseModel):
    enabled: bool = True
    model: str = Field(min_length=1, max_length=200)
    provider: Optional[str] = Field(default=None, max_length=120)
    base_url: Optional[str] = Field(default=None, max_length=500)
    api_key: Optional[str] = Field(default=None, max_length=1000)
    clear_api_key: bool = False
    task_root: str = Field(min_length=1, max_length=500)
    hermes_home: str = Field(min_length=1, max_length=500)
    max_iterations: int = Field(ge=1, le=200)
    default_toolsets: list[str] = Field(default_factory=list)
    allowed_toolsets: list[str] = Field(default_factory=list)
    memory_mode: str = Field(pattern="^(tenant|project|off)$")
    timeout_seconds: float = Field(gt=0, le=3600)

    @field_validator("model", "provider", "base_url", "api_key", "task_root", "hermes_home", mode="before")
    @classmethod
    def trim_optional_text(cls, value: object) -> object:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("default_toolsets", "allowed_toolsets", mode="before")
    @classmethod
    def normalize_toolsets(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            items = value.split(",")
        elif isinstance(value, list):
            items = value
        else:
            raise ValueError("toolsets must be a list or comma-separated string")

        normalized: list[str] = []
        for item in items:
            toolset = str(item).strip()
            if toolset and toolset not in normalized:
                normalized.append(toolset)
        return normalized


class HermesConfigOut(BaseModel):
    enabled: bool
    model: str
    provider: Optional[str] = None
    base_url: Optional[str] = None
    api_key_configured: bool = False
    task_root: str
    hermes_home: str
    max_iterations: int
    default_toolsets: list[str] = Field(default_factory=list)
    allowed_toolsets: list[str] = Field(default_factory=list)
    memory_mode: str
    timeout_seconds: float
    updated_at: Optional[datetime] = None


class HermesRunnerConfigOut(HermesConfigOut):
    api_key: Optional[str] = None


class AuditLogOut(ORMModel):
    id: int
    actor_user_id: Optional[int]
    action: str
    entity_type: Optional[str]
    entity_id: Optional[int]
    ip_address: Optional[str]
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class RunnerNodeIn(BaseModel):
    model_config = {"populate_by_name": True}

    node_key: str = Field(validation_alias=AliasChoices("node_key", "runner_id"))
    display_name: Optional[str] = None
    version: Optional[str] = None
    capabilities: Any = Field(default_factory=dict)


class RunnerNodeOut(ORMModel):
    id: int
    node_key: str
    display_name: Optional[str]
    version: Optional[str]
    capabilities: Any
    status: str
    last_heartbeat_at: datetime


class RunnerClaimIn(BaseModel):
    model_config = {"populate_by_name": True}

    node_key: str = Field(validation_alias=AliasChoices("node_key", "runner_id"))
    capabilities: Any = Field(default_factory=dict)
    limit: int = Field(default=1, ge=1, le=10)


class RunnerJobOut(ORMModel):
    id: int
    task_id: Optional[int]
    runner_node_id: Optional[int]
    job_type: str
    status: str
    priority: int
    payload_json: dict[str, Any]
    result_json: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
    attempts: int
    max_attempts: int
    next_run_at: datetime
    claimed_at: Optional[datetime]
    heartbeat_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class RunnerCompleteIn(BaseModel):
    model_config = {"populate_by_name": True}

    result_json: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("result_json", "result"),
    )


class RunnerFailIn(BaseModel):
    model_config = {"populate_by_name": True}

    error_message: Optional[str] = None
    retry_after_seconds: int = Field(default=30, ge=0, le=86400)
    data_json: dict[str, Any] = Field(default_factory=dict)
    error: Optional[dict[str, Any]] = None
