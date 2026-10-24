import grpc

from app.domain.entities import ActionResult, PageProblem
from app.domain.exceptions import RunCancelledError
from app.grpc_gen import runs_pb2 as pb
from app.grpc_gen import runs_pb2_grpc

TIMEOUT_SECONDS = 10


class RunsClient:
    def __init__(self, channel: grpc.aio.Channel) -> None:
        self._stub = runs_pb2_grpc.RunsServiceStub(channel)

    async def claim(self) -> pb.ClaimedRun | None:
        """Берёт следующий прогон из очереди или возвращает None, если очередь пуста."""
        claimed = await self._stub.ClaimRun(pb.Empty(), timeout=TIMEOUT_SECONDS)
        return claimed if claimed.HasField("run") else None

    async def add_step(self, run_id: str, index: int, action, result: ActionResult) -> None:
        """Записывает выполненное действие агента в прогон."""
        request = pb.AddStepRequest(
            run_id=run_id,
            index=index,
            action=action.name,
            ok=result.ok,
            locator=action.locator,
            value=action.value,
            error=result.error,
        )
        await self._call(self._stub.AddStep(request, timeout=TIMEOUT_SECONDS))

    async def add_finding(self, run_id: str, problem: PageProblem, step_index: int) -> None:
        """Записывает найденную на странице проблему как баг прогона."""
        request = pb.AddFindingRequest(
            run_id=run_id,
            kind=problem.kind,
            title=problem.title,
            details=problem.details,
            step_index=step_index,
        )
        await self._call(self._stub.AddFinding(request, timeout=TIMEOUT_SECONDS))

    async def add_tokens(self, run_id: str, count: int) -> None:
        """Прибавляет к прогону потраченные токены LLM."""
        request = pb.AddTokensRequest(run_id=run_id, count=count)
        await self._call(self._stub.AddTokens(request, timeout=TIMEOUT_SECONDS))

    async def finish(self, run_id: str) -> None:
        """Завершает прогон, итог сервис runs считает сам по записанным багам."""
        await self._call(
            self._stub.FinishRun(pb.RunnerRequest(run_id=run_id), timeout=TIMEOUT_SECONDS)
        )

    async def crash(self, run_id: str) -> None:
        """Отмечает, что прогон сломался из-за раннера, а не из-за сайта."""
        await self._call(
            self._stub.CrashRun(pb.RunnerRequest(run_id=run_id), timeout=TIMEOUT_SECONDS)
        )

    async def save_test(self, run_id: str, code: str) -> None:
        """Сохраняет сгенерированный Playwright-тест прогона."""
        request = pb.SaveGeneratedTestRequest(run_id=run_id, code=code)
        await self._call(self._stub.SaveGeneratedTest(request, timeout=TIMEOUT_SECONDS))

    async def _call(self, call) -> None:
        """Выполняет вызов и превращает отказ из-за статуса прогона в отмену прогона."""
        try:
            await call
        except grpc.aio.AioRpcError as exc:
            if exc.code() == grpc.StatusCode.FAILED_PRECONDITION:
                raise RunCancelledError from None
            raise
