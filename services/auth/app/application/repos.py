import uuid
from datetime import datetime
from typing import Protocol

from app.domain.entities import RefreshToken, User


class UserRepository(Protocol):
    async def add(self, user: User) -> None:
        """Сохраняет нового пользователя."""

    async def get(self, user_id: uuid.UUID) -> User | None:
        """Находит пользователя по id."""

    async def get_by_email(self, email: str) -> User | None:
        """Находит пользователя по email."""


class RefreshTokenRepository(Protocol):
    async def add(self, token: RefreshToken) -> None:
        """Сохраняет новый refresh-токен."""

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        """Находит refresh-токен по его хэшу."""

    async def save(self, token: RefreshToken) -> None:
        """Сохраняет изменения refresh-токена."""

    async def revoke_all(self, user_id: uuid.UUID, now: datetime) -> None:
        """Отзывает все действующие refresh-токены пользователя."""
