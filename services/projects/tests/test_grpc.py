import uuid

import grpc
import pytest

from app.grpc_gen import projects_pb2 as pb

OWNER = str(uuid.uuid4())
STRANGER = str(uuid.uuid4())


async def expect_error(call, code: grpc.StatusCode) -> str:
    """Проверяет, что вызов упал с нужным gRPC-кодом, и возвращает код ошибки из метаданных."""
    with pytest.raises(grpc.aio.AioRpcError) as info:
        await call
    assert info.value.code() == code
    return dict(info.value.trailing_metadata())["error-code"]


async def test_project_and_scenario_flow(stub) -> None:
    """Через gRPC можно создать проект и сценарий, получить их списки и удалить."""
    project = await stub.CreateProject(
        pb.CreateProjectRequest(
            owner_id=OWNER, name="Магазин", base_url="https://shop.example.com/"
        )
    )
    assert project.base_url == "https://shop.example.com" and project.created_at > 0

    listed = await stub.ListProjects(pb.ListProjectsRequest(owner_id=OWNER))
    assert [p.id for p in listed.projects] == [project.id]

    ref = pb.ProjectRequest(owner_id=OWNER, project_id=project.id)
    assert (await stub.GetProject(ref)).name == "Магазин"

    scenario = await stub.CreateScenario(
        pb.CreateScenarioRequest(
            owner_id=OWNER, project_id=project.id, title="Корзина", text="Добавь товар"
        )
    )
    assert scenario.project_id == project.id
    scenarios = await stub.ListScenarios(ref)
    assert [s.id for s in scenarios.scenarios] == [scenario.id]

    await stub.DeleteScenario(pb.ScenarioRequest(owner_id=OWNER, scenario_id=scenario.id))
    assert not (await stub.ListScenarios(ref)).scenarios

    await stub.DeleteProject(ref)
    assert not (await stub.ListProjects(pb.ListProjectsRequest(owner_id=OWNER))).projects


async def test_validation_error(stub) -> None:
    """Плохой адрес сайта возвращает INVALID_ARGUMENT с кодом VALIDATION_ERROR."""
    request = pb.CreateProjectRequest(owner_id=OWNER, name="Магазин", base_url="ftp://x.com")
    code = await expect_error(stub.CreateProject(request), grpc.StatusCode.INVALID_ARGUMENT)
    assert code == "VALIDATION_ERROR"


async def test_foreign_project_is_not_found(stub) -> None:
    """Чужой проект возвращает NOT_FOUND, будто его нет."""
    project = await stub.CreateProject(
        pb.CreateProjectRequest(owner_id=OWNER, name="Магазин", base_url="https://a.com")
    )
    ref = pb.ProjectRequest(owner_id=STRANGER, project_id=project.id)
    code = await expect_error(stub.GetProject(ref), grpc.StatusCode.NOT_FOUND)
    assert code == "PROJECT_NOT_FOUND"
    await expect_error(stub.DeleteProject(ref), grpc.StatusCode.NOT_FOUND)
