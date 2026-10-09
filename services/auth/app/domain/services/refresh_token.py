"""Правила для refresh-токена: когда он действует и как его отозвать."""

from datetime import datetime

from app.domain.entities.refresh_token import RefreshToken
from app.domain.exceptions import DomainError


def is_active(token: RefreshToken, now: datetime) -> bool:
    return token.revoked_at is None and now < token.expires_at


def ensure_active(token: RefreshToken, now: datetime) -> None:
    if token.revoked_at is not None:
        raise DomainError("Токен отозван")
    if now >= token.expires_at:
        raise DomainError("Срок действия токена истёк")


def revoke(token: RefreshToken, now: datetime) -> None:
    """Отзыв при выходе или после обмена на новый токен. Повторный отзыв ничего не меняет."""
    if token.revoked_at is None:
        token.revoked_at = now
