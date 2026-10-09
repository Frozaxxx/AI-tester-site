from datetime import UTC, datetime, timedelta

import pytest
from fakeredis import FakeAsyncRedis

from app.infrastructure.redis.denylist import AccessTokenDenylist


@pytest.fixture
def denylist() -> AccessTokenDenylist:
    return AccessTokenDenylist(FakeAsyncRedis())


async def test_revoked_token_is_in_denylist(denylist: AccessTokenDenylist) -> None:
    await denylist.add("jti-1", datetime.now(UTC) + timedelta(minutes=10))
    assert await denylist.contains("jti-1")
    assert not await denylist.contains("jti-2")


async def test_expired_token_is_not_stored(denylist: AccessTokenDenylist) -> None:
    await denylist.add("jti-old", datetime.now(UTC) - timedelta(seconds=1))
    assert not await denylist.contains("jti-old")
