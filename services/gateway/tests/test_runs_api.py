import uuid

from httpx import AsyncClient

from tests.conftest import make_access_token

PROJECT = {"name": "Магазин", "base_url": "https://shop.example.com"}


def login_as(client: AsyncClient, user_id: str) -> None:
    """Кладёт клиенту access-куку нужного пользователя."""
    client.cookies.set("access_token", make_access_token(user_id))


async def create_project(client: AsyncClient) -> str:
    """Создаёт проект текущего пользователя и возвращает его id."""
    return (await client.post("/api/v1/projects", json=PROJECT)).json()["id"]


async def test_runs_require_auth(client: AsyncClient) -> None:
    """Без access-куки ручки прогонов отвечают 401."""
    project_id = str(uuid.uuid4())
    assert (await client.post(f"/api/v1/projects/{project_id}/runs", json={})).status_code == 401
    assert (await client.get(f"/api/v1/runs/{uuid.uuid4()}")).status_code == 401


async def test_run_flow(client: AsyncClient, runs) -> None:
    """Пользователь запускает прогон, видит его в списке, смотрит результаты и отменяет."""
    owner = str(uuid.uuid4())
    login_as(client, owner)
    project_id = await create_project(client)

    r = await client.post(f"/api/v1/projects/{project_id}/runs", json={})
    assert r.status_code == 201
    run = r.json()
    assert run["status"] == "queued" and run["scenario_id"] is None and run["finished_at"] is None
    assert runs.runs[run["id"]][0] == owner

    listed = (await client.get(f"/api/v1/projects/{project_id}/runs")).json()
    assert [item["id"] for item in listed] == [run["id"]]

    details = (await client.get(f"/api/v1/runs/{run['id']}")).json()
    assert details["steps"][0]["error"] == "нет кнопки" and details["steps"][0]["value"] is None
    assert details["findings"][0]["step_index"] == 0 and details["test"] is None

    cancelled = await client.post(f"/api/v1/runs/{run['id']}/cancel")
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelled"
    again = await client.post(f"/api/v1/runs/{run['id']}/cancel")
    assert again.status_code == 409 and again.json()["error_code"] == "INVALID_RUN_STATE"


async def test_run_with_scenario(client: AsyncClient) -> None:
    """Прогон по сценарию запускается, только если сценарий лежит в этом проекте."""
    login_as(client, str(uuid.uuid4()))
    project_id = await create_project(client)
    other_project_id = await create_project(client)
    scenario = await client.post(
        f"/api/v1/projects/{project_id}/scenarios", json={"title": "Корзина", "text": "Купи"}
    )
    scenario_id = scenario.json()["id"]

    url = f"/api/v1/projects/{project_id}/runs"
    r = await client.post(url, json={"scenario_id": scenario_id.upper()})
    assert r.status_code == 201 and r.json()["scenario_id"] == scenario_id
    r = await client.post(url, json={"scenario_id": "not-a-uuid"})
    assert r.status_code == 422

    url = f"/api/v1/projects/{other_project_id}/runs"
    r = await client.post(url, json={"scenario_id": scenario_id})
    assert r.status_code == 404 and r.json()["error_code"] == "SCENARIO_NOT_FOUND"


async def test_foreign_project_and_run_are_not_found(client: AsyncClient) -> None:
    """Нельзя запустить прогон в чужом проекте, смотреть или отменять чужой прогон."""
    login_as(client, str(uuid.uuid4()))
    project_id = await create_project(client)
    run_id = (await client.post(f"/api/v1/projects/{project_id}/runs", json={})).json()["id"]

    login_as(client, str(uuid.uuid4()))
    r = await client.post(f"/api/v1/projects/{project_id}/runs", json={})
    assert r.status_code == 404 and r.json()["error_code"] == "PROJECT_NOT_FOUND"
    assert (await client.get(f"/api/v1/projects/{project_id}/runs")).status_code == 404
    assert (await client.get(f"/api/v1/runs/{run_id}")).status_code == 404
    assert (await client.post(f"/api/v1/runs/{run_id}/cancel")).status_code == 404
