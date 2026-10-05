import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import HTTPException

from app.config.settings import Settings

hasher = PasswordHasher(type=Type.ID)
# A missing account still performs a password verification to reduce timing differences.
dummy_hash = hasher.hash(secrets.token_urlsafe(32))


def hash_password(password: str) -> str:
    return hasher.hash(password)


def verify_password(password: str, encoded: str | None) -> bool:
    try:
        return hasher.verify(encoded or dummy_hash, password) and encoded is not None
    except (VerificationError, InvalidHashError):
        return False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def create_access_token(user_id: str, session_id: str, config: Settings) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": user_id,
            "sid": session_id,
            "type": "access",
            "jti": secrets.token_hex(16),
            "iat": now,
            "nbf": now,
            "exp": now + timedelta(minutes=config.access_token_expire_minutes),
            "iss": "ligapro",
            "aud": "ligapro-mobile",
        },
        config.jwt_secret_key.get_secret_value(),
        algorithm=config.jwt_algorithm,
    )


def decode_access_token(token: str, config: Settings) -> dict:
    try:
        claims = jwt.decode(
            token,
            config.jwt_secret_key.get_secret_value(),
            algorithms=[config.jwt_algorithm],
            audience="ligapro-mobile",
            issuer="ligapro",
            options={"require": ["sub", "sid", "type", "jti", "iat", "nbf", "exp"]},
        )
        if claims["type"] != "access" or not all(
            isinstance(claims[field], str) for field in ["sub", "sid"]
        ):
            raise jwt.InvalidTokenError()
        return claims
    except jwt.InvalidTokenError:
        raise HTTPException(
            401, "Sessão inválida ou expirada.", headers={"WWW-Authenticate": "Bearer"}
        ) from None
