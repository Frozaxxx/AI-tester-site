"""Перевод между доменной сущностью RefreshToken и ORM-моделью RefreshTokenModel."""

from app.domain.entities.refresh_token import RefreshToken
from app.infrastructure.db.models import RefreshTokenModel


def to_entity(model: RefreshTokenModel) -> RefreshToken:
    return RefreshToken(
        id=model.id,
        user_id=model.user_id,
        token_hash=model.token_hash,
        expires_at=model.expires_at,
        revoked_at=model.revoked_at,
        created_at=model.created_at,
    )


def to_model(entity: RefreshToken) -> RefreshTokenModel:
    return RefreshTokenModel(
        id=entity.id,
        user_id=entity.user_id,
        token_hash=entity.token_hash,
        expires_at=entity.expires_at,
        revoked_at=entity.revoked_at,
        created_at=entity.created_at,
    )
