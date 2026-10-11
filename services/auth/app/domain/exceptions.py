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


class EmailAlreadyExistsError(DomainError):
    status_code = HTTPStatus.CONFLICT
    error_code = "EMAIL_ALREADY_EXISTS"
    public_message = "Пользователь с таким email уже зарегистрирован"


class InvalidCredentialsError(DomainError):
    status_code = HTTPStatus.UNAUTHORIZED
    error_code = "INVALID_CREDENTIALS"
    public_message = "Неверный email или пароль"


class UnauthorizedError(DomainError):
    status_code = HTTPStatus.UNAUTHORIZED
    error_code = "UNAUTHORIZED"
    public_message = "Требуется авторизация"


class TooManyAttemptsError(DomainError):
    status_code = HTTPStatus.TOO_MANY_REQUESTS
    error_code = "TOO_MANY_ATTEMPTS"
    public_message = "Слишком много попыток входа, попробуйте позже"
