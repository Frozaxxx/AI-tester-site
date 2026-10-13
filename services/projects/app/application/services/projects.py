import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.repos import ProjectRepository, ScenarioRepository
from app.domain.entities import Project, Scenario
from app.domain.exceptions import ProjectNotFoundError, ScenarioNotFoundError, ValidationError
from app.domain.services import create_project, create_scenario, ensure_owner


class ProjectService:
    def __init__(
        self,
        session: AsyncSession,
        project_repo: ProjectRepository,
        scenario_repo: ScenarioRepository,
    ) -> None:
        self._session = session
        self._project_repo = project_repo
        self._scenario_repo = scenario_repo

    async def create_project(self, owner_id: str, name: str, base_url: str) -> Project:
        """Создаёт проект для пользователя."""
        project = create_project(_parse_owner_id(owner_id), name, base_url)
        await self._project_repo.add(project)
        await self._session.commit()
        return project

    async def list_projects(self, owner_id: str) -> list[Project]:
        """Возвращает проекты пользователя, сначала новые."""
        return await self._project_repo.list_by_owner(_parse_owner_id(owner_id))

    async def get_project(self, owner_id: str, project_id: str) -> Project:
        """Возвращает проект, если он принадлежит пользователю."""
        project_uuid = _parse_id(project_id, ProjectNotFoundError)
        project = await self._project_repo.get(project_uuid)
        return ensure_owner(project, _parse_owner_id(owner_id))

    async def delete_project(self, owner_id: str, project_id: str) -> None:
        """Удаляет проект пользователя вместе со сценариями."""
        project = await self.get_project(owner_id, project_id)
        await self._project_repo.delete(project.id)
        await self._session.commit()

    async def create_scenario(
        self, owner_id: str, project_id: str, title: str, text: str
    ) -> Scenario:
        """Добавляет сценарий в проект пользователя."""
        project = await self.get_project(owner_id, project_id)
        scenario = create_scenario(project, title, text)
        await self._scenario_repo.add(scenario)
        await self._session.commit()
        return scenario

    async def list_scenarios(self, owner_id: str, project_id: str) -> list[Scenario]:
        """Возвращает сценарии проекта пользователя в порядке создания."""
        project = await self.get_project(owner_id, project_id)
        return await self._scenario_repo.list_by_project(project.id)

    async def delete_scenario(self, owner_id: str, scenario_id: str) -> None:
        """Удаляет сценарий, если он лежит в проекте пользователя."""
        scenario = await self._scenario_repo.get(_parse_id(scenario_id, ScenarioNotFoundError))
        if scenario is None:
            raise ScenarioNotFoundError
        try:
            await self.get_project(owner_id, str(scenario.project_id))
        except ProjectNotFoundError:
            raise ScenarioNotFoundError from None
        await self._scenario_repo.delete(scenario.id)
        await self._session.commit()


def _parse_id(raw: str, error: type[Exception]) -> uuid.UUID:
    """Превращает строку в UUID, а кривой id считает ненайденным объектом."""
    try:
        return uuid.UUID(raw)
    except ValueError:
        raise error from None


def _parse_owner_id(raw: str) -> uuid.UUID:
    """Превращает id пользователя из токена в UUID."""
    return _parse_id(raw, ValidationError)
