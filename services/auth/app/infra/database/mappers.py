from datetime import UTC, datetime

from app.domain.entities import RefreshToken, User
from app.infra.database.models import RefreshTokenOrm, UserOrm


def _utc(value: datetime | None) -> datetime | None:
    """Добавляет к дате часовой пояс UTC, если его нет."""
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


class UserMapper:
    @staticmethod
    def from_model(model: UserOrm) -> User:
        """Собирает доменного пользователя из записи в базе."""
        return User(
            id=model.id,
            email=model.email,
            password_hash=model.password_hash,
            created_at=_utc(model.created_at),
        )

    @staticmethod
    def to_model(entity: User) -> UserOrm:
        """Готовит пользователя к сохранению в базу."""
        return UserOrm(
            id=entity.id,
            email=entity.email,
            password_hash=entity.password_hash,
            created_at=entity.created_at,
        )


class RefreshTokenMapper:
    @staticmethod
    def from_model(model: RefreshTokenOrm) -> RefreshToken:
        """Собирает доменный refresh-токен из записи в базе."""
        return RefreshToken(
            id=model.id,
            user_id=model.user_id,
            token_hash=model.token_hash,
            expires_at=_utc(model.expires_at),
            revoked_at=_utc(model.revoked_at),
            created_at=_utc(model.created_at),
        )

    @staticmethod
    def to_model(entity: RefreshToken) -> RefreshTokenOrm:
        """Готовит refresh-токен к сохранению в базу."""
        return RefreshTokenOrm(
            id=entity.id,
            user_id=entity.user_id,
            token_hash=entity.token_hash,
            expires_at=entity.expires_at,
            revoked_at=entity.revoked_at,
            created_at=entity.created_at,
        )
