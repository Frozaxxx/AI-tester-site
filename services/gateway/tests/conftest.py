import time
import uuid
from collections.abc import AsyncIterator
from http import HTTPStatus

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fakeredis import FakeAsyncRedis
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.exceptions import GatewayError
from app.grpc_gen import auth_pb2, projects_pb2, runs_pb2
from app.main import app

_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PRIVATE_KEY = _key.private_bytes(
    serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
)
PUBLIC_KEY = (
    _key.public_key()
    .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    .decode()
)


def make_access_token(user_id: str, jti: str | None = None, **overrides) -> str:
    payload = {
        "sub": user_id,
        "jti": jti or uuid.uuid4().hex,
        "exp": int(time.time()) + 1800,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "type": "access",
        **overrides,
    }
    return jwt.encode(payload, PRIVATE_KEY, algorithm=settings.jwt_algorithm)


class FakeAuthClient:
    def __init__(self) -> None:
        self.user = auth_pb2.User(id=str(uuid.uuid4()), email="andrey@example.com", created_at=0)
        self.logout_calls: list[tuple[str, str]] = []

    def _pair(self) -> auth_pb2.TokenPair:
        now = int(time.time())
        return auth_pb2.TokenPair(
            user=self.user,
            access_token=make_access_token(self.user.id),
            access_expires_at=now + 1800,
            refresh_token=uuid.uuid4().hex,
            refresh_expires_at=now + 86400,
        )

    async def register(self, email: str, password: str) -> auth_pb2.User:
        if email == "taken@example.com":
            raise GatewayError(HTTPStatus.CONFLICT, "EMAIL_ALREADY_EXISTS", "занят")
        return self.user

    async def login(self, email: str, password: str) -> auth_pb2.TokenPair:
        if password != "secret123":
            raise GatewayError(HTTPStatus.UNAUTHORIZED, "INVALID_CREDENTIALS", "неверно")
        return self._pair()

    async def refresh(self, refresh_token: str) -> auth_pb2.TokenPair:
        return self._pair()

    async def logout(self, refresh_token: str, access_token: str) -> None:
        self.logout_calls.append((refresh_token, access_token))

    async def get_user(self, user_id: str) -> auth_pb2.User:
        return self.user


class FakeProjectsClient:
    def __init__(self) -> None:
        self.projects: dict[str, tuple[str, projects_pb2.Project]] = {}
        self.scenarios: dict[str, tuple[str, projects_pb2.Scenario]] = {}

    def _own_project(self, owner_id: str, project_id: str) -> projects_pb2.Project:
        owner, project = self.projects.get(project_id, ("", None))
        if owner != owner_id:
            raise GatewayError(HTTPStatus.NOT_FOUND, "PROJECT_NOT_FOUND", "Проект не найден")
        return project

    async def create_project(self, owner_id: str, name: str, base_url: str) -> projects_pb2.Project:
        if not base_url.startswith(("http://", "https://")):
            raise GatewayError(HTTPStatus.UNPROCESSABLE_ENTITY, "VALIDATION_ERROR", "плохой адрес")
        project = projects_pb2.Project(
            id=str(uuid.uuid4()), name=name, base_url=base_url, created_at=int(time.time())
        )
        self.projects[project.id] = (owner_id, project)
        return project

    async def list_projects(self, owner_id: str) -> list[projects_pb2.Project]:
        return [p for owner, p in self.projects.values() if owner == owner_id]

    async def get_project(self, owner_id: str, project_id: str) -> projects_pb2.Project:
        return self._own_project(owner_id, project_id)

    async def delete_project(self, owner_id: str, project_id: str) -> None:
        self._own_project(owner_id, project_id)
        del self.projects[project_id]

    async def create_scenario(
        self, owner_id: str, project_id: str, title: str, text: str
    ) -> projects_pb2.Scenario:
        self._own_project(owner_id, project_id)
        scenario = projects_pb2.Scenario(
            id=str(uuid.uuid4()), project_id=project_id, title=title, text=text, created_at=0
        )
        self.scenarios[scenario.id] = (owner_id, scenario)
        return scenario

    async def list_scenarios(self, owner_id: str, project_id: str) -> list[projects_pb2.Scenario]:
        self._own_project(owner_id, project_id)
        return [s for _, s in self.scenarios.values() if s.project_id == project_id]

    async def delete_scenario(self, owner_id: str, scenario_id: str) -> None:
        owner, _ = self.scenarios.get(scenario_id, ("", None))
        if owner != owner_id:
            raise GatewayError(HTTPStatus.NOT_FOUND, "SCENARIO_NOT_FOUND", "Сценарий не найден")
        del self.scenarios[scenario_id]


class FakeRunsClient:
    def __init__(self) -> None:
        self.runs: dict[str, tuple[str, runs_pb2.Run]] = {}

    def _own_run(self, owner_id: str, run_id: str) -> runs_pb2.Run:
        owner, run = self.runs.get(run_id, ("", None))
        if owner != owner_id:
            raise GatewayError(HTTPStatus.NOT_FOUND, "RUN_NOT_FOUND", "Прогон не найден")
        return run

    async def create_run(
        self, owner_id: str, project_id: str, scenario_id: str | None
    ) -> runs_pb2.Run:
        run = runs_pb2.Run(
            id=str(uuid.uuid4()),
            project_id=project_id,
            scenario_id=scenario_id,
            status="queued",
            created_at=int(time.time()),
        )
        self.runs[run.id] = (owner_id, run)
        return run

    async def list_runs(self, owner_id: str, project_id: str) -> list[runs_pb2.Run]:
        return [
            r for owner, r in self.runs.values() if owner == owner_id and r.project_id == project_id
        ]

    async def get_run(self, owner_id: str, run_id: str) -> runs_pb2.RunDetails:
        run = self._own_run(owner_id, run_id)
        step = runs_pb2.Step(index=0, action="click", ok=False, error="нет кнопки")
        finding = runs_pb2.Finding(id="f1", kind="assertion", title="Баг", step_index=0)
        return runs_pb2.RunDetails(run=run, steps=[step], findings=[finding])

    async def cancel_run(self, owner_id: str, run_id: str) -> runs_pb2.Run:
        run = self._own_run(owner_id, run_id)
        if run.status == "cancelled":
            raise GatewayError(HTTPStatus.CONFLICT, "INVALID_RUN_STATE", "Прогон уже завершён")
        run.status = "cancelled"
        run.finished_at = int(time.time())
        return run


@pytest.fixture
def auth() -> FakeAuthClient:
    return FakeAuthClient()


@pytest.fixture
def redis() -> FakeAsyncRedis:
    return FakeAsyncRedis(decode_responses=True)


@pytest.fixture
def projects() -> FakeProjectsClient:
    return FakeProjectsClient()


@pytest.fixture
def runs() -> FakeRunsClient:
    return FakeRunsClient()


@pytest.fixture
async def client(
    auth: FakeAuthClient,
    projects: FakeProjectsClient,
    runs: FakeRunsClient,
    redis: FakeAsyncRedis,
) -> AsyncIterator[AsyncClient]:
    app.state.auth_client = auth
    app.state.projects_client = projects
    app.state.runs_client = runs
    app.state.redis = redis
    app.state.public_key = PUBLIC_KEY
    settings.cookie_secure = False
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
