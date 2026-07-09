import base64
import hashlib
import hmac
import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from pydantic import BaseModel

from app.core.config import Settings, get_settings

bearer = HTTPBearer(auto_error=False)


class Principal(BaseModel):
    user_id: str
    email: str
    role: str


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 600_000)
    return "$".join(
        (
            "pbkdf2_sha256",
            "600000",
            base64.b64encode(salt).decode(),
            base64.b64encode(digest).decode(),
        )
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, rounds, salt_value, digest_value = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), base64.b64decode(salt_value), int(rounds)
        )
        return hmac.compare_digest(actual, base64.b64decode(digest_value))
    except (ValueError, TypeError):
        return False


def create_token(principal: Principal, settings: Settings) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": principal.user_id,
        "email": principal.email,
        "role": principal.role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str, settings: Settings) -> Principal:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if not all(isinstance(payload.get(key), str) for key in ("sub", "email", "role")):
            raise ValueError("Malformed token")
        return Principal(user_id=payload["sub"], email=payload["email"], role=payload["role"])
    except (InvalidTokenError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired access token") from exc


def get_current_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Principal:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return decode_token(credentials.credentials, settings)


def require_roles(*roles: str) -> Callable[[Principal], Principal]:
    def dependency(principal: Annotated[Principal, Depends(get_current_principal)]) -> Principal:
        if principal.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return principal

    return dependency
