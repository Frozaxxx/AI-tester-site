import grpc
import pytest
from httpx import AsyncClient

from app.clients.base import grpc_call
from app.exceptions import GatewayError
from tests.conftest import make_access_token

AUTH = "/api/v1/auth"
CREDS = {"email": "andrey@example.com", "password": "secret123"}


async def test_register(client: AsyncClient) -> None:
    r = await client.post(f"{AUTH}/register", json=CREDS)
    assert r.status_code == 201
    assert r.json()["email"] == CREDS["email"]


async def test_auth_error_is_passed_through(client: AsyncClient) -> None:
    r = await client.post(f"{AUTH}/register", json={**CREDS, "email": "taken@example.com"})
    assert r.status_code == 409
    assert r.json()["error_code"] == "EMAIL_ALREADY_EXISTS"


async def test_too_long_input_is_rejected_before_auth(client: AsyncClient) -> None:
    r = await client.post(f"{AUTH}/login", json={**CREDS, "password": "a" * 10_000})
    assert r.status_code == 422
    assert r.json() == {
        "error_code": "VALIDATION_ERROR",
        "message": "Некорректные данные: password",
    }


async def test_login_sets_cookies(client: AsyncClient) -> None:
    r = await client.post(f"{AUTH}/login", json=CREDS)
    assert r.status_code == 200
    assert "token" not in r.json()
    cookies = r.headers.get_list("set-cookie")
    access = next(c for c in cookies if c.startswith("access_token="))
    refresh = next(c for c in cookies if c.startswith("refresh_token="))
    assert "HttpOnly" in access and "SameSite=lax" in access and "Path=/;" in access
    assert "Max-Age=1800" in access or "Max-Age=1799" in access
    assert "HttpOnly" in refresh and "SameSite=strict" in refresh
    assert "Path=/api/v1/auth" in refresh


async def test_me_requires_valid_token(client: AsyncClient, auth) -> None:
    assert (await client.get(f"{AUTH}/me")).status_code == 401
    client.cookies.set("access_token", "garbage")
    assert (await client.get(f"{AUTH}/me")).status_code == 401
    client.cookies.set("access_token", make_access_token(auth.user.id, aud="other"))
    assert (await client.get(f"{AUTH}/me")).status_code == 401
    client.cookies.set("access_token", make_access_token(auth.user.id, type="refresh"))
    assert (await client.get(f"{AUTH}/me")).status_code == 401
    client.cookies.set("access_token", make_access_token(auth.user.id))
    assert (await client.get(f"{AUTH}/me")).status_code == 200


async def test_revoked_token_is_rejected(client: AsyncClient, auth, redis) -> None:
    client.cookies.set("access_token", make_access_token(auth.user.id, jti="revoked-jti"))
    await redis.set("auth:revoked:revoked-jti", 1)
    r = await client.get(f"{AUTH}/me")
    assert r.status_code == 401
    assert r.json()["message"] == "Токен отозван"


async def test_refresh_requires_cookie(client: AsyncClient) -> None:
    assert (await client.post(f"{AUTH}/refresh")).status_code == 401


async def test_logout_passes_tokens_and_deletes_cookies(client: AsyncClient, auth) -> None:
    await client.post(f"{AUTH}/login", json=CREDS)
    access = client.cookies.get("access_token")
    refresh = client.cookies.get("refresh_token")
    r = await client.post(f"{AUTH}/logout")
    assert r.status_code == 204
    assert auth.logout_calls == [(refresh, access)]
    assert client.cookies.get("access_token") is None


def _rpc_error(code: grpc.StatusCode, error_code: str | None = None) -> grpc.aio.AioRpcError:
    trailing = grpc.aio.Metadata(("error-code", error_code)) if error_code else grpc.aio.Metadata()
    return grpc.aio.AioRpcError(code, grpc.aio.Metadata(), trailing, details="текст ошибки")


@pytest.mark.parametrize(
    ("code", "status"),
    [
        (grpc.StatusCode.UNAUTHENTICATED, 401),
        (grpc.StatusCode.ALREADY_EXISTS, 409),
        (grpc.StatusCode.INVALID_ARGUMENT, 422),
        (grpc.StatusCode.RESOURCE_EXHAUSTED, 429),
        (grpc.StatusCode.NOT_FOUND, 404),
        (grpc.StatusCode.FAILED_PRECONDITION, 409),
        (grpc.StatusCode.UNAVAILABLE, 503),
    ],
)
async def test_grpc_errors_map_to_http(code: grpc.StatusCode, status: int) -> None:
    async def failing():
        raise _rpc_error(code, "SOME_CODE")

    with pytest.raises(GatewayError) as info:
        await grpc_call(failing())
    assert info.value.status_code == status
