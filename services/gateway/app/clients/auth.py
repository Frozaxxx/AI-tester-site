from collections.abc import Awaitable
from http import HTTPStatus

import grpc

from app.exceptions import GatewayError
from app.grpc_gen import auth_pb2, auth_pb2_grpc

HTTP_STATUS = {
    grpc.StatusCode.UNAUTHENTICATED: HTTPStatus.UNAUTHORIZED,
    grpc.StatusCode.ALREADY_EXISTS: HTTPStatus.CONFLICT,
    grpc.StatusCode.INVALID_ARGUMENT: HTTPStatus.UNPROCESSABLE_ENTITY,
    grpc.StatusCode.RESOURCE_EXHAUSTED: HTTPStatus.TOO_MANY_REQUESTS,
}
TIMEOUT_SECONDS = 5


async def _call[T](call: Awaitable[T]) -> T:
    """Выполняет gRPC-вызов и превращает его ошибки в HTTP-ошибки gateway."""
    try:
        return await call
    except grpc.aio.AioRpcError as exc:
        status = HTTP_STATUS.get(exc.code())
        if status is None:
            raise GatewayError(
                HTTPStatus.SERVICE_UNAVAILABLE, "AUTH_UNAVAILABLE", "Сервис временно недоступен"
            ) from None
        error_code = dict(exc.trailing_metadata() or ()).get("error-code", "ERROR")
        raise GatewayError(status, error_code, exc.details() or "") from None


class AuthClient:
    def __init__(self, channel: grpc.aio.Channel) -> None:
        self._stub = auth_pb2_grpc.AuthServiceStub(channel)

    async def register(self, email: str, password: str) -> auth_pb2.User:
        """Регистрирует пользователя через сервис auth."""
        request = auth_pb2.Credentials(email=email, password=password)
        return await _call(self._stub.Register(request, timeout=TIMEOUT_SECONDS))

    async def login(self, email: str, password: str) -> auth_pb2.TokenPair:
        """Выполняет вход через сервис auth."""
        request = auth_pb2.Credentials(email=email, password=password)
        return await _call(self._stub.Login(request, timeout=TIMEOUT_SECONDS))

    async def refresh(self, refresh_token: str) -> auth_pb2.TokenPair:
        """Обновляет пару токенов через сервис auth."""
        request = auth_pb2.RefreshRequest(refresh_token=refresh_token)
        return await _call(self._stub.Refresh(request, timeout=TIMEOUT_SECONDS))

    async def logout(self, refresh_token: str, access_token: str) -> None:
        """Завершает сессию через сервис auth."""
        request = auth_pb2.LogoutRequest(refresh_token=refresh_token, access_token=access_token)
        await _call(self._stub.Logout(request, timeout=TIMEOUT_SECONDS))

    async def get_user(self, user_id: str) -> auth_pb2.User:
        """Получает пользователя у сервиса auth."""
        request = auth_pb2.GetUserRequest(user_id=user_id)
        return await _call(self._stub.GetUser(request, timeout=TIMEOUT_SECONDS))

    async def get_public_key(self) -> str:
        """Получает у сервиса auth публичный ключ для проверки JWT."""
        response = await _call(self._stub.GetPublicKey(auth_pb2.Empty(), timeout=TIMEOUT_SECONDS))
        return response.pem
