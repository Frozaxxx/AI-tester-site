from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from functools import wraps
from http import HTTPStatus

import grpc
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.application.services import ProjectService
from app.domain.entities import Project, Scenario
from app.domain.exceptions import DomainError
from app.grpc_gen import projects_pb2, projects_pb2_grpc
from app.infra.database.repos import SqlProjectRepository, SqlScenarioRepository

GRPC_STATUS = {
    HTTPStatus.NOT_FOUND: grpc.StatusCode.NOT_FOUND,
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


def _project(project: Project) -> projects_pb2.Project:
    """Переводит проект в proto-сообщение."""
    return projects_pb2.Project(
        id=str(project.id),
        name=project.name,
        base_url=project.base_url,
        created_at=int(project.created_at.timestamp()),
    )


def _scenario(scenario: Scenario) -> projects_pb2.Scenario:
    """Переводит сценарий в proto-сообщение."""
    return projects_pb2.Scenario(
        id=str(scenario.id),
        project_id=str(scenario.project_id),
        title=scenario.title,
        text=scenario.text,
        created_at=int(scenario.created_at.timestamp()),
    )


class ProjectsServicer(projects_pb2_grpc.ProjectsServiceServicer):
    def __init__(self, session_factory: async_sessionmaker, allow_internal_urls: bool) -> None:
        self._session_factory = session_factory
        self._allow_internal_urls = allow_internal_urls

    @asynccontextmanager
    async def _service(self) -> AsyncIterator[ProjectService]:
        """Открывает сессию базы и собирает сервис проектов на один вызов."""
        async with self._session_factory() as session:
            yield ProjectService(
                session=session,
                project_repo=SqlProjectRepository(session),
                scenario_repo=SqlScenarioRepository(session),
                allow_internal_urls=self._allow_internal_urls,
            )

    @handle_errors
    async def CreateProject(self, request, context):
        """Создаёт проект пользователя."""
        async with self._service() as service:
            project = await service.create_project(request.owner_id, request.name, request.base_url)
        return _project(project)

    @handle_errors
    async def ListProjects(self, request, context):
        """Возвращает проекты пользователя."""
        async with self._service() as service:
            projects = await service.list_projects(request.owner_id)
        return projects_pb2.ProjectList(projects=[_project(p) for p in projects])

    @handle_errors
    async def GetProject(self, request, context):
        """Возвращает один проект пользователя."""
        async with self._service() as service:
            project = await service.get_project(request.owner_id, request.project_id)
        return _project(project)

    @handle_errors
    async def DeleteProject(self, request, context):
        """Удаляет проект пользователя вместе со сценариями."""
        async with self._service() as service:
            await service.delete_project(request.owner_id, request.project_id)
        return projects_pb2.Empty()

    @handle_errors
    async def CreateScenario(self, request, context):
        """Добавляет сценарий в проект."""
        async with self._service() as service:
            scenario = await service.create_scenario(
                request.owner_id, request.project_id, request.title, request.text
            )
        return _scenario(scenario)

    @handle_errors
    async def ListScenarios(self, request, context):
        """Возвращает сценарии проекта."""
        async with self._service() as service:
            scenarios = await service.list_scenarios(request.owner_id, request.project_id)
        return projects_pb2.ScenarioList(scenarios=[_scenario(s) for s in scenarios])

    @handle_errors
    async def DeleteScenario(self, request, context):
        """Удаляет сценарий из проекта."""
        async with self._service() as service:
            await service.delete_scenario(request.owner_id, request.scenario_id)
        return projects_pb2.Empty()
