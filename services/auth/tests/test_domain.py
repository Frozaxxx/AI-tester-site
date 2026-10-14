import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.domain.entities import RefreshToken
from app.domain.exceptions import UnauthorizedError, ValidationError
from app.domain.services import create_user, ensure_active, is_active, revoke, validate_password

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def test_email_is_normalized() -> None:
    user = create_user(email="  Andrey@Example.COM ", password_hash="hash")
    assert user.email == "andrey@example.com"


@pytest.mark.parametrize(
    "email",
    [
        "",
        "andrey",
        "andrey@",
        "@example.com",
        "a b@example.com",
        "a\x00b@example.com",
        "a" * 250 + "@example.com",
    ],
)
def test_invalid_email(email: str) -> None:
    with pytest.raises(ValidationError):
        create_user(email=email, password_hash="hash")


@pytest.mark.parametrize("password", ["short", "x" * 129])
def test_invalid_password(password: str) -> None:
    with pytest.raises(ValidationError):
        validate_password(password)


def token(expires_in: timedelta = timedelta(days=1)) -> RefreshToken:
    return RefreshToken(user_id=uuid.uuid4(), token_hash="hash", expires_at=NOW + expires_in)


def test_refresh_token_lifecycle() -> None:
    t = token()
    assert is_active(t, NOW)
    revoke(t, NOW)
    assert not is_active(t, NOW)
    with pytest.raises(UnauthorizedError):
        ensure_active(t, NOW)


def test_expired_refresh_token() -> None:
    with pytest.raises(UnauthorizedError):
        ensure_active(token(expires_in=timedelta(seconds=-1)), NOW)


def test_revoke_twice_keeps_first_time() -> None:
    t = token()
    revoke(t, NOW)
    revoke(t, NOW + timedelta(hours=1))
    assert t.revoked_at == NOW
