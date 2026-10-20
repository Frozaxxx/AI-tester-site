from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import datetime
from functools import wraps
from http import HTTPStatus

import grpc
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.application.dtos import RunDetails
from app.application.services import RunService
from app.domain.entities import Finding, GeneratedTest, Run, Step
from app.domain.exceptions import DomainError
from app.grpc_gen import runs_pb2, runs_pb2_grpc
from app.infra.database.repos import (
    SqlFindingRepository,
    SqlGeneratedTestRepository,
    SqlRunRepository,
    SqlStepRepository,
)

GRPC_STATUS = {
    HTTPStatus.NOT_FOUND: grpc.StatusCode.NOT_FOUND,
    HTTPStatus.CONFLICT: grpc.StatusCode.FAILED_PRECONDITION,
    HTTPStatus.UNPROCESSABLE_ENTITY: grpc.StatusCode.INVALID_ARGUMENT,
}


def handle_errors[**P, R](method: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
    """Превращает доменные ошибки в gRPC-ошибки с кодом в метаданных."""

    @wraps(method)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        context: grpc.aio.ServicerContext = args[2]  # type: ignore[assignment]
        try:
            return await method(*args, **kwargs)
        except DomainError as exc:
            code = GRPC_STATUS.get(HTTPStatus(exc.status_code), grpc.StatusCode.INVALID_ARGUMENT)
            await context.abort(
                code, exc.message, trailing_metadata=(("error-code", exc.error_code),)
            )

    return wrapper


def _ts(value: datetime | None) -> int | None:
    """Переводит дату в unix-время в секундах."""
    return int(value.timestamp()) if value is not None else None


def _run(run: Run) -> runs_pb2.Run:
    """Переводит прогон в proto-сообщение."""
    return runs_pb2.Run(
        id=str(run.id),
        project_id=str(run.project_id),
        scenario_id=str(run.scenario_id) if run.scenario_id else None,
        status=run.status,
        tokens_used=run.tokens_used,
        created_at=_ts(run.created_at),
        started_at=_ts(run.started_at),
        finished_at=_ts(run.finished_at),
    )


def _step(step: Step) -> runs_pb2.Step:
    """Переводит шаг прогона в proto-сообщение."""
    return runs_pb2.Step(
        index=step.index,
        action=step.action,
        ok=step.ok,
        locator=step.locator,
        value=step.value,
        error=step.error,
        created_at=_ts(step.created_at),
    )


def _finding(finding: Finding) -> runs_pb2.Finding:
    """Переводит найденный баг в proto-сообщение."""
    return runs_pb2.Finding(
        id=str(finding.id),
        kind=finding.kind,
        title=finding.title,
        details=finding.details,
        step_index=finding.step_index,
        reproduced=finding.reproduced,
        created_at=_ts(finding.created_at),
    )


def _test(test: GeneratedTest) -> runs_pb2.GeneratedTest:
    """Переводит сгенерированный тест в proto-сообщение."""
    return runs_pb2.GeneratedTest(
        code=test.code, verified=test.verified, created_at=_ts(test.created_at)
    )


def _details(details: RunDetails) -> runs_pb2.RunDetails:
    """Собирает proto-сообщение с прогоном и всеми его результатами."""
    return runs_pb2.RunDetails(
        run=_run(details.run),
        steps=[_step(step) for step in details.steps],
        findings=[_finding(finding) for finding in details.findings],
        test=_test(details.test) if details.test else None,
    )


def _optional(request, field: str) -> str | None:
    """Возвращает значение optional-поля запроса или None, если поле не передали."""
    return getattr(request, field) if request.HasField(field) else None


class RunsServicer(runs_pb2_grpc.RunsServiceServicer):
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    @asynccontextmanager
    async def _service(self) -> AsyncIterator[RunService]:
        """Открывает сессию базы и собирает сервис прогонов на один вызов."""
        async with self._session_factory() as session:
            yield RunService(
                session=session,
                run_repo=SqlRunRepository(session),
                step_repo=SqlStepRepository(session),
                finding_repo=SqlFindingRepository(session),
                test_repo=SqlGeneratedTestRepository(session),
            )

    @handle_errors
    async def CreateRun(self, request, context):
        """Ставит прогон проекта в очередь."""
        async with self._service() as service:
            run = await service.create_run(
                request.owner_id, request.project_id, _optional(request, "scenario_id")
            )
        return _run(run)

    @handle_errors
    async def ListRuns(self, request, context):
        """Возвращает прогоны проекта пользователя."""
        async with self._service() as service:
            runs = await service.list_runs(request.owner_id, request.project_id)
        return runs_pb2.RunList(runs=[_run(run) for run in runs])

    @handle_errors
    async def GetRun(self, request, context):
        """Возвращает прогон пользователя со всеми результатами."""
        async with self._service() as service:
            details = await service.get_run(request.owner_id, request.run_id)
        return _details(details)

    @handle_errors
    async def CancelRun(self, request, context):
        """Отменяет прогон пользователя."""
        async with self._service() as service:
            run = await service.cancel_run(request.owner_id, request.run_id)
        return _run(run)

    @handle_errors
    async def StartRun(self, request, context):
        """Отмечает, что раннер взял прогон в работу."""
        async with self._service() as service:
            run = await service.start_run(request.run_id)
        return _run(run)

    @handle_errors
    async def AddStep(self, request, context):
        """Записывает действие агента."""
        async with self._service() as service:
            step = await service.add_step(
                request.run_id,
                request.index,
                request.action,
                request.ok,
                _optional(request, "locator"),
                _optional(request, "value"),
                _optional(request, "error"),
            )
        return _step(step)

    @handle_errors
    async def AddFinding(self, request, context):
        """Записывает найденный баг."""
        async with self._service() as service:
            finding = await service.add_finding(
                request.run_id,
                request.kind,
                request.title,
                request.details,
                _optional(request, "step_index"),
            )
        return _finding(finding)

    @handle_errors
    async def AddTokens(self, request, context):
        """Прибавляет к прогону потраченные токены LLM."""
        async with self._service() as service:
            run = await service.add_tokens(request.run_id, request.count)
        return _run(run)

    @handle_errors
    async def FinishRun(self, request, context):
        """Завершает прогон по итогам записанных багов."""
        async with self._service() as service:
            run = await service.finish_run(request.run_id)
        return _run(run)

    @handle_errors
    async def CrashRun(self, request, context):
        """Отмечает, что прогон сломался сам."""
        async with self._service() as service:
            run = await service.crash_run(request.run_id)
        return _run(run)

    @handle_errors
    async def SaveGeneratedTest(self, request, context):
        """Сохраняет Playwright-тест, собранный из прогона."""
        async with self._service() as service:
            test = await service.save_generated_test(request.run_id, request.code)
        return _test(test)
