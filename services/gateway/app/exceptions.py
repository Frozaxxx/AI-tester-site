from http import HTTPStatus


class GatewayError(Exception):
    def __init__(self, status_code: int, error_code: str, message: str) -> None:
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        super().__init__(message)


class UnauthorizedError(GatewayError):
    def __init__(self, message: str = "Требуется авторизация") -> None:
        super().__init__(HTTPStatus.UNAUTHORIZED, "UNAUTHORIZED", message)
