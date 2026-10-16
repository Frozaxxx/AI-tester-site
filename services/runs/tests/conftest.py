from collections.abc import AsyncIterator

import pytest
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.infra.database.models import Base


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    """Даёт сессию к чистой SQLite-базе в памяти с включёнными внешними ключами."""
    engine = create_async_engine("sqlite+aiosqlite://")
    event.listen(
        engine.sync_engine, "connect", lambda conn, _: conn.execute("PRAGMA foreign_keys=ON")
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        yield session
    await engine.dispose()
