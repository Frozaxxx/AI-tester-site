import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import User
from app.domain.exceptions import EmailAlreadyExistsError
from app.infra.database.mappers import UserMapper
from app.infra.database.models import UserOrm


class SqlUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user: User) -> None:
        """Сохраняет пользователя, а если email уже занят, выбрасывает ошибку."""
        self._session.add(UserMapper.to_model(user))
        try:
            await self._session.flush()
        except IntegrityError:
            await self._session.rollback()
            raise EmailAlreadyExistsError from None

    async def get(self, user_id: uuid.UUID) -> User | None:
        """Находит пользователя по id."""
        model = await self._session.get(UserOrm, user_id)
        return UserMapper.from_model(model) if model else None

    async def get_by_email(self, email: str) -> User | None:
        """Находит пользователя по email."""
        result = await self._session.execute(select(UserOrm).where(UserOrm.email == email))
        model = result.scalar_one_or_none()
        return UserMapper.from_model(model) if model else None
