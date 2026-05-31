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


def ensure_user_role(user: User, role: Role) -> None:
    if role.name not in {current_role.name for current_role in user.roles}:
        user.roles.append(role)


def remove_roles(user: User, role_names: set[str]) -> None:
    user.roles = [role for role in user.roles if role.name not in role_names]


def seed_data(db: Session, config: AppConfig) -> None:
    roles_by_name = {role.name: role for role in db.query(Role).all()}
    for name, description in {
        "user": "Default local application user.",
        "super_admin": "Dedicated super administrator access.",
    }.items():
        if name not in roles_by_name:
            role = Role(name=name, description=description)
            db.add(role)
            roles_by_name[name] = role

    db.flush()

    default_user_email = config.default_admin_email.lower()
    super_admin_email = config.super_admin_email.lower()

    default_user = db.query(User).filter(User.email == default_user_email).one_or_none()
    if default_user is None:
        default_user = User(
            email=config.default_admin_email.lower(),
            display_name="Default User",
            password_hash=hash_password(config.default_admin_password),
            is_active=True,
        )
        db.add(default_user)
        db.flush()
    if default_user_email != super_admin_email:
        remove_roles(default_user, {"admin", "super_admin"})
    ensure_user_role(default_user, roles_by_name["user"])

    super_admin = db.query(User).filter(User.email == super_admin_email).one_or_none()
    if super_admin is None:
        super_admin = User(
            email=super_admin_email,
            display_name="Super Admin",
            password_hash=hash_password(config.super_admin_password),
            is_active=True,
        )
        db.add(super_admin)
        db.flush()
    elif not super_admin.password_hash:
        super_admin.password_hash = hash_password(config.super_admin_password)
    ensure_user_role(super_admin, roles_by_name["user"])
    ensure_user_role(super_admin, roles_by_name["super_admin"])

    settings = {setting.key: setting for setting in db.query(AppSetting).all()}
    if "schema.version" not in settings:
        db.add(AppSetting(key="schema.version", value_json={"version": SCHEMA_VERSION}))
    if "runner.key.configured" not in settings:
        db.add(AppSetting(key="runner.key.configured", value_json={"configured": True}, is_secret=True))
    ensure_hermes_setting(db)

    db.commit()
