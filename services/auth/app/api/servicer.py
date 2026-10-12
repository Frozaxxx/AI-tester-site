from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from functools import wraps
from http import HTTPStatus

import grpc
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.application.dtos import Credentials, Tokens
from app.application.services import AuthService
from app.domain.entities import User
from app.domain.exceptions import DomainError
from app.grpc_gen import auth_pb2, auth_pb2_grpc
from app.infra.database.repos import SqlRefreshTokenRepository, SqlUserRepository
from app.security import public_key_pem

GRPC_STATUS = {
    HTTPStatus.UNAUTHORIZED: grpc.StatusCode.UNAUTHENTICATED,
    HTTPStatus.CONFLICT: grpc.StatusCode.ALREADY_EXISTS,
    HTTPStatus.UNPROCESSABLE_ENTITY: grpc.StatusCode.INVALID_ARGUMENT,
    HTTPStatus.TOO_MANY_REQUESTS: grpc.StatusCode.RESOURCE_EXHAUSTED,
}


def handle_errors[**P, R](method: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
    """Превращает доменные ошибки в gRPC-ошибки с кодом в метаданных."""

    @wraps(method)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        context: grpc.aio.ServicerContext = args[2]  # type: ignore[assignment]
        try:
            return await method(*args, **kwargs)
        except DomainError as exc:
            code = GRPC_STATUS.get(HTTPStatus(exc.status_code), grpc.StatusCode.INVALID_ARGUMENT)
            await context.abort(
                code, exc.message, trailing_metadata=(("error-code", exc.error_code),)
            )

    return wrapper


def _user(user: User) -> auth_pb2.User:
    """Переводит пользователя в proto-сообщение."""
    return auth_pb2.User(
        id=str(user.id), email=user.email, created_at=int(user.created_at.timestamp())
    )


def _token_pair(tokens: Tokens) -> auth_pb2.TokenPair:
    """Собирает proto-сообщение с парой токенов и данными пользователя."""
    return auth_pb2.TokenPair(
        user=_user(tokens.user),
        access_token=tokens.access.token,
        access_expires_at=int(tokens.access.expires_at.timestamp()),
        refresh_token=tokens.refresh_token,
        refresh_expires_at=int(tokens.refresh_expires_at.timestamp()),
    )


class AuthServicer(auth_pb2_grpc.AuthServiceServicer):
    def __init__(self, session_factory: async_sessionmaker, redis: Redis) -> None:
        self._session_factory = session_factory
        self._redis = redis

    @asynccontextmanager
    async def _service(self) -> AsyncIterator[AuthService]:
        """Открывает сессию базы и собирает сервис авторизации на один вызов."""
        async with self._session_factory() as session:
            yield AuthService(
                session=session,
                user_repo=SqlUserRepository(session),
                token_repo=SqlRefreshTokenRepository(session),
                redis=self._redis,
            )

    @handle_errors
    async def Register(self, request, context):
        """Регистрирует нового пользователя."""
        async with self._service() as service:
            user = await service.register(Credentials(request.email, request.password))
        return _user(user)

    @handle_errors
    async def Login(self, request, context):
        """Проверяет email и пароль и выдаёт пару токенов."""
        async with self._service() as service:
            tokens = await service.login(Credentials(request.email, request.password))
        return _token_pair(tokens)

    @handle_errors
    async def Refresh(self, request, context):
        """Выдаёт новую пару токенов по refresh-токену."""
        async with self._service() as service:
            tokens = await service.refresh(request.refresh_token)
        return _token_pair(tokens)

    @handle_errors
    async def Logout(self, request, context):
        """Отзывает refresh-токен и блокирует access-токен."""
        async with self._service() as service:
            await service.logout(request.refresh_token, request.access_token)
        return auth_pb2.Empty()

    @handle_errors
    async def GetUser(self, request, context):
        """Возвращает пользователя по его id."""
        async with self._service() as service:
            user = await service.get_user(request.user_id)
        return _user(user)

    async def GetPublicKey(self, request, context):
        """Отдаёт публичный ключ, которым проверяют подпись JWT."""
        return auth_pb2.PublicKey(pem=public_key_pem())
