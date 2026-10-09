"""Перевод между доменной сущностью User и ORM-моделью UserModel."""

from app.domain.entities.user import User
from app.infrastructure.db.models import UserModel


def to_entity(model: UserModel) -> User:
    return User(
        id=model.id,
        email=model.email,
        password_hash=model.password_hash,
        created_at=model.created_at,
    )


def to_model(entity: User) -> UserModel:
    return UserModel(
        id=entity.id,
        email=entity.email,
        password_hash=entity.password_hash,
        created_at=entity.created_at,
    )
