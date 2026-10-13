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
from app.grpc_gen import auth_pb2
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


@pytest.fixture
def auth() -> FakeAuthClient:
    return FakeAuthClient()


@pytest.fixture
def redis() -> FakeAsyncRedis:
    return FakeAsyncRedis(decode_responses=True)


@pytest.fixture
async def client(auth: FakeAuthClient, redis: FakeAsyncRedis) -> AsyncIterator[AsyncClient]:
    app.state.auth_client = auth
    app.state.redis = redis
    app.state.public_key = PUBLIC_KEY
    settings.cookie_secure = False
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
