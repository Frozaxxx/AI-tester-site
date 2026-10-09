"""Правила для пользователя: email и пароль."""

import re

from app.domain.entities.user import User
from app.domain.exceptions import DomainError

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128


def normalize_email(raw: str) -> str:
    email = raw.strip().lower()
    if not EMAIL_RE.match(email):
        raise DomainError("Некорректный email")
    return email


def validate_password(raw: str) -> None:
    """Проверяем пароль до хэширования: сам пароль в User не хранится."""
    if len(raw) < PASSWORD_MIN_LENGTH:
        raise DomainError(f"Пароль должен быть не короче {PASSWORD_MIN_LENGTH} символов")
    if len(raw) > PASSWORD_MAX_LENGTH:
        raise DomainError(f"Пароль должен быть не длиннее {PASSWORD_MAX_LENGTH} символов")


def create_user(email: str, password_hash: str) -> User:
    return User(email=normalize_email(email), password_hash=password_hash)
