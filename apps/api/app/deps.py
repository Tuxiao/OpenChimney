from __future__ import annotations

from datetime import datetime
from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import AppConfig
from .db import get_db
from .models import SessionToken, User
from .security import hash_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_config(request: Request) -> AppConfig:
    return request.app.state.config


def current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")

    session = (
        db.query(SessionToken)
        .filter(SessionToken.token_hash == hash_token(credentials.credentials))
        .one_or_none()
    )
    if (
        session is None
        or session.revoked_at is not None
        or session.expires_at <= datetime.utcnow()
        or not session.user.is_active
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session")
    return session.user


def require_admin(user: Annotated[User, Depends(current_user)]) -> User:
    if "admin" not in {role.name for role in user.roles}:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin role required")
    return user


def require_runner_key(
    config: Annotated[AppConfig, Depends(get_config)],
    x_runner_key: Annotated[Optional[str], Header(alias="X-Runner-Key")] = None,
) -> None:
    if not x_runner_key or x_runner_key != config.runner_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid runner key")
