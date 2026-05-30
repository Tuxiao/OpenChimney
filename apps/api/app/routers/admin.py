from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require_admin
from ..hermes_settings import (
    HERMES_SETTING_KEY,
    ensure_hermes_setting,
    load_hermes_setting,
    merged_hermes_config,
    public_hermes_config,
)
from ..models import AuditLog, Member, Order, RunnerJob, Task, User
from ..schemas import AdminOverviewOut, AuditLogOut, HermesConfigIn, HermesConfigOut, RunnerJobOut

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/overview", response_model=AdminOverviewOut)
def overview(
    db: Annotated[Session, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
) -> AdminOverviewOut:
    return AdminOverviewOut(
        users=db.query(User).count(),
        members=db.query(Member).count(),
        orders=db.query(Order).count(),
        tasks=db.query(Task).count(),
        queued_jobs=db.query(RunnerJob).filter(RunnerJob.status == "queued").count(),
        running_jobs=db.query(RunnerJob).filter(RunnerJob.status == "running").count(),
        failed_jobs=db.query(RunnerJob).filter(RunnerJob.status == "failed").count(),
    )


@router.get("/runner-jobs", response_model=list[RunnerJobOut])
def runner_jobs(
    db: Annotated[Session, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
    status: Optional[str] = None,
) -> list[RunnerJob]:
    query = db.query(RunnerJob).order_by(RunnerJob.created_at.desc())
    if status:
        query = query.filter(RunnerJob.status == status)
    return query.limit(100).all()


@router.get("/audit-logs", response_model=list[AuditLogOut])
def audit_logs(
    db: Annotated[Session, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
) -> list[AuditLog]:
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(100).all()


@router.get("/hermes-config", response_model=HermesConfigOut)
def get_hermes_config(
    db: Annotated[Session, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
) -> dict:
    setting = ensure_hermes_setting(db)
    db.commit()
    db.refresh(setting)
    config = merged_hermes_config(setting.value_json)
    return public_hermes_config(config, setting.updated_at)


@router.put("/hermes-config", response_model=HermesConfigOut)
def update_hermes_config(
    payload: HermesConfigIn,
    db: Annotated[Session, Depends(get_db)],
    admin_user: Annotated[User, Depends(require_admin)],
) -> dict:
    current_config, setting = load_hermes_setting(db)
    if setting is None:
        setting = ensure_hermes_setting(db)

    data = payload.model_dump()
    next_config = merged_hermes_config(
        {
            "enabled": data["enabled"],
            "model": data["model"],
            "provider": data["provider"],
            "base_url": data["base_url"],
            "task_root": data["task_root"],
            "hermes_home": data["hermes_home"],
            "max_iterations": data["max_iterations"],
            "default_toolsets": data["default_toolsets"],
            "allowed_toolsets": data["allowed_toolsets"],
            "memory_mode": data["memory_mode"],
            "timeout_seconds": data["timeout_seconds"],
        }
    )
    if data["clear_api_key"]:
        next_config["api_key"] = None
    elif data["api_key"]:
        next_config["api_key"] = data["api_key"]
    else:
        next_config["api_key"] = current_config.get("api_key")

    setting.value_json = next_config
    setting.is_secret = True
    db.add(
        AuditLog(
            actor_user_id=admin_user.id,
            action="updated hermes config",
            entity_type="app_setting",
            entity_id=setting.id,
            metadata_json={"key": HERMES_SETTING_KEY, "config": public_hermes_config(next_config)},
        )
    )
    db.commit()
    db.refresh(setting)
    return public_hermes_config(merged_hermes_config(setting.value_json), setting.updated_at)
