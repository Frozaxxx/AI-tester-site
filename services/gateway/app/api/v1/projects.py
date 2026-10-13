from fastapi import APIRouter, status

from app.dependencies import CurrentUserId, ProjectsClientDep
from app.schemas import ProjectCreate, ProjectResponse, ScenarioCreate, ScenarioResponse

router = APIRouter(tags=["Проекты"])


@router.post("/projects", status_code=status.HTTP_201_CREATED, summary="Создать проект")
async def create_project(
    body: ProjectCreate, user_id: CurrentUserId, projects: ProjectsClientDep
) -> ProjectResponse:
    """Создаёт проект текущего пользователя."""
    project = await projects.create_project(user_id, body.name, body.base_url)
    return ProjectResponse.from_proto(project)


@router.get("/projects", summary="Мои проекты")
async def list_projects(
    user_id: CurrentUserId, projects: ProjectsClientDep
) -> list[ProjectResponse]:
    """Возвращает проекты текущего пользователя."""
    return [ProjectResponse.from_proto(p) for p in await projects.list_projects(user_id)]


@router.get("/projects/{project_id}", summary="Проект")
async def get_project(
    project_id: str, user_id: CurrentUserId, projects: ProjectsClientDep
) -> ProjectResponse:
    """Возвращает один проект текущего пользователя."""
    return ProjectResponse.from_proto(await projects.get_project(user_id, project_id))


@router.delete(
    "/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить проект"
)
async def delete_project(
    project_id: str, user_id: CurrentUserId, projects: ProjectsClientDep
) -> None:
    """Удаляет проект вместе со сценариями."""
    await projects.delete_project(user_id, project_id)


@router.post(
    "/projects/{project_id}/scenarios",
    status_code=status.HTTP_201_CREATED,
    summary="Добавить сценарий",
)
async def create_scenario(
    project_id: str, body: ScenarioCreate, user_id: CurrentUserId, projects: ProjectsClientDep
) -> ScenarioResponse:
    """Добавляет сценарий в проект."""
    scenario = await projects.create_scenario(user_id, project_id, body.title, body.text)
    return ScenarioResponse.from_proto(scenario)


@router.get("/projects/{project_id}/scenarios", summary="Сценарии проекта")
async def list_scenarios(
    project_id: str, user_id: CurrentUserId, projects: ProjectsClientDep
) -> list[ScenarioResponse]:
    """Возвращает сценарии проекта."""
    scenarios = await projects.list_scenarios(user_id, project_id)
    return [ScenarioResponse.from_proto(s) for s in scenarios]


@router.delete(
    "/scenarios/{scenario_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить сценарий"
)
async def delete_scenario(
    scenario_id: str, user_id: CurrentUserId, projects: ProjectsClientDep
) -> None:
    """Удаляет сценарий."""
    await projects.delete_scenario(user_id, scenario_id)
