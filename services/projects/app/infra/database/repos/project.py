import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import Project
from app.infra.database.mappers import ProjectMapper
from app.infra.database.models import ProjectOrm


class SqlProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, project: Project) -> None:
        """Сохраняет новый проект."""
        self._session.add(ProjectMapper.to_model(project))
        await self._session.flush()

    async def get(self, project_id: uuid.UUID) -> Project | None:
        """Находит проект по id."""
        model = await self._session.get(ProjectOrm, project_id)
        return ProjectMapper.from_model(model) if model else None

    async def list_by_owner(self, owner_id: uuid.UUID) -> list[Project]:
        """Возвращает все проекты пользователя, сначала новые."""
        result = await self._session.scalars(
            select(ProjectOrm)
            .where(ProjectOrm.owner_id == owner_id)
            .order_by(ProjectOrm.created_at.desc())
        )
        return [ProjectMapper.from_model(model) for model in result]

    async def delete(self, project_id: uuid.UUID) -> None:
        """Удаляет проект вместе с его сценариями."""
        await self._session.execute(delete(ProjectOrm).where(ProjectOrm.id == project_id))
