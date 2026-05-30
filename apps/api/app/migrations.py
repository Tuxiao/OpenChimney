from __future__ import annotations

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from . import models  # noqa: F401 - imports mapped classes before create_all.
from .config import AppConfig
from .db import Base
from .hermes_settings import ensure_hermes_setting
from .models import AppSetting, Role, User
from .security import hash_password


SCHEMA_VERSION = 1


def init_schema(engine: Engine) -> None:
    Base.metadata.create_all(engine)


def seed_data(db: Session, config: AppConfig) -> None:
    roles_by_name = {role.name: role for role in db.query(Role).all()}
    for name, description in {
        "user": "Default local application user.",
        "admin": "Full administrative access.",
    }.items():
        if name not in roles_by_name:
            role = Role(name=name, description=description)
            db.add(role)
            roles_by_name[name] = role

    db.flush()

    admin = db.query(User).filter(User.email == config.default_admin_email.lower()).one_or_none()
    if admin is None:
        admin = User(
            email=config.default_admin_email.lower(),
            display_name="Admin",
            password_hash=hash_password(config.default_admin_password),
            is_active=True,
        )
        admin.roles.extend([roles_by_name["user"], roles_by_name["admin"]])
        db.add(admin)

    settings = {setting.key: setting for setting in db.query(AppSetting).all()}
    if "schema.version" not in settings:
        db.add(AppSetting(key="schema.version", value_json={"version": SCHEMA_VERSION}))
    if "runner.key.configured" not in settings:
        db.add(AppSetting(key="runner.key.configured", value_json={"configured": True}, is_secret=True))
    ensure_hermes_setting(db)

    db.commit()
