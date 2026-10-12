import asyncio
import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import cache

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from cryptography.hazmat.primitives import serialization

from app.config import settings
from app.domain.exceptions import UnauthorizedError

TOKEN_TYPE = "access"

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Хэширует пароль алгоритмом argon2."""
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Проверяет, подходит ли пароль к хэшу."""
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(16))


async def hash_password_async(password: str) -> str:
    """Хэширует пароль в отдельном потоке, чтобы не блокировать сервер."""
    return await asyncio.to_thread(hash_password, password)


async def verify_password_async(password: str, password_hash: str) -> bool:
    """Проверяет пароль в отдельном потоке, чтобы не блокировать сервер."""
    return await asyncio.to_thread(verify_password, password, password_hash)


@dataclass
class AccessToken:
    token: str
    jti: str
    expires_at: datetime


@cache
def public_key_pem() -> str:
    """Возвращает публичный ключ, полученный из приватного ключа подписи."""
    key = serialization.load_pem_private_key(settings.jwt_private_key.encode(), password=None)
    return (
        key.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )


def create_access_token(user_id: uuid.UUID) -> AccessToken:
    """Создаёт подписанный access-токен для пользователя."""
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=settings.access_token_ttl_minutes)
    jti = uuid.uuid4().hex
    payload = {
        "sub": str(user_id),
        "jti": jti,
        "iat": now,
        "exp": expires_at,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "type": TOKEN_TYPE,
    }
    token = jwt.encode(payload, settings.jwt_private_key, algorithm=settings.jwt_algorithm)
    return AccessToken(token=token, jti=jti, expires_at=expires_at)


def decode_access_token(token: str) -> dict:
    """Проверяет access-токен и возвращает его содержимое."""
    try:
        payload = jwt.decode(
            token,
            public_key_pem(),
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={"require": ["sub", "jti", "exp", "iss", "aud"]},
        )
    except jwt.InvalidTokenError:
        raise UnauthorizedError("Недействительный токен") from None
    if payload.get("type") != TOKEN_TYPE:
        raise UnauthorizedError("Недействительный токен")
    return payload


def new_refresh_token() -> tuple[str, str]:
    """Создаёт случайный refresh-токен и его хэш для хранения в базе."""
    token = secrets.token_urlsafe(32)
    return token, hash_refresh_token(token)


def hash_refresh_token(token: str) -> str:
    """Считает хэш refresh-токена."""
    return hashlib.sha256(token.encode()).hexdigest()
