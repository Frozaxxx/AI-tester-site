import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


def now() -> datetime:
    """Возвращает текущее время в UTC."""
    return datetime.now(UTC)


@dataclass(kw_only=True)
class User:
    email: str
    password_hash: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=now)


@dataclass(kw_only=True)
class RefreshToken:
    user_id: uuid.UUID
    token_hash: str
    expires_at: datetime
    revoked_at: datetime | None = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=now)
