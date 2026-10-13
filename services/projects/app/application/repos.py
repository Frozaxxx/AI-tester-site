import uuid
from typing import Protocol

from app.domain.entities import Project, Scenario


class ProjectRepository(Protocol):
    async def add(self, project: Project) -> None:
        """Сохраняет новый проект."""

    async def get(self, project_id: uuid.UUID) -> Project | None:
        """Находит проект по id."""

    async def list_by_owner(self, owner_id: uuid.UUID) -> list[Project]:
        """Возвращает все проекты пользователя, сначала новые."""

    async def delete(self, project_id: uuid.UUID) -> None:
        """Удаляет проект вместе с его сценариями."""


class ScenarioRepository(Protocol):
    async def add(self, scenario: Scenario) -> None:
        """Сохраняет новый сценарий."""

    async def get(self, scenario_id: uuid.UUID) -> Scenario | None:
        """Находит сценарий по id."""

    async def list_by_project(self, project_id: uuid.UUID) -> list[Scenario]:
        """Возвращает все сценарии проекта в порядке создания."""

    async def delete(self, scenario_id: uuid.UUID) -> None:
        """Удаляет сценарий."""
