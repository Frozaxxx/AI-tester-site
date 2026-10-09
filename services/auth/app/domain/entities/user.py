import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class User:
    email: str
    password_hash: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
