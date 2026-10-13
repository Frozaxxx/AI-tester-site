import uuid
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.services import create_project, create_scenario
from app.infra.database.repos import SqlProjectRepository, SqlScenarioRepository


async def test_project_roundtrip(session: AsyncSession) -> None:
    """Проект сохраняется и читается обратно без потерь."""
    repo = SqlProjectRepository(session)
    project = create_project(uuid.uuid4(), "Магазин", "https://shop.example.com")
    await repo.add(project)
    session.expunge_all()
    assert await repo.get(project.id) == project
    assert await repo.get(uuid.uuid4()) is None


async def test_list_by_owner_returns_only_own_projects_newest_first(session: AsyncSession) -> None:
    """Пользователь видит только свои проекты, сначала новые."""
    repo = SqlProjectRepository(session)
    owner = uuid.uuid4()
    old = create_project(owner, "Старый", "https://a.example.com")
    new = create_project(owner, "Новый", "https://b.example.com")
    new.created_at = old.created_at + timedelta(seconds=1)
    for project in (old, new, create_project(uuid.uuid4(), "Чужой", "https://c.example.com")):
        await repo.add(project)
    assert [p.id for p in await repo.list_by_owner(owner)] == [new.id, old.id]


async def test_scenarios_are_deleted_with_project(session: AsyncSession) -> None:
    """При удалении проекта удаляются и его сценарии."""
    projects = SqlProjectRepository(session)
    scenarios = SqlScenarioRepository(session)
    project = create_project(uuid.uuid4(), "Магазин", "https://shop.example.com")
    await projects.add(project)
    first = create_scenario(project, "Каталог", "Открой каталог")
    second = create_scenario(project, "Корзина", "Добавь товар")
    second.created_at = first.created_at + timedelta(seconds=1)
    await scenarios.add(first)
    await scenarios.add(second)
    assert [s.id for s in await scenarios.list_by_project(project.id)] == [first.id, second.id]

    await scenarios.delete(first.id)
    assert await scenarios.get(first.id) is None

    await projects.delete(project.id)
    session.expunge_all()
    assert await projects.get(project.id) is None
    assert await scenarios.list_by_project(project.id) == []
