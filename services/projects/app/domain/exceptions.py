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


class ProjectNotFoundError(DomainError):
    status_code = HTTPStatus.NOT_FOUND
    error_code = "PROJECT_NOT_FOUND"
    public_message = "Проект не найден"


class ScenarioNotFoundError(DomainError):
    status_code = HTTPStatus.NOT_FOUND
    error_code = "SCENARIO_NOT_FOUND"
    public_message = "Сценарий не найден"
