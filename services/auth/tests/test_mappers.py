"""Сущность -> ORM-модель -> сущность должна вернуть то же самое."""

import uuid
from datetime import UTC, datetime, timedelta

from app.domain.entities.refresh_token import RefreshToken
from app.domain.entities.user import User
from app.infrastructure.db.mappers import refresh_token as token_mapper
from app.infrastructure.db.mappers import user as user_mapper


def test_user_roundtrip() -> None:
    user = User(email="andrey@example.com", password_hash="hash")
    assert user_mapper.to_entity(user_mapper.to_model(user)) == user


def test_refresh_token_roundtrip() -> None:
    now = datetime.now(UTC)
    token = RefreshToken(
        user_id=uuid.uuid4(),
        token_hash="hash",
        expires_at=now + timedelta(days=1),
        revoked_at=now,
    )
    assert token_mapper.to_entity(token_mapper.to_model(token)) == token
