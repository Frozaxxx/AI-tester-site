import asyncio

import grpc
import pytest

from app.config import settings
from app.grpc_gen import auth_pb2
from app.security import decode_access_token

CREDS = auth_pb2.Credentials(email="andrey@example.com", password="secret123")


async def expect_error(call, code: grpc.StatusCode) -> str:
    with pytest.raises(grpc.aio.AioRpcError) as info:
        await call
    assert info.value.code() == code
    return dict(info.value.trailing_metadata())["error-code"]


async def test_register(stub) -> None:
    user = await stub.Register(CREDS)
    assert user.email == "andrey@example.com" and user.id


async def test_register_duplicate(stub) -> None:
    await stub.Register(CREDS)
    other_case = auth_pb2.Credentials(email="ANDREY@example.com", password="secret123")
    code = await expect_error(stub.Register(other_case), grpc.StatusCode.ALREADY_EXISTS)
    assert code == "EMAIL_ALREADY_EXISTS"


async def test_register_validation(stub) -> None:
    short = auth_pb2.Credentials(email="a@example.com", password="123")
    await expect_error(stub.Register(short), grpc.StatusCode.INVALID_ARGUMENT)


async def test_login_errors_are_identical(stub) -> None:
    await stub.Register(CREDS)
    wrong_password = auth_pb2.Credentials(email=CREDS.email, password="wrong-pass")
    unknown_email = auth_pb2.Credentials(email="x@example.com", password="wrong-pass")
    huge_password = auth_pb2.Credentials(email=CREDS.email, password="a" * 10_000)
    for creds in (wrong_password, unknown_email, huge_password):
        code = await expect_error(stub.Login(creds), grpc.StatusCode.UNAUTHENTICATED)
        assert code == "INVALID_CREDENTIALS"


async def test_login_returns_tokens(stub) -> None:
    await stub.Register(CREDS)
    pair = await stub.Login(CREDS)
    assert decode_access_token(pair.access_token)["sub"] == pair.user.id
    assert pair.refresh_token
    assert pair.refresh_expires_at > pair.access_expires_at


async def test_login_blocked_after_failures(stub) -> None:
    await stub.Register(CREDS)
    wrong = auth_pb2.Credentials(email=CREDS.email, password="wrong-pass")
    for _ in range(settings.login_attempts_limit):
        await expect_error(stub.Login(wrong), grpc.StatusCode.UNAUTHENTICATED)
    await expect_error(stub.Login(CREDS), grpc.StatusCode.RESOURCE_EXHAUSTED)


async def test_parallel_logins_respect_limit(stub) -> None:
    await stub.Register(CREDS)
    wrong = auth_pb2.Credentials(email=CREDS.email, password="wrong-pass")
    results = await asyncio.gather(*(stub.Login(wrong) for _ in range(20)), return_exceptions=True)
    codes = [result.code() for result in results]
    assert codes.count(grpc.StatusCode.UNAUTHENTICATED) == settings.login_attempts_limit
    assert codes.count(grpc.StatusCode.RESOURCE_EXHAUSTED) == 20 - settings.login_attempts_limit


async def test_refresh_rotation_and_reuse(stub) -> None:
    await stub.Register(CREDS)
    first = await stub.Login(CREDS)
    second = await stub.Refresh(auth_pb2.RefreshRequest(refresh_token=first.refresh_token))
    assert second.refresh_token != first.refresh_token

    reuse = stub.Refresh(auth_pb2.RefreshRequest(refresh_token=first.refresh_token))
    await expect_error(reuse, grpc.StatusCode.UNAUTHENTICATED)
    fresh = stub.Refresh(auth_pb2.RefreshRequest(refresh_token=second.refresh_token))
    await expect_error(fresh, grpc.StatusCode.UNAUTHENTICATED)


async def test_logout_revokes_refresh(stub) -> None:
    await stub.Register(CREDS)
    pair = await stub.Login(CREDS)
    await stub.Logout(
        auth_pb2.LogoutRequest(refresh_token=pair.refresh_token, access_token=pair.access_token)
    )
    again = stub.Refresh(auth_pb2.RefreshRequest(refresh_token=pair.refresh_token))
    await expect_error(again, grpc.StatusCode.UNAUTHENTICATED)


async def test_logout_with_garbage_is_ok(stub) -> None:
    await stub.Logout(auth_pb2.LogoutRequest(refresh_token="garbage", access_token="garbage"))


async def test_get_user(stub) -> None:
    user = await stub.Register(CREDS)
    assert (await stub.GetUser(auth_pb2.GetUserRequest(user_id=user.id))).email == CREDS.email
    await expect_error(
        stub.GetUser(auth_pb2.GetUserRequest(user_id="not-a-uuid")), grpc.StatusCode.UNAUTHENTICATED
    )


async def test_public_key(stub) -> None:
    key = await stub.GetPublicKey(auth_pb2.Empty())
    assert "BEGIN PUBLIC KEY" in key.pem and "PRIVATE" not in key.pem
