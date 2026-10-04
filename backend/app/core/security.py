from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.core.config import get_auth_settings


password_hash = PasswordHash.recommended()
# Verify against a real hash even when the email does not exist.
DUMMY_PASSWORD_HASH = password_hash.hash("dummy-password-for-login-timing")
JWT_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def create_access_token(user_id: int) -> str:
    settings = get_auth_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> int:
    settings = get_auth_settings()
    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[JWT_ALGORITHM],
        options={"require": ["sub", "iat", "exp"]},
    )
    subject = payload["sub"]
    if not isinstance(subject, str) or not subject.isascii() or not subject.isdecimal():
        raise jwt.InvalidTokenError("Invalid user ID")

    user_id = int(subject)
    if not 0 < user_id <= 2**63 - 1:
        raise jwt.InvalidTokenError("Invalid user ID")
    return user_id
