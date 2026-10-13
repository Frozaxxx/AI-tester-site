import jwt
from redis.asyncio import Redis

from app.config import settings
from app.exceptions import UnauthorizedError

TOKEN_TYPE = "access"
REVOKED_KEY = "auth:revoked:{jti}"


async def verify_access_token(token: str | None, public_key: str, redis: Redis) -> str:
    """Проверяет access-токен и возвращает id пользователя."""
    if not token:
        raise UnauthorizedError
    try:
        payload = jwt.decode(
            token,
            public_key,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={"require": ["sub", "jti", "exp", "iss", "aud"]},
        )
    except jwt.InvalidTokenError:
        raise UnauthorizedError("Недействительный токен") from None
    if payload.get("type") != TOKEN_TYPE:
        raise UnauthorizedError("Недействительный токен")
    if await redis.exists(REVOKED_KEY.format(jti=payload["jti"])):
        raise UnauthorizedError("Токен отозван")
    return payload["sub"]
