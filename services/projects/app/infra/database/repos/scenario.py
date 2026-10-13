import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import Scenario
from app.infra.database.mappers import ScenarioMapper
from app.infra.database.models import ScenarioOrm


class SqlScenarioRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, scenario: Scenario) -> None:
        """Сохраняет новый сценарий."""
        self._session.add(ScenarioMapper.to_model(scenario))
        await self._session.flush()

    async def get(self, scenario_id: uuid.UUID) -> Scenario | None:
        """Находит сценарий по id."""
        model = await self._session.get(ScenarioOrm, scenario_id)
        return ScenarioMapper.from_model(model) if model else None

    async def list_by_project(self, project_id: uuid.UUID) -> list[Scenario]:
        """Возвращает все сценарии проекта в порядке создания."""
        result = await self._session.scalars(
            select(ScenarioOrm)
            .where(ScenarioOrm.project_id == project_id)
            .order_by(ScenarioOrm.created_at)
        )
        return [ScenarioMapper.from_model(model) for model in result]

    async def delete(self, scenario_id: uuid.UUID) -> None:
        """Удаляет сценарий."""
        await self._session.execute(delete(ScenarioOrm).where(ScenarioOrm.id == scenario_id))
