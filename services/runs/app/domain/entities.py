import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


def now() -> datetime:
    """Возвращает текущее время в UTC."""
    return datetime.now(UTC)


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    CANCELLED = "cancelled"


class FindingKind(StrEnum):
    JS_ERROR = "js_error"
    HTTP_ERROR = "http_error"
    ASSERTION = "assertion"
    LLM_JUDGE = "llm_judge"


@dataclass(kw_only=True)
class Run:
    owner_id: uuid.UUID
    project_id: uuid.UUID
    scenario_id: uuid.UUID | None = None
    status: RunStatus = RunStatus.QUEUED
    tokens_used: int = 0
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=now)
    started_at: datetime | None = None
    finished_at: datetime | None = None


@dataclass(kw_only=True)
class Step:
    run_id: uuid.UUID
    index: int
    action: str
    ok: bool
    locator: str | None = None
    value: str | None = None
    error: str | None = None
    screenshot_key: str | None = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=now)


@dataclass(kw_only=True)
class Finding:
    run_id: uuid.UUID
    kind: FindingKind
    title: str
    details: str = ""
    step_index: int | None = None
    reproduced: bool = False
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=now)


@dataclass(kw_only=True)
class GeneratedTest:
    run_id: uuid.UUID
    code: str
    verified: bool = False
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=now)
