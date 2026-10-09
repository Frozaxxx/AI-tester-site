"""Выпуск токенов.

Access-токен — JWT с подписью RS256: подписываем приватным ключом, а gateway
проверяет публичным, не обращаясь к сервису auth.
Refresh-токен — случайная строка. Пользователю отдаём её, в базе храним хэш.
"""

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from cryptography.hazmat.primitives import serialization

ALGORITHM = "RS256"
ISSUER = "ai-tester-auth"  # кто выдал токен
AUDIENCE = "ai-tester-api"  # для кого токен
TOKEN_TYPE = "access"


@dataclass
class AccessToken:
    token: str
    jti: str  # id токена: по нему токен попадает в чёрный список при выходе
    expires_at: datetime


class JwtIssuer:
    def __init__(self, private_key_pem: str, ttl: timedelta) -> None:
        self._private_key = private_key_pem
        self._ttl = ttl
        key = serialization.load_pem_private_key(private_key_pem.encode(), password=None)
        self.public_key_pem = (
            key.public_key()
            .public_bytes(
                serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
            )
            .decode()
        )

    def issue(self, user_id: uuid.UUID) -> AccessToken:
        now = datetime.now(UTC)
        expires_at = now + self._ttl
        jti = uuid.uuid4().hex
        # Только id и служебные поля: JWT не шифруется, его может прочитать кто угодно.
        payload = {
            "sub": str(user_id),
            "jti": jti,
            "iat": now,
            "exp": expires_at,
            "iss": ISSUER,
            "aud": AUDIENCE,
            "type": TOKEN_TYPE,
        }
        token = jwt.encode(payload, self._private_key, algorithm=ALGORITHM)
        return AccessToken(token=token, jti=jti, expires_at=expires_at)

    def decode(self, token: str) -> dict:
        """Проверяет подпись, срок, издателя и тип. Бросает jwt.InvalidTokenError."""
        payload = jwt.decode(
            token,
            self.public_key_pem,
            algorithms=[ALGORITHM],
            issuer=ISSUER,
            audience=AUDIENCE,
            options={"require": ["sub", "jti", "exp", "iss", "aud"]},
        )
        if payload.get("type") != TOKEN_TYPE:
            raise jwt.InvalidTokenError("Неверный тип токена")
        return payload


def new_refresh_token() -> tuple[str, str]:
    """Возвращает (токен для пользователя, хэш для базы)."""
    token = secrets.token_urlsafe(32)
    return token, hash_refresh_token(token)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
