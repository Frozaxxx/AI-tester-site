import grpc

from app.clients.base import TIMEOUT_SECONDS, grpc_call
from app.grpc_gen import auth_pb2, auth_pb2_grpc


class AuthClient:
    def __init__(self, channel: grpc.aio.Channel) -> None:
        self._stub = auth_pb2_grpc.AuthServiceStub(channel)

    async def register(self, email: str, password: str) -> auth_pb2.User:
        """Регистрирует пользователя через сервис auth."""
        request = auth_pb2.Credentials(email=email, password=password)
        return await grpc_call(self._stub.Register(request, timeout=TIMEOUT_SECONDS))

    async def login(self, email: str, password: str) -> auth_pb2.TokenPair:
        """Выполняет вход через сервис auth."""
        request = auth_pb2.Credentials(email=email, password=password)
        return await grpc_call(self._stub.Login(request, timeout=TIMEOUT_SECONDS))

    async def refresh(self, refresh_token: str) -> auth_pb2.TokenPair:
        """Обновляет пару токенов через сервис auth."""
        request = auth_pb2.RefreshRequest(refresh_token=refresh_token)
        return await grpc_call(self._stub.Refresh(request, timeout=TIMEOUT_SECONDS))

    async def logout(self, refresh_token: str, access_token: str) -> None:
        """Завершает сессию через сервис auth."""
        request = auth_pb2.LogoutRequest(refresh_token=refresh_token, access_token=access_token)
        await grpc_call(self._stub.Logout(request, timeout=TIMEOUT_SECONDS))

    async def get_user(self, user_id: str) -> auth_pb2.User:
        """Получает пользователя у сервиса auth."""
        request = auth_pb2.GetUserRequest(user_id=user_id)
        return await grpc_call(self._stub.GetUser(request, timeout=TIMEOUT_SECONDS))

    async def get_public_key(self) -> str:
        """Получает у сервиса auth публичный ключ для проверки JWT."""
        response = await grpc_call(
            self._stub.GetPublicKey(auth_pb2.Empty(), timeout=TIMEOUT_SECONDS)
        )
        return response.pem
