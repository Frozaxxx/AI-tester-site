import logging

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, Path, Response, status

from app.dependencies import CurrentUserId, ProjectsClientDep, RunsClientDep
from app.exceptions import GatewayError
from app.schemas import RunCreate, RunDetailsResponse, RunResponse
from app.screenshots import screenshot_store

router = APIRouter(tags=["Прогоны"])
logger = logging.getLogger(__name__)


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
    details = RunDetailsResponse.from_proto(await runs.get_run(user_id, run_id))
    if details.steps:
        try:
            if store := screenshot_store():
                indices = await store.list_steps(details.run.id)
                for step in details.steps:
                    step.has_screenshot = step.index in indices
        except (BotoCoreError, ClientError) as error:
            logger.warning(
                "Снимки прогона %s недоступны (%s)", details.run.id, type(error).__name__
            )
    return details


@router.get("/runs/{run_id}/screenshots/{index}", summary="Скриншот шага")
async def get_screenshot(
    run_id: str, user_id: CurrentUserId, runs: RunsClientDep, index: int = Path(ge=0)
) -> Response:
    details = await runs.get_run(user_id, run_id)
    if any(step.index == index for step in details.steps):
        try:
            if store := screenshot_store():
                if image := await store.get(details.run.id, index):
                    return Response(
                        image,
                        media_type="image/jpeg",
                        headers={
                            "Cache-Control": "private, no-store",
                            "X-Content-Type-Options": "nosniff",
                        },
                    )
        except (BotoCoreError, ClientError) as error:
            logger.warning(
                "Снимок прогона %s недоступен (%s)", details.run.id, type(error).__name__
            )
            raise GatewayError(
                503, "SCREENSHOT_UNAVAILABLE", "Скриншот временно недоступен"
            ) from None
    raise GatewayError(404, "SCREENSHOT_NOT_FOUND", "Скриншот не найден")


@router.post("/runs/{run_id}/cancel", summary="Отменить прогон")
async def cancel_run(run_id: str, user_id: CurrentUserId, runs: RunsClientDep) -> RunResponse:
    """Отменяет прогон, который ещё не завершён."""
    return RunResponse.from_proto(await runs.cancel_run(user_id, run_id))
