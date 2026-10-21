from fastapi import APIRouter, status

from app.dependencies import CurrentUserId, ProjectsClientDep, RunsClientDep
from app.exceptions import GatewayError
from app.schemas import RunCreate, RunDetailsResponse, RunResponse

router = APIRouter(tags=["Прогоны"])


async def _ensure_scenario(
    projects: ProjectsClientDep, user_id: str, project_id: str, scenario_id: str
) -> None:
    """Проверяет, что сценарий лежит в этом проекте пользователя."""
    scenarios = await projects.list_scenarios(user_id, project_id)
    if all(scenario.id != scenario_id for scenario in scenarios):
        raise GatewayError(status.HTTP_404_NOT_FOUND, "SCENARIO_NOT_FOUND", "Сценарий не найден")


@router.post(
    "/projects/{project_id}/runs",
    status_code=status.HTTP_201_CREATED,
    summary="Запустить прогон",
)
async def create_run(
    project_id: str,
    body: RunCreate,
    user_id: CurrentUserId,
    projects: ProjectsClientDep,
    runs: RunsClientDep,
) -> RunResponse:
    """Ставит в очередь прогон проекта пользователя, при желании по одному сценарию."""
    await projects.get_project(user_id, project_id)
    scenario_id = str(body.scenario_id) if body.scenario_id else None
    if scenario_id is not None:
        await _ensure_scenario(projects, user_id, project_id, scenario_id)
    run = await runs.create_run(user_id, project_id, scenario_id)
    return RunResponse.from_proto(run)


@router.get("/projects/{project_id}/runs", summary="Прогоны проекта")
async def list_runs(
    project_id: str, user_id: CurrentUserId, projects: ProjectsClientDep, runs: RunsClientDep
) -> list[RunResponse]:
    """Возвращает прогоны проекта пользователя, сначала новые."""
    await projects.get_project(user_id, project_id)
    return [RunResponse.from_proto(run) for run in await runs.list_runs(user_id, project_id)]


@router.get("/runs/{run_id}", summary="Прогон с результатами")
async def get_run(run_id: str, user_id: CurrentUserId, runs: RunsClientDep) -> RunDetailsResponse:
    """Возвращает прогон со всеми шагами, багами и сгенерированным тестом."""
    return RunDetailsResponse.from_proto(await runs.get_run(user_id, run_id))


@router.post("/runs/{run_id}/cancel", summary="Отменить прогон")
async def cancel_run(run_id: str, user_id: CurrentUserId, runs: RunsClientDep) -> RunResponse:
    """Отменяет прогон, который ещё не завершён."""
    return RunResponse.from_proto(await runs.cancel_run(user_id, run_id))
