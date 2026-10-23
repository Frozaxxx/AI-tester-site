import uuid
from datetime import datetime
from typing import Protocol

from app.domain.entities import Finding, GeneratedTest, Run, Step


class RunRepository(Protocol):
    async def add(self, run: Run) -> None:
        """Сохраняет новый прогон."""

    async def get(self, run_id: uuid.UUID, for_update: bool = False) -> Run | None:
        """Находит прогон по id и при необходимости блокирует его до конца транзакции."""

    async def save(self, run: Run) -> None:
        """Сохраняет изменения прогона."""

    async def list_by_project(self, owner_id: uuid.UUID, project_id: uuid.UUID) -> list[Run]:
        """Возвращает прогоны проекта пользователя, сначала новые."""

    async def count_active(self, owner_id: uuid.UUID) -> int:
        """Считает незавершённые прогоны пользователя, заранее блокируя его прогоны от гонки."""

    async def claim_next(self) -> Run | None:
        """Берёт самый старый прогон из очереди и блокирует его, пропуская занятые другими."""

    async def list_stale(self, started_before: datetime) -> list[Run]:
        """Находит прогоны, которые идут дольше допустимого, и блокирует их для обновления."""


class StepRepository(Protocol):
    async def add(self, step: Step) -> None:
        """Сохраняет шаг прогона."""

    async def list_by_run(self, run_id: uuid.UUID) -> list[Step]:
        """Возвращает шаги прогона по порядку."""


class FindingRepository(Protocol):
    async def add(self, finding: Finding) -> None:
        """Сохраняет найденный баг."""

    async def list_by_run(self, run_id: uuid.UUID) -> list[Finding]:
        """Возвращает баги прогона в порядке нахождения."""


class GeneratedTestRepository(Protocol):
    async def save(self, test: GeneratedTest) -> None:
        """Сохраняет сгенерированный тест прогона или обновляет его."""

    async def get_by_run(self, run_id: uuid.UUID) -> GeneratedTest | None:
        """Находит сгенерированный тест прогона."""
