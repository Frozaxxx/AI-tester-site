from http import HTTPStatus


class DomainError(Exception):
    status_code: int = HTTPStatus.BAD_REQUEST
    error_code: str = "BAD_REQUEST"
    public_message: str = "Некорректный запрос"

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.public_message
        super().__init__(self.message)


class ValidationError(DomainError):
    status_code = HTTPStatus.UNPROCESSABLE_ENTITY
    error_code = "VALIDATION_ERROR"
    public_message = "Некорректные данные"


class RunNotFoundError(DomainError):
    status_code = HTTPStatus.NOT_FOUND
    error_code = "RUN_NOT_FOUND"
    public_message = "Прогон не найден"


class InvalidRunStateError(DomainError):
    status_code = HTTPStatus.CONFLICT
    error_code = "INVALID_RUN_STATE"
    public_message = "Действие недоступно в текущем статусе прогона"
