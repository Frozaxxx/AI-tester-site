from redis.asyncio import Redis

from app.config import settings
from app.domain.exceptions import TooManyAttemptsError


def _key(email: str) -> str:
    """Возвращает ключ Redis со счётчиком попыток входа для email."""
    return f"auth:login_attempts:{email}"


async def register_attempt(redis: Redis, email: str) -> None:
    """Засчитывает попытку входа заранее и запрещает вход, если лимит попыток исчерпан."""
    key = _key(email)
    async with redis.pipeline(transaction=True) as pipe:
        pipe.set(key, 0, ex=settings.login_block_minutes * 60, nx=True)
        pipe.incr(key)
        _, attempts = await pipe.execute()
    if attempts > settings.login_attempts_limit:
        raise TooManyAttemptsError


async def reset(redis: Redis, email: str) -> None:
    """Сбрасывает счётчик попыток после успешного входа."""
    await redis.delete(_key(email))
