import grpc

from app.clients.base import TIMEOUT_SECONDS, grpc_call
from app.grpc_gen import projects_pb2 as pb
from app.grpc_gen import projects_pb2_grpc


class ProjectsClient:
    def __init__(self, channel: grpc.aio.Channel) -> None:
        self._stub = projects_pb2_grpc.ProjectsServiceStub(channel)

    async def create_project(self, owner_id: str, name: str, base_url: str) -> pb.Project:
        """Создаёт проект через сервис projects."""
        request = pb.CreateProjectRequest(owner_id=owner_id, name=name, base_url=base_url)
        return await grpc_call(self._stub.CreateProject(request, timeout=TIMEOUT_SECONDS))

    async def list_projects(self, owner_id: str) -> list[pb.Project]:
        """Получает проекты пользователя."""
        request = pb.ListProjectsRequest(owner_id=owner_id)
        response = await grpc_call(self._stub.ListProjects(request, timeout=TIMEOUT_SECONDS))
        return list(response.projects)

    async def get_project(self, owner_id: str, project_id: str) -> pb.Project:
        """Получает один проект пользователя."""
        request = pb.ProjectRequest(owner_id=owner_id, project_id=project_id)
        return await grpc_call(self._stub.GetProject(request, timeout=TIMEOUT_SECONDS))

    async def delete_project(self, owner_id: str, project_id: str) -> None:
        """Удаляет проект пользователя."""
        request = pb.ProjectRequest(owner_id=owner_id, project_id=project_id)
        await grpc_call(self._stub.DeleteProject(request, timeout=TIMEOUT_SECONDS))

    async def create_scenario(
        self, owner_id: str, project_id: str, title: str, text: str
    ) -> pb.Scenario:
        """Добавляет сценарий в проект."""
        request = pb.CreateScenarioRequest(
            owner_id=owner_id, project_id=project_id, title=title, text=text
        )
        return await grpc_call(self._stub.CreateScenario(request, timeout=TIMEOUT_SECONDS))

    async def list_scenarios(self, owner_id: str, project_id: str) -> list[pb.Scenario]:
        """Получает сценарии проекта."""
        request = pb.ProjectRequest(owner_id=owner_id, project_id=project_id)
        response = await grpc_call(self._stub.ListScenarios(request, timeout=TIMEOUT_SECONDS))
        return list(response.scenarios)

    async def delete_scenario(self, owner_id: str, scenario_id: str) -> None:
        """Удаляет сценарий."""
        request = pb.ScenarioRequest(owner_id=owner_id, scenario_id=scenario_id)
        await grpc_call(self._stub.DeleteScenario(request, timeout=TIMEOUT_SECONDS))
