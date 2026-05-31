from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..config import AppConfig
from ..db import get_db
from ..deps import current_user, get_config
from ..models import AuditLog, PhoneLoginCode, Role, SessionToken, User
from ..schemas import (
    AuthOut,
    LoginIn,
    PhoneCodeRequestIn,
    PhoneCodeRequestOut,
    PhoneCodeVerifyIn,
    PhonePasswordLoginIn,
    RegisterIn,
    SetPasswordIn,
    TokenResponse,
    UserOut,
)
from ..security import hash_password, hash_token, new_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


def normalize_phone(phone: str) -> str:
    cleaned = "".join(ch for ch in phone.strip() if ch.isdigit() or ch == "+")
    if cleaned.startswith("00"):
        cleaned = f"+{cleaned[2:]}"
    if not cleaned:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Phone number is required")
    return cleaned


def get_user_role(db: Session) -> Role:
    role = db.query(Role).filter(Role.name == "user").one_or_none()
    if role is None:
        role = Role(name="user", description="Default local application user.")
        db.add(role)
        db.flush()
    return role


def build_auth_out(user: User, token: str, session: SessionToken, *, is_new_user: bool = False) -> AuthOut:
    return AuthOut(
        user=UserOut.model_validate(user),
        token=TokenResponse(access_token=token, expires_at=session.expires_at),
        is_new_user=is_new_user,
        requires_password_setup=user.requires_password_setup,
    )


def create_session(
    db: Session, user: User, config: AppConfig, request: Request
) -> tuple[str, SessionToken]:
    token = new_token()
    session = SessionToken(
        user_id=user.id,
        token_hash=hash_token(token),
        expires_at=datetime.utcnow() + timedelta(seconds=config.session_ttl_seconds),
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    db.add(session)
    return token, session


@router.post("/register", response_model=AuthOut, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterIn,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    config: Annotated[AppConfig, Depends(get_config)],
) -> AuthOut:
    email = payload.email.strip().lower()
    if db.query(User).filter(User.email == email).first() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email is already registered")

    user_role = get_user_role(db)
    user = User(
        email=email,
        display_name=payload.display_name,
        password_hash=hash_password(payload.password),
        is_active=True,
    )
    user.roles.append(user_role)
    db.add(user)
    db.flush()
    token, session = create_session(db, user, config, request)
    db.add(AuditLog(actor_user_id=user.id, action="auth.register", entity_type="user", entity_id=user.id))
    db.commit()
    db.refresh(user)
    return build_auth_out(user, token, session)


@router.post("/login", response_model=AuthOut)
def login(
    payload: LoginIn,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    config: Annotated[AppConfig, Depends(get_config)],
) -> AuthOut:
    user = db.query(User).filter(User.email == payload.email.strip().lower()).one_or_none()
    if (
        user is None
        or not user.is_active
        or not user.password_hash
        or not verify_password(payload.password, user.password_hash)
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    token, session = create_session(db, user, config, request)
    db.add(AuditLog(actor_user_id=user.id, action="auth.login", entity_type="user", entity_id=user.id))
    db.commit()
    db.refresh(user)
    return build_auth_out(user, token, session)


@router.post("/phone/request-code", response_model=PhoneCodeRequestOut)
def request_phone_code(
    payload: PhoneCodeRequestIn,
    db: Annotated[Session, Depends(get_db)],
) -> PhoneCodeRequestOut:
    phone = normalize_phone(payload.phone)
    code = f"{secrets.randbelow(1_000_000):06d}"
    expires_at = datetime.utcnow() + timedelta(minutes=5)
    db.add(
        PhoneLoginCode(
            phone=phone,
            code_hash=hash_token(code),
            expires_at=expires_at,
        )
    )
    db.add(AuditLog(action="auth.phone_code.requested", entity_type="phone_login_code"))
    db.commit()
    return PhoneCodeRequestOut(phone=phone, expires_at=expires_at, dev_code=code)


@router.post("/phone/verify-code", response_model=AuthOut)
def verify_phone_code(
    payload: PhoneCodeVerifyIn,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    config: Annotated[AppConfig, Depends(get_config)],
) -> AuthOut:
    phone = normalize_phone(payload.phone)
    code_row = (
        db.query(PhoneLoginCode)
        .filter(
            PhoneLoginCode.phone == phone,
            PhoneLoginCode.consumed_at.is_(None),
            PhoneLoginCode.expires_at > datetime.utcnow(),
        )
        .order_by(PhoneLoginCode.created_at.desc())
        .first()
    )
    if code_row is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired SMS code")
    code_row.attempts += 1
    if code_row.attempts > 5 or code_row.code_hash != hash_token(payload.code.strip()):
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired SMS code")

    code_row.consumed_at = datetime.utcnow()
    user = db.query(User).filter(User.phone == phone).one_or_none()
    is_new_user = user is None
    if user is None:
        user = User(
            email=None,
            phone=phone,
            display_name=phone,
            password_hash=None,
            is_active=True,
        )
        user.roles.append(get_user_role(db))
        db.add(user)
        db.flush()
        db.add(AuditLog(actor_user_id=user.id, action="auth.phone.auto_register", entity_type="user", entity_id=user.id))

    if not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User account is disabled")

    token, session = create_session(db, user, config, request)
    db.add(AuditLog(actor_user_id=user.id, action="auth.phone.login", entity_type="user", entity_id=user.id))
    db.commit()
    db.refresh(user)
    return build_auth_out(user, token, session, is_new_user=is_new_user)


@router.post("/phone/login", response_model=AuthOut)
def login_with_phone_password(
    payload: PhonePasswordLoginIn,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    config: Annotated[AppConfig, Depends(get_config)],
) -> AuthOut:
    phone = normalize_phone(payload.phone)
    user = db.query(User).filter(User.phone == phone).one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid phone or password")
    if not user.password_hash:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Password is not set for this phone. Sign in with SMS first.",
        )
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid phone or password")

    token, session = create_session(db, user, config, request)
    db.add(AuditLog(actor_user_id=user.id, action="auth.phone_password.login", entity_type="user", entity_id=user.id))
    db.commit()
    db.refresh(user)
    return build_auth_out(user, token, session)


@router.post("/set-password", response_model=UserOut)
def set_password(
    payload: SetPasswordIn,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
) -> User:
    user.password_hash = hash_password(payload.password)
    user.password_set_at = datetime.utcnow()
    db.add(AuditLog(actor_user_id=user.id, action="auth.password.set", entity_type="user", entity_id=user.id))
    db.commit()
    db.refresh(user)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
) -> None:
    auth_header = request.headers.get("authorization", "")
    token = auth_header.removeprefix("Bearer ").removeprefix("bearer ")
    session = db.query(SessionToken).filter(SessionToken.token_hash == hash_token(token)).one_or_none()
    if session is not None:
        session.revoked_at = datetime.utcnow()
    db.add(AuditLog(actor_user_id=user.id, action="auth.logout", entity_type="user", entity_id=user.id))
    db.commit()


@router.get("/me", response_model=UserOut)
def me(user: Annotated[User, Depends(current_user)]) -> User:
    return user
