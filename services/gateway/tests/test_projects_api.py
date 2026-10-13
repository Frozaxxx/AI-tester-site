import uuid

from httpx import AsyncClient

from tests.conftest import make_access_token

PROJECT = {"name": "Демо-магазин", "base_url": "http://127.0.0.1:8001"}


def login_as(client: AsyncClient, user_id: str) -> None:
    """Кладёт клиенту access-куку нужного пользователя."""
    client.cookies.set("access_token", make_access_token(user_id))


async def test_projects_require_auth(client: AsyncClient) -> None:
    """Без access-куки ручки проектов отвечают 401."""
    assert (await client.get("/api/v1/projects")).status_code == 401
    assert (await client.post("/api/v1/projects", json=PROJECT)).status_code == 401
    assert (await client.delete(f"/api/v1/scenarios/{uuid.uuid4()}")).status_code == 401


async def test_project_and_scenario_flow(client: AsyncClient) -> None:
    """Пользователь создаёт проект и сценарий, видит их и удаляет."""
    login_as(client, str(uuid.uuid4()))
    r = await client.post("/api/v1/projects", json=PROJECT)
    assert r.status_code == 201
    project_id = r.json()["id"]
    assert r.json()["base_url"] == PROJECT["base_url"]

    assert [p["id"] for p in (await client.get("/api/v1/projects")).json()] == [project_id]
    assert (await client.get(f"/api/v1/projects/{project_id}")).json()["name"] == PROJECT["name"]

    scenarios_url = f"/api/v1/projects/{project_id}/scenarios"
    r = await client.post(scenarios_url, json={"title": "Корзина", "text": "Добавь товар"})
    assert r.status_code == 201
    scenario_id = r.json()["id"]
    assert [s["id"] for s in (await client.get(scenarios_url)).json()] == [scenario_id]

    assert (await client.delete(f"/api/v1/scenarios/{scenario_id}")).status_code == 204
    assert (await client.delete(f"/api/v1/projects/{project_id}")).status_code == 204
    assert (await client.get("/api/v1/projects")).json() == []


async def test_owner_is_taken_from_token(client: AsyncClient, projects) -> None:
    """Владельцем проекта становится пользователь из токена, а чужой проект даёт 404."""
    owner = str(uuid.uuid4())
    login_as(client, owner)
    project_id = (await client.post("/api/v1/projects", json=PROJECT)).json()["id"]
    assert projects.projects[project_id][0] == owner

    login_as(client, str(uuid.uuid4()))
    r = await client.get(f"/api/v1/projects/{project_id}")
    assert r.status_code == 404
    assert r.json()["error_code"] == "PROJECT_NOT_FOUND"
    assert (await client.get("/api/v1/projects")).json() == []


async def test_validation(client: AsyncClient) -> None:
    """Слишком длинные поля отсекает gateway, а плохой адрес — сервис projects."""
    login_as(client, str(uuid.uuid4()))
    r = await client.post("/api/v1/projects", json={**PROJECT, "name": "x" * 201})
    assert r.status_code == 422
    r = await client.post("/api/v1/projects", json={**PROJECT, "base_url": "ftp://x.com"})
    assert r.status_code == 422
    assert r.json()["error_code"] == "VALIDATION_ERROR"
