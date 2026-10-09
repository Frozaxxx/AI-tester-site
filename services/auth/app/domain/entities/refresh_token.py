import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class RefreshToken:
    user_id: uuid.UUID
    token_hash: str  # сам токен не храним, только хэш
    expires_at: datetime
    revoked_at: datetime | None = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
