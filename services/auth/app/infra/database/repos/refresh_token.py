import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import RefreshToken
from app.infra.database.mappers import RefreshTokenMapper
from app.infra.database.models import RefreshTokenOrm


class SqlRefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, token: RefreshToken) -> None:
        """Сохраняет новый refresh-токен."""
        self._session.add(RefreshTokenMapper.to_model(token))
        await self._session.flush()

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        """Находит refresh-токен по хэшу и блокирует строку до конца транзакции."""
        result = await self._session.execute(
            select(RefreshTokenOrm)
            .where(RefreshTokenOrm.token_hash == token_hash)
            .with_for_update()
        )
        model = result.scalar_one_or_none()
        return RefreshTokenMapper.from_model(model) if model else None

    async def save(self, token: RefreshToken) -> None:
        """Сохраняет изменения refresh-токена."""
        await self._session.merge(RefreshTokenMapper.to_model(token))
        await self._session.flush()

    async def revoke_all(self, user_id: uuid.UUID, now: datetime) -> None:
        """Отзывает все действующие refresh-токены пользователя."""
        await self._session.execute(
            update(RefreshTokenOrm)
            .where(RefreshTokenOrm.user_id == user_id, RefreshTokenOrm.revoked_at.is_(None))
            .values(revoked_at=now)
        )
