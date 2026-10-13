from datetime import UTC, datetime

from app.domain.entities import Project, Scenario
from app.infra.database.models import ProjectOrm, ScenarioOrm


def _utc(value: datetime) -> datetime:
    """Добавляет к дате часовой пояс UTC, если его нет."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


class ProjectMapper:
    @staticmethod
    def from_model(model: ProjectOrm) -> Project:
        """Собирает доменный проект из записи в базе."""
        return Project(
            id=model.id,
            owner_id=model.owner_id,
            name=model.name,
            base_url=model.base_url,
            created_at=_utc(model.created_at),
        )

    @staticmethod
    def to_model(entity: Project) -> ProjectOrm:
        """Готовит проект к сохранению в базу."""
        return ProjectOrm(
            id=entity.id,
            owner_id=entity.owner_id,
            name=entity.name,
            base_url=entity.base_url,
            created_at=entity.created_at,
        )


class ScenarioMapper:
    @staticmethod
    def from_model(model: ScenarioOrm) -> Scenario:
        """Собирает доменный сценарий из записи в базе."""
        return Scenario(
            id=model.id,
            project_id=model.project_id,
            title=model.title,
            text=model.text,
            created_at=_utc(model.created_at),
        )

    @staticmethod
    def to_model(entity: Scenario) -> ScenarioOrm:
        """Готовит сценарий к сохранению в базу."""
        return ScenarioOrm(
            id=entity.id,
            project_id=entity.project_id,
            title=entity.title,
            text=entity.text,
            created_at=entity.created_at,
        )
