from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets

try:
    from passlib.context import CryptContext
except Exception:  # pragma: no cover - used only if optional dependency is absent.
    CryptContext = None


if CryptContext is not None:
    _pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
else:
    _pwd_context = None


def hash_password(password: str) -> str:
    if _pwd_context is not None:
        return _pwd_context.hash(password)

    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 390_000)
    return "pbkdf2_sha256$390000$%s$%s" % (
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, password_hash: str) -> bool:
    if _pwd_context is not None and not password_hash.startswith("pbkdf2_sha256$"):
        return _pwd_context.verify(password, password_hash)

    algorithm, rounds, salt_b64, digest_b64 = password_hash.split("$", 3)
    if algorithm != "pbkdf2_sha256":
        return False
    salt = base64.b64decode(salt_b64)
    expected = base64.b64decode(digest_b64)
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(rounds))
    return hmac.compare_digest(actual, expected)


def new_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
