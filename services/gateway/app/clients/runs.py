import grpc

from app.clients.base import TIMEOUT_SECONDS, grpc_call
from app.grpc_gen import runs_pb2 as pb
from app.grpc_gen import runs_pb2_grpc


class RunsClient:
    def __init__(self, channel: grpc.aio.Channel) -> None:
        self._stub = runs_pb2_grpc.RunsServiceStub(channel)

    async def create_run(self, owner_id: str, project_id: str, scenario_id: str | None) -> pb.Run:
        """Ставит прогон в очередь через сервис runs."""
        request = pb.CreateRunRequest(
            owner_id=owner_id, project_id=project_id, scenario_id=scenario_id
        )
        return await grpc_call(self._stub.CreateRun(request, timeout=TIMEOUT_SECONDS))

    async def list_runs(self, owner_id: str, project_id: str) -> list[pb.Run]:
        """Получает прогоны проекта пользователя."""
        request = pb.ListRunsRequest(owner_id=owner_id, project_id=project_id)
        response = await grpc_call(self._stub.ListRuns(request, timeout=TIMEOUT_SECONDS))
        return list(response.runs)

    async def get_run(self, owner_id: str, run_id: str) -> pb.RunDetails:
        """Получает прогон пользователя со всеми результатами."""
        request = pb.RunRequest(owner_id=owner_id, run_id=run_id)
        return await grpc_call(self._stub.GetRun(request, timeout=TIMEOUT_SECONDS))

    async def cancel_run(self, owner_id: str, run_id: str) -> pb.Run:
        """Отменяет прогон пользователя."""
        request = pb.RunRequest(owner_id=owner_id, run_id=run_id)
        return await grpc_call(self._stub.CancelRun(request, timeout=TIMEOUT_SECONDS))
