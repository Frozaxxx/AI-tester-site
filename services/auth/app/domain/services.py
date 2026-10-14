import re
from datetime import datetime

from app.domain.entities import RefreshToken, User
from app.domain.exceptions import UnauthorizedError, ValidationError

EMAIL_RE = re.compile(r"^[^@\s\x00-\x1f\x7f]+@[^@\s\x00-\x1f\x7f]+\.[^@\s\x00-\x1f\x7f]+$")
EMAIL_MAX_LENGTH = 254
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128


def normalize_email(raw: str) -> str:
    """Приводит email к нижнему регистру и проверяет его формат."""
    email = raw.strip().lower()
    if len(email) > EMAIL_MAX_LENGTH or not EMAIL_RE.match(email):
        raise ValidationError("Некорректный email")
    return email


def validate_password(raw: str) -> None:
    """Проверяет, что длина пароля в допустимых пределах."""
    if len(raw) < PASSWORD_MIN_LENGTH:
        raise ValidationError(f"Пароль должен быть не короче {PASSWORD_MIN_LENGTH} символов")
    if len(raw) > PASSWORD_MAX_LENGTH:
        raise ValidationError(f"Пароль должен быть не длиннее {PASSWORD_MAX_LENGTH} символов")


def create_user(email: str, password_hash: str) -> User:
    """Создаёт пользователя с проверенным email."""
    return User(email=normalize_email(email), password_hash=password_hash)


def is_active(token: RefreshToken, now: datetime) -> bool:
    """Проверяет, что refresh-токен не отозван и не истёк."""
    return token.revoked_at is None and now < token.expires_at


def ensure_active(token: RefreshToken, now: datetime) -> None:
    """Выбрасывает ошибку, если refresh-токен отозван или истёк."""
    if token.revoked_at is not None:
        raise UnauthorizedError("Токен отозван")
    if now >= token.expires_at:
        raise UnauthorizedError("Срок действия токена истёк")


def revoke(token: RefreshToken, now: datetime) -> None:
    """Отзывает refresh-токен, если он ещё не отозван."""
    if token.revoked_at is None:
        token.revoked_at = now
