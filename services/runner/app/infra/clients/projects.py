import grpc

from app.grpc_gen import projects_pb2 as pb
from app.grpc_gen import projects_pb2_grpc

TIMEOUT_SECONDS = 10


class ProjectsClient:
    def __init__(self, channel: grpc.aio.Channel) -> None:
        self._stub = projects_pb2_grpc.ProjectsServiceStub(channel)

    async def get_project(self, owner_id: str, project_id: str) -> pb.Project:
        """Получает проект владельца прогона."""
        request = pb.ProjectRequest(owner_id=owner_id, project_id=project_id)
        return await self._stub.GetProject(request, timeout=TIMEOUT_SECONDS)

    async def list_scenarios(self, owner_id: str, project_id: str) -> list[pb.Scenario]:
        """Получает сценарии проекта владельца прогона."""
        request = pb.ProjectRequest(owner_id=owner_id, project_id=project_id)
        response = await self._stub.ListScenarios(request, timeout=TIMEOUT_SECONDS)
        return list(response.scenarios)
