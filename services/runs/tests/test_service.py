import uuid
from datetime import timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services import RunService
from app.domain.entities import RunStatus
from app.domain.exceptions import (
    InvalidRunStateError,
    RunNotFoundError,
    TooManyActiveRunsError,
    ValidationError,
)
from app.infra.database.repos import (
    SqlFindingRepository,
    SqlGeneratedTestRepository,
    SqlRunRepository,
    SqlStepRepository,
)

OWNER = str(uuid.uuid4())
STRANGER = str(uuid.uuid4())
PROJECT = str(uuid.uuid4())


@pytest.fixture
def service(session: AsyncSession) -> RunService:
    """Собирает сервис прогонов поверх тестовой базы."""
    return RunService(
        session,
        SqlRunRepository(session),
        SqlStepRepository(session),
        SqlFindingRepository(session),
        SqlGeneratedTestRepository(session),
    )


async def test_full_run_flow(service: RunService) -> None:
    """Прогон проходит путь от очереди до сохранённого теста, а владелец видит все результаты."""
    run = await service.create_run(OWNER, PROJECT)
    run_id = str(run.id)
    assert run.status == RunStatus.QUEUED

    await service.start_run(run_id)
    await service.add_step(run_id, 0, "goto", ok=True, value="https://shop.example.com")
    await service.add_step(run_id, 1, "click", ok=False, error="кнопка не нажимается")
    await service.add_finding(run_id, "assertion", "Кнопка «В корзину» не работает", step_index=1)
    await service.add_tokens(run_id, 1500)
    finished = await service.finish_run(run_id)
    assert finished.status == RunStatus.FAILED
    await service.save_generated_test(run_id, "def test_cart(page): ...")
    await service.save_generated_test(run_id, "def test_cart(page): pass")

    details = await service.get_run(OWNER, run_id)
    assert details.run.tokens_used == 1500
    assert [s.action for s in details.steps] == ["goto", "click"]
    assert details.findings[0].step_index == 1
    assert details.test.code == "def test_cart(page): pass"
    assert [r.id for r in await service.list_runs(OWNER, PROJECT)] == [run.id]


async def test_stranger_does_not_see_run(service: RunService) -> None:
    """Чужой пользователь не видит прогон и не может его отменить."""
    run = await service.create_run(OWNER, PROJECT)
    assert await service.list_runs(STRANGER, PROJECT) == []
    with pytest.raises(RunNotFoundError):
        await service.get_run(STRANGER, str(run.id))
    with pytest.raises(RunNotFoundError):
        await service.cancel_run(STRANGER, str(run.id))


async def test_cancelled_run_stops_runner(service: RunService) -> None:
    """После отмены раннер не может записывать шаги и завершать прогон."""
    run_id = str((await service.create_run(OWNER, PROJECT)).id)
    await service.start_run(run_id)
    cancelled = await service.cancel_run(OWNER, run_id)
    assert cancelled.status == RunStatus.CANCELLED
    with pytest.raises(InvalidRunStateError):
        await service.add_step(run_id, 0, "click", ok=True)
    with pytest.raises(InvalidRunStateError):
        await service.finish_run(run_id)
    with pytest.raises(InvalidRunStateError):
        await service.cancel_run(OWNER, run_id)


async def test_duplicate_step_index_is_rejected(service: RunService) -> None:
    """Один и тот же номер шага нельзя записать дважды."""
    run_id = str((await service.create_run(OWNER, PROJECT)).id)
    await service.start_run(run_id)
    await service.add_step(run_id, 0, "goto", ok=True)
    with pytest.raises(ValidationError):
        await service.add_step(run_id, 0, "click", ok=True)
    await service.add_step(run_id, 1, "click", ok=True)
    assert len((await service.get_run(OWNER, run_id)).steps) == 2


@pytest.mark.parametrize("bad_id", ["not-a-uuid", "", str(uuid.uuid4())])
async def test_bad_or_missing_run_id(service: RunService, bad_id: str) -> None:
    """Кривой или несуществующий id прогона даёт «не найдено»."""
    with pytest.raises(RunNotFoundError):
        await service.get_run(OWNER, bad_id)
    with pytest.raises(RunNotFoundError):
        await service.start_run(bad_id)


async def test_bad_project_id_is_rejected(service: RunService) -> None:
    """Кривой id проекта при создании прогона даёт ошибку валидации."""
    with pytest.raises(ValidationError):
        await service.create_run(OWNER, "not-a-uuid")


async def test_finish_status_depends_on_recorded_findings(service: RunService) -> None:
    """Итог прогона определяется записанными багами, а не словами раннера."""
    clean_id = str((await service.create_run(OWNER, PROJECT)).id)
    await service.start_run(clean_id)
    assert (await service.finish_run(clean_id)).status == RunStatus.PASSED

    buggy_id = str((await service.create_run(OWNER, PROJECT)).id)
    await service.start_run(buggy_id)
    await service.add_finding(buggy_id, "js_error", "Ошибка в консоли")
    assert (await service.finish_run(buggy_id)).status == RunStatus.FAILED


async def test_unknown_finding_kind_is_rejected(service: RunService) -> None:
    """Неизвестный тип бага даёт ошибку валидации, а не падение базы."""
    run_id = str((await service.create_run(OWNER, PROJECT)).id)
    await service.start_run(run_id)
    with pytest.raises(ValidationError):
        await service.add_finding(run_id, "nonsense", "Баг")


async def test_active_runs_limit(service: RunService) -> None:
    """Больше трёх незавершённых прогонов разом запустить нельзя, а отмена освобождает место."""
    runs = [await service.create_run(OWNER, PROJECT) for _ in range(3)]
    with pytest.raises(TooManyActiveRunsError):
        await service.create_run(OWNER, PROJECT)
    assert await service.create_run(STRANGER, PROJECT)

    await service.cancel_run(OWNER, str(runs[0].id))
    assert await service.create_run(OWNER, PROJECT)


async def test_claim_run_takes_oldest_queued(service: RunService) -> None:
    """Раннер получает самый старый прогон из очереди уже в статусе «идёт»."""
    assert await service.claim_run() is None
    first = await service.create_run(OWNER, PROJECT)
    second = await service.create_run(OWNER, PROJECT)
    second.created_at = first.created_at
    claimed = await service.claim_run()
    assert claimed.id == first.id and claimed.status == RunStatus.RUNNING
    assert (await service.claim_run()).id == second.id
    assert await service.claim_run() is None


async def test_stale_runs_are_expired(service: RunService, session: AsyncSession) -> None:
    """Прогон, который идёт дольше 15 минут, переводится в ошибку, а свежий не трогается."""
    stale_id = str((await service.create_run(OWNER, PROJECT)).id)
    fresh_id = str((await service.create_run(OWNER, PROJECT)).id)
    stale = await service.start_run(stale_id)
    await service.start_run(fresh_id)
    stale.started_at -= timedelta(minutes=16)
    await SqlRunRepository(session).save(stale)
    await session.commit()

    assert await service.expire_stale_runs() == 1
    assert (await service.get_run(OWNER, stale_id)).run.status == RunStatus.ERROR
    assert (await service.get_run(OWNER, fresh_id)).run.status == RunStatus.RUNNING
    assert await service.expire_stale_runs() == 0
