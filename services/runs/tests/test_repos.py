import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import FindingKind, RunStatus
from app.domain.services import (
    create_finding,
    create_generated_test,
    create_run,
    create_step,
    finish_run,
    start_run,
)
from app.infra.database.models import RunOrm
from app.infra.database.repos import (
    SqlFindingRepository,
    SqlGeneratedTestRepository,
    SqlRunRepository,
    SqlStepRepository,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)


async def test_run_roundtrip_and_status_update(session: AsyncSession) -> None:
    """Прогон сохраняется, а смена статуса записывается в базу."""
    repo = SqlRunRepository(session)
    run = create_run(uuid.uuid4(), uuid.uuid4(), uuid.uuid4())
    await repo.add(run)
    start_run(run, NOW)
    await repo.save(run)
    session.expunge_all()

    loaded = await repo.get(run.id, for_update=True)
    assert loaded == run
    assert loaded.status == RunStatus.RUNNING
    assert await repo.get(uuid.uuid4()) is None


async def test_list_by_project_filters_by_owner(session: AsyncSession) -> None:
    """В списке только прогоны этого проекта и этого пользователя, сначала новые."""
    repo = SqlRunRepository(session)
    owner, project = uuid.uuid4(), uuid.uuid4()
    old = create_run(owner, project, None)
    new = create_run(owner, project, None)
    new.created_at = old.created_at + timedelta(seconds=1)
    for run in (
        old,
        new,
        create_run(uuid.uuid4(), project, None),
        create_run(owner, uuid.uuid4(), None),
    ):
        await repo.add(run)
    assert [r.id for r in await repo.list_by_project(owner, project)] == [new.id, old.id]


async def test_results_are_saved_and_deleted_with_run(session: AsyncSession) -> None:
    """Шаги, баги и тест сохраняются и читаются, а удаление прогона удаляет их."""
    runs = SqlRunRepository(session)
    steps = SqlStepRepository(session)
    findings = SqlFindingRepository(session)
    tests = SqlGeneratedTestRepository(session)

    run = create_run(uuid.uuid4(), uuid.uuid4(), None)
    start_run(run, NOW)
    await runs.add(run)
    await steps.add(create_step(run, 1, "click", ok=False, error="не нашёл кнопку"))
    await steps.add(create_step(run, 0, "goto", ok=True, value="https://shop.example.com"))
    await findings.add(create_finding(run, FindingKind.HTTP_ERROR, "500 на /cart", step_index=1))
    finish_run(run, found_bugs=True, now=NOW)
    await runs.save(run)
    test = create_generated_test(run, "def test_cart(page): ...")
    await tests.save(test)
    test.verified = True
    await tests.save(test)
    session.expunge_all()

    assert [s.action for s in await steps.list_by_run(run.id)] == ["goto", "click"]
    assert [f.title for f in await findings.list_by_run(run.id)] == ["500 на /cart"]
    assert (await tests.get_by_run(run.id)).verified is True

    await session.execute(delete(RunOrm).where(RunOrm.id == run.id))
    session.expunge_all()
    assert await steps.list_by_run(run.id) == []
    assert await tests.get_by_run(run.id) is None
