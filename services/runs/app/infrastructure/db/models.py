"""Таблицы сервиса runs: прогоны и их результаты."""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    PASSED = "passed"  # багов не нашли
    FAILED = "failed"  # нашли баги
    ERROR = "error"  # прогон сломался сам
    CANCELLED = "cancelled"


class FindingKind(StrEnum):
    JS_ERROR = "js_error"  # ошибка JavaScript на странице
    HTTP_ERROR = "http_error"  # ответ 5xx или 404
    ASSERTION = "assertion"  # не выполнилась проверка из сценария
    LLM_JUDGE = "llm_judge"  # LLM решила, что поведение неверное


def _values(enum: type[StrEnum]) -> list[str]:
    """Хранить в базе значения ("queued"), а не имена (QUEUED)."""
    return [item.value for item in enum]


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(index=True)  # id из сервиса projects
    scenario_id: Mapped[uuid.UUID | None]  # пусто — свободное исследование сайта
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, name="run_status", values_callable=_values), default=RunStatus.QUEUED
    )
    tokens_used: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Step(Base):
    """Одно действие агента: клик, ввод текста, проверка."""

    __tablename__ = "steps"
    __table_args__ = (UniqueConstraint("run_id", "index"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"))
    index: Mapped[int]
    action: Mapped[str] = mapped_column(String(20))  # click, fill, goto, expect_text...
    locator: Mapped[str | None] = mapped_column(Text)  # например get_by_role("button", ...)
    value: Mapped[str | None] = mapped_column(Text)  # введённый текст или URL
    ok: Mapped[bool]
    error: Mapped[str | None] = mapped_column(Text)
    screenshot_key: Mapped[str | None] = mapped_column(String(512))  # ключ файла в MinIO
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Finding(Base):
    """Найденный баг."""

    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    step_index: Mapped[int | None]
    kind: Mapped[FindingKind] = mapped_column(
        Enum(FindingKind, name="finding_kind", values_callable=_values)
    )
    title: Mapped[str] = mapped_column(String(300))
    details: Mapped[str] = mapped_column(Text, default="")
    reproduced: Mapped[bool] = mapped_column(default=False)  # повторился без LLM
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GeneratedTest(Base):
    """Playwright-тест"""

    __tablename__ = "generated_tests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("runs.id", ondelete="CASCADE"), unique=True
    )
    code: Mapped[str] = mapped_column(Text)
    verified: Mapped[bool] = mapped_column(default=False)  # тест прогнали и он стабилен
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
