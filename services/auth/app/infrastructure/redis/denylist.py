"""Чёрный список access-токенов в Redis.

При выходе jti токена кладётся в Redis на столько, сколько токен ещё жил бы.
Потом ключ удаляется сам: истёкший токен и так не пройдёт проверку.
"""

from datetime import UTC, datetime

from redis.asyncio import Redis

KEY_PREFIX = "auth:revoked:"


class AccessTokenDenylist:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def add(self, jti: str, expires_at: datetime) -> None:
        ttl = int((expires_at - datetime.now(UTC)).total_seconds())
        if ttl > 0:
            await self._redis.set(KEY_PREFIX + jti, 1, ex=ttl)

    async def contains(self, jti: str) -> bool:
        return await self._redis.exists(KEY_PREFIX + jti) > 0
