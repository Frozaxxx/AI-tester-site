from collections.abc import Awaitable
from http import HTTPStatus

import grpc

from app.exceptions import GatewayError

HTTP_STATUS = {
    grpc.StatusCode.UNAUTHENTICATED: HTTPStatus.UNAUTHORIZED,
    grpc.StatusCode.ALREADY_EXISTS: HTTPStatus.CONFLICT,
    grpc.StatusCode.INVALID_ARGUMENT: HTTPStatus.UNPROCESSABLE_ENTITY,
    grpc.StatusCode.RESOURCE_EXHAUSTED: HTTPStatus.TOO_MANY_REQUESTS,
    grpc.StatusCode.NOT_FOUND: HTTPStatus.NOT_FOUND,
    grpc.StatusCode.FAILED_PRECONDITION: HTTPStatus.CONFLICT,
}
TIMEOUT_SECONDS = 5


async def grpc_call[T](call: Awaitable[T]) -> T:
    """Выполняет gRPC-вызов и превращает его ошибки в HTTP-ошибки gateway."""
    try:
        return await call
    except grpc.aio.AioRpcError as exc:
        status = HTTP_STATUS.get(exc.code())
        if status is None:
            raise GatewayError(
                HTTPStatus.SERVICE_UNAVAILABLE, "SERVICE_UNAVAILABLE", "Сервис временно недоступен"
            ) from None
        error_code = dict(exc.trailing_metadata() or ()).get("error-code", "ERROR")
        raise GatewayError(status, error_code, exc.details() or "") from None
