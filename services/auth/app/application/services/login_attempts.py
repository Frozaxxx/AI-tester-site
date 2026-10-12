from redis.asyncio import Redis

from app.config import settings
from app.domain.exceptions import TooManyAttemptsError


def _key(email: str) -> str:
    """Возвращает ключ Redis со счётчиком неудачных входов для email."""
    return f"auth:login_attempts:{email}"


async def ensure_not_blocked(redis: Redis, email: str) -> None:
    """Запрещает вход, если для этого email исчерпан лимит попыток."""
    attempts = await redis.get(_key(email))
    if attempts is not None and int(attempts) >= settings.login_attempts_limit:
        raise TooManyAttemptsError


async def register_failure(redis: Redis, email: str) -> None:
    """Увеличивает счётчик неудачных входов и запускает таймер блокировки."""
    key = _key(email)
    attempts = await redis.incr(key)
    if attempts == 1:
        await redis.expire(key, settings.login_block_minutes * 60)


async def reset(redis: Redis, email: str) -> None:
    """Сбрасывает счётчик неудачных входов после успешного входа."""
    await redis.delete(_key(email))
