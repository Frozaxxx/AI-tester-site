import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos import RunDetails
from app.application.repos import (
    FindingRepository,
    GeneratedTestRepository,
    RunRepository,
    StepRepository,
)
from app.domain.entities import Finding, FindingKind, GeneratedTest, Run, Step, now
from app.domain.exceptions import RunNotFoundError, ValidationError
from app.domain.services import (
    add_tokens,
    cancel_run,
    crash_run,
    create_finding,
    create_generated_test,
    create_run,
    create_step,
    ensure_owner,
    finish_run,
    start_run,
)


class RunService:
    def __init__(
        self,
        session: AsyncSession,
        run_repo: RunRepository,
        step_repo: StepRepository,
        finding_repo: FindingRepository,
        test_repo: GeneratedTestRepository,
    ) -> None:
        self._session = session
        self._run_repo = run_repo
        self._step_repo = step_repo
        self._finding_repo = finding_repo
        self._test_repo = test_repo

    async def create_run(
        self, owner_id: str, project_id: str, scenario_id: str | None = None
    ) -> Run:
        """Ставит в очередь прогон проекта, владельца которого уже проверил gateway."""
        run = create_run(
            _parse_id(owner_id, ValidationError),
            _parse_id(project_id, ValidationError),
            _parse_id(scenario_id, ValidationError) if scenario_id else None,
        )
        await self._run_repo.add(run)
        await self._session.commit()
        return run

    async def list_runs(self, owner_id: str, project_id: str) -> list[Run]:
        """Возвращает прогоны проекта пользователя, сначала новые."""
        return await self._run_repo.list_by_project(
            _parse_id(owner_id, ValidationError), _parse_id(project_id, ValidationError)
        )

    async def get_run(self, owner_id: str, run_id: str) -> RunDetails:
        """Возвращает прогон пользователя вместе с шагами, багами и сгенерированным тестом."""
        run = await self._own_run(owner_id, run_id)
        return RunDetails(
            run=run,
            steps=await self._step_repo.list_by_run(run.id),
            findings=await self._finding_repo.list_by_run(run.id),
            test=await self._test_repo.get_by_run(run.id),
        )

    async def cancel_run(self, owner_id: str, run_id: str) -> Run:
        """Отменяет незавершённый прогон пользователя."""
        run = await self._own_run(owner_id, run_id, for_update=True)
        cancel_run(run, now())
        return await self._save(run)

    async def start_run(self, run_id: str) -> Run:
        """Отмечает, что раннер взял прогон в работу."""
        run = await self._locked_run(run_id)
        start_run(run, now())
        return await self._save(run)

    async def add_step(
        self,
        run_id: str,
        index: int,
        action: str,
        ok: bool,
        locator: str | None = None,
        value: str | None = None,
        error: str | None = None,
    ) -> Step:
        """Записывает действие агента в идущий прогон."""
        run = await self._locked_run(run_id)
        step = create_step(run, index, action, ok, locator, value, error)
        await self._step_repo.add(step)
        await self._session.commit()
        return step

    async def add_finding(
        self,
        run_id: str,
        kind: FindingKind,
        title: str,
        details: str = "",
        step_index: int | None = None,
    ) -> Finding:
        """Записывает найденный баг в идущий прогон."""
        run = await self._locked_run(run_id)
        finding = create_finding(run, kind, title, details, step_index)
        await self._finding_repo.add(finding)
        await self._session.commit()
        return finding

    async def add_tokens(self, run_id: str, count: int) -> Run:
        """Прибавляет к прогону потраченные токены LLM."""
        run = await self._locked_run(run_id)
        add_tokens(run, count)
        return await self._save(run)

    async def finish_run(self, run_id: str, found_bugs: bool) -> Run:
        """Завершает прогон: с багами он упал, без багов прошёл."""
        run = await self._locked_run(run_id)
        finish_run(run, found_bugs, now())
        return await self._save(run)

    async def crash_run(self, run_id: str) -> Run:
        """Отмечает, что прогон сломался сам, а не из-за сайта."""
        run = await self._locked_run(run_id)
        crash_run(run, now())
        return await self._save(run)

    async def save_generated_test(self, run_id: str, code: str) -> GeneratedTest:
        """Сохраняет Playwright-тест, собранный из шагов завершённого прогона."""
        run = await self._locked_run(run_id)
        test = create_generated_test(run, code)
        existing = await self._test_repo.get_by_run(run.id)
        if existing is not None:
            test.id = existing.id
        await self._test_repo.save(test)
        await self._session.commit()
        return test

    async def _own_run(self, owner_id: str, run_id: str, for_update: bool = False) -> Run:
        """Находит прогон, только если он принадлежит пользователю."""
        run = await self._run_repo.get(_parse_id(run_id, RunNotFoundError), for_update)
        return ensure_owner(run, _parse_id(owner_id, ValidationError))

    async def _locked_run(self, run_id: str) -> Run:
        """Находит прогон и блокирует его, чтобы параллельные вызовы не испортили статус."""
        run = await self._run_repo.get(_parse_id(run_id, RunNotFoundError), for_update=True)
        if run is None:
            raise RunNotFoundError
        return run

    async def _save(self, run: Run) -> Run:
        """Сохраняет прогон и фиксирует транзакцию."""
        await self._run_repo.save(run)
        await self._session.commit()
        return run


def _parse_id(raw: str, error: type[Exception]) -> uuid.UUID:
    """Превращает строку в UUID, а кривой id превращает в переданную ошибку."""
    try:
        return uuid.UUID(raw)
    except ValueError:
        raise error from None
