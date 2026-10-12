from datetime import UTC, datetime

from redis.asyncio import Redis


def _key(jti: str) -> str:
    """Возвращает ключ Redis для отозванного токена."""
    return f"auth:revoked:{jti}"


async def revoke_token(redis: Redis, jti: str, expires_at: datetime) -> None:
    """Добавляет access-токен в чёрный список до конца срока его действия."""
    ttl = int((expires_at - datetime.now(UTC)).total_seconds())
    if ttl > 0:
        await redis.set(_key(jti), 1, ex=ttl)


async def is_revoked(redis: Redis, jti: str) -> bool:
    """Проверяет, отозван ли access-токен."""
    return await redis.exists(_key(jti)) > 0
