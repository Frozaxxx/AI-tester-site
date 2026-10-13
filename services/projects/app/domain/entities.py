import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


def now() -> datetime:
    """Возвращает текущее время в UTC."""
    return datetime.now(UTC)


@dataclass(kw_only=True)
class Project:
    owner_id: uuid.UUID
    name: str
    base_url: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=now)


@dataclass(kw_only=True)
class Scenario:
    project_id: uuid.UUID
    title: str
    text: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=now)
