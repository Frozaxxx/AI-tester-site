import time

from fastapi import APIRouter, Response, status

from app.config import settings
from app.dependencies import (
    ACCESS_COOKIE,
    REFRESH_COOKIE,
    AccessCookie,
    AuthClientDep,
    CurrentUserId,
    RefreshCookie,
)
from app.exceptions import UnauthorizedError
from app.grpc_gen import auth_pb2
from app.schemas import Credentials, UserResponse

router = APIRouter(prefix="/auth", tags=["Авторизация"])

REFRESH_COOKIE_PATH = "/api/v1/auth"


def _seconds_until(timestamp: int) -> int:
    """Считает, сколько секунд осталось до указанного момента."""
    return max(0, timestamp - int(time.time()))


def _set_auth_cookies(response: Response, tokens: auth_pb2.TokenPair) -> None:
    """Кладёт access- и refresh-токены в httpOnly-куки."""
    response.set_cookie(
        ACCESS_COOKIE,
        tokens.access_token,
        max_age=_seconds_until(tokens.access_expires_at),
        path="/",
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )
    response.set_cookie(
        REFRESH_COOKIE,
        tokens.refresh_token,
        max_age=_seconds_until(tokens.refresh_expires_at),
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
    )


def _delete_auth_cookies(response: Response) -> None:
    """Удаляет куки с токенами."""
    response.delete_cookie(
        ACCESS_COOKIE, path="/", httponly=True, secure=settings.cookie_secure, samesite="lax"
    )
    response.delete_cookie(
        REFRESH_COOKIE,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
    )


@router.post("/register", status_code=status.HTTP_201_CREATED, summary="Регистрация")
async def register(credentials: Credentials, auth: AuthClientDep) -> UserResponse:
    """Регистрирует нового пользователя."""
    user = await auth.register(credentials.email, credentials.password)
    return UserResponse.from_proto(user)


@router.post("/login", summary="Вход: ставит куки с токенами")
async def login(credentials: Credentials, response: Response, auth: AuthClientDep) -> UserResponse:
    """Выполняет вход и ставит куки с токенами."""
    tokens = await auth.login(credentials.email, credentials.password)
    _set_auth_cookies(response, tokens)
    return UserResponse.from_proto(tokens.user)


@router.post("/refresh", summary="Новая пара токенов по refresh-куке")
async def refresh(
    response: Response, auth: AuthClientDep, refresh_token: RefreshCookie = None
) -> UserResponse:
    """Обновляет пару токенов по refresh-куке."""
    if not refresh_token:
        raise UnauthorizedError
    tokens = await auth.refresh(refresh_token)
    _set_auth_cookies(response, tokens)
    return UserResponse.from_proto(tokens.user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Выход")
async def logout(
    response: Response,
    auth: AuthClientDep,
    access_token: AccessCookie = None,
    refresh_token: RefreshCookie = None,
) -> None:
    """Выходит из аккаунта и удаляет куки с токенами."""
    await auth.logout(refresh_token or "", access_token or "")
    _delete_auth_cookies(response)


@router.get("/me", summary="Текущий пользователь")
async def me(user_id: CurrentUserId, auth: AuthClientDep) -> UserResponse:
    """Возвращает текущего пользователя."""
    return UserResponse.from_proto(await auth.get_user(user_id))
