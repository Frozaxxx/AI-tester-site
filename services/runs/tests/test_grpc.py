import uuid

import grpc
import pytest

from app.grpc_gen import runs_pb2 as pb

OWNER = str(uuid.uuid4())
STRANGER = str(uuid.uuid4())
PROJECT = str(uuid.uuid4())


async def expect_error(call, code: grpc.StatusCode) -> str:
    """Проверяет, что вызов упал с нужным gRPC-кодом, и возвращает код ошибки из метаданных."""
    with pytest.raises(grpc.aio.AioRpcError) as info:
        await call
    assert info.value.code() == code
    return dict(info.value.trailing_metadata())["error-code"]


async def test_full_run_over_grpc(stub) -> None:
    """Через gRPC проходит весь путь прогона: очередь, шаги, баг, итог и тест."""
    run = await stub.CreateRun(pb.CreateRunRequest(owner_id=OWNER, project_id=PROJECT))
    assert run.status == "queued" and not run.HasField("scenario_id")
    assert not run.HasField("started_at")
    ref = pb.RunnerRequest(run_id=run.id)

    assert (await stub.StartRun(ref)).status == "running"
    await stub.AddStep(
        pb.AddStepRequest(run_id=run.id, index=0, action="goto", ok=True, value="https://a.com")
    )
    await stub.AddStep(
        pb.AddStepRequest(run_id=run.id, index=1, action="click", ok=False, error="нет кнопки")
    )
    await stub.AddFinding(
        pb.AddFindingRequest(run_id=run.id, kind="assertion", title="Кнопка пропала", step_index=1)
    )
    await stub.AddTokens(pb.AddTokensRequest(run_id=run.id, count=700))
    finished = await stub.FinishRun(ref)
    assert finished.status == "failed" and finished.HasField("finished_at")
    await stub.SaveGeneratedTest(
        pb.SaveGeneratedTestRequest(run_id=run.id, code="def test(page): ...")
    )

    details = await stub.GetRun(pb.RunRequest(owner_id=OWNER, run_id=run.id))
    assert details.run.tokens_used == 700
    assert [s.action for s in details.steps] == ["goto", "click"]
    assert details.steps[0].value == "https://a.com" and not details.steps[0].HasField("error")
    assert details.findings[0].step_index == 1
    assert details.test.code == "def test(page): ..."

    listed = await stub.ListRuns(pb.ListRunsRequest(owner_id=OWNER, project_id=PROJECT))
    assert [r.id for r in listed.runs] == [run.id]


async def test_run_without_results_has_no_test(stub) -> None:
    """У нового прогона нет сгенерированного теста, а сценарий передаётся как есть."""
    scenario = str(uuid.uuid4())
    run = await stub.CreateRun(
        pb.CreateRunRequest(owner_id=OWNER, project_id=PROJECT, scenario_id=scenario)
    )
    assert run.scenario_id == scenario
    details = await stub.GetRun(pb.RunRequest(owner_id=OWNER, run_id=run.id))
    assert not details.HasField("test") and not details.steps


async def test_errors_map_to_grpc_codes(stub) -> None:
    """Чужой прогон даёт NOT_FOUND, неверный статус FAILED_PRECONDITION, мусор INVALID_ARGUMENT."""
    run = await stub.CreateRun(pb.CreateRunRequest(owner_id=OWNER, project_id=PROJECT))

    code = await expect_error(
        stub.GetRun(pb.RunRequest(owner_id=STRANGER, run_id=run.id)), grpc.StatusCode.NOT_FOUND
    )
    assert code == "RUN_NOT_FOUND"
    step = pb.AddStepRequest(run_id=run.id, index=0, action="click", ok=True)
    code = await expect_error(stub.AddStep(step), grpc.StatusCode.FAILED_PRECONDITION)
    assert code == "INVALID_RUN_STATE"

    await stub.StartRun(pb.RunnerRequest(run_id=run.id))
    bad = pb.AddFindingRequest(run_id=run.id, kind="nonsense", title="x")
    code = await expect_error(stub.AddFinding(bad), grpc.StatusCode.INVALID_ARGUMENT)
    assert code == "VALIDATION_ERROR"

    cancelled = await stub.CancelRun(pb.RunRequest(owner_id=OWNER, run_id=run.id))
    assert cancelled.status == "cancelled"
