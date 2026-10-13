import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services import ProjectService
from app.domain.exceptions import ProjectNotFoundError, ScenarioNotFoundError
from app.infra.database.repos import SqlProjectRepository, SqlScenarioRepository

OWNER = str(uuid.uuid4())
STRANGER = str(uuid.uuid4())


@pytest.fixture
def service(session: AsyncSession) -> ProjectService:
    """Собирает сервис проектов поверх тестовой базы."""
    return ProjectService(session, SqlProjectRepository(session), SqlScenarioRepository(session))


async def test_owner_manages_project_and_scenarios(service: ProjectService) -> None:
    """Владелец создаёт проект, добавляет сценарий, видит и удаляет их."""
    project = await service.create_project(OWNER, "Магазин", "https://shop.example.com/")
    assert project.base_url == "https://shop.example.com"
    assert [p.id for p in await service.list_projects(OWNER)] == [project.id]

    scenario = await service.create_scenario(OWNER, str(project.id), "Корзина", "Добавь товар")
    assert [s.id for s in await service.list_scenarios(OWNER, str(project.id))] == [scenario.id]

    await service.delete_scenario(OWNER, str(scenario.id))
    assert await service.list_scenarios(OWNER, str(project.id)) == []

    await service.delete_project(OWNER, str(project.id))
    assert await service.list_projects(OWNER) == []


async def test_stranger_cannot_touch_foreign_project(service: ProjectService) -> None:
    """Чужой пользователь не видит проект и не может его менять."""
    project = await service.create_project(OWNER, "Магазин", "https://shop.example.com")
    scenario = await service.create_scenario(OWNER, str(project.id), "Корзина", "Добавь товар")
    project_id = str(project.id)

    assert await service.list_projects(STRANGER) == []
    with pytest.raises(ProjectNotFoundError):
        await service.get_project(STRANGER, project_id)
    with pytest.raises(ProjectNotFoundError):
        await service.delete_project(STRANGER, project_id)
    with pytest.raises(ProjectNotFoundError):
        await service.create_scenario(STRANGER, project_id, "Взлом", "Текст")
    with pytest.raises(ProjectNotFoundError):
        await service.list_scenarios(STRANGER, project_id)
    with pytest.raises(ScenarioNotFoundError):
        await service.delete_scenario(STRANGER, str(scenario.id))
    assert await service.get_project(OWNER, project_id) == project


@pytest.mark.parametrize("bad_id", ["not-a-uuid", "", str(uuid.uuid4())])
async def test_bad_or_missing_ids_look_not_found(service: ProjectService, bad_id: str) -> None:
    """Кривой или несуществующий id даёт «не найдено», а не ошибку сервера."""
    with pytest.raises(ProjectNotFoundError):
        await service.get_project(OWNER, bad_id)
    with pytest.raises(ScenarioNotFoundError):
        await service.delete_scenario(OWNER, bad_id)
