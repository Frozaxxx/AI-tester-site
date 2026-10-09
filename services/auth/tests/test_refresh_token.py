import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.domain.entities.refresh_token import RefreshToken
from app.domain.exceptions import DomainError
from app.domain.services.refresh_token import ensure_active, is_active, revoke

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def token(expires_in: timedelta = timedelta(days=1)) -> RefreshToken:
    return RefreshToken(user_id=uuid.uuid4(), token_hash="hash", expires_at=NOW + expires_in)


def test_new_token_is_active() -> None:
    assert is_active(token(), NOW)


def test_expired_token() -> None:
    expired = token(expires_in=timedelta(seconds=-1))
    assert not is_active(expired, NOW)
    with pytest.raises(DomainError):
        ensure_active(expired, NOW)


def test_revoked_token() -> None:
    revoked = token()
    revoke(revoked, NOW)
    assert not is_active(revoked, NOW)
    with pytest.raises(DomainError):
        ensure_active(revoked, NOW)


def test_revoke_twice_keeps_first_time() -> None:
    t = token()
    revoke(t, NOW)
    revoke(t, NOW + timedelta(hours=1))
    assert t.revoked_at == NOW
