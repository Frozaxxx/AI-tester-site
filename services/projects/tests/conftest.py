from collections.abc import AsyncIterator

import grpc
import pytest
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.api.servicer import ProjectsServicer
from app.grpc_gen import projects_pb2_grpc
from app.infra.database.models import Base


@pytest.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Даёт фабрику сессий к чистой SQLite-базе в памяти с включёнными внешними ключами."""
    engine: AsyncEngine = create_async_engine("sqlite+aiosqlite://")
    event.listen(
        engine.sync_engine, "connect", lambda conn, _: conn.execute("PRAGMA foreign_keys=ON")
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
async def session(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    """Даёт сессию к тестовой базе."""
    async with session_factory() as session:
        yield session


@pytest.fixture
async def stub(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[projects_pb2_grpc.ProjectsServiceStub]:
    """Поднимает gRPC-сервер проектов в тесте и даёт клиент к нему."""
    server = grpc.aio.server()
    projects_pb2_grpc.add_ProjectsServiceServicer_to_server(
        ProjectsServicer(session_factory, allow_internal_urls=False), server
    )
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    async with grpc.aio.insecure_channel(f"127.0.0.1:{port}") as channel:
        yield projects_pb2_grpc.ProjectsServiceStub(channel)
    await server.stop(None)
