from collections.abc import AsyncIterator

import grpc
import pytest
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.servicer import RunsServicer
from app.grpc_gen import runs_pb2_grpc
from app.infra.database.models import Base


@pytest.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Даёт фабрику сессий к чистой SQLite-базе в памяти с включёнными внешними ключами."""
    engine = create_async_engine("sqlite+aiosqlite://")
    event.listen(
        engine.sync_engine, "connect", lambda conn, _: conn.execute("PRAGMA foreign_keys=ON")
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
async def session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Даёт сессию к тестовой базе."""
    async with session_factory() as session:
        yield session


@pytest.fixture
async def stub(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[runs_pb2_grpc.RunsServiceStub]:
    """Поднимает gRPC-сервер прогонов в тесте и даёт клиент к нему."""
    server = grpc.aio.server()
    runs_pb2_grpc.add_RunsServiceServicer_to_server(RunsServicer(session_factory), server)
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    async with grpc.aio.insecure_channel(f"127.0.0.1:{port}") as channel:
        yield runs_pb2_grpc.RunsServiceStub(channel)
    await server.stop(None)
