from collections.abc import AsyncIterator

import grpc
import pytest
from fakeredis import FakeAsyncRedis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.servicer import AuthServicer
from app.grpc_gen import auth_pb2_grpc
from app.infra.database.models import Base


@pytest.fixture
async def stub() -> AsyncIterator[auth_pb2_grpc.AuthServiceStub]:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    server = grpc.aio.server()
    auth_pb2_grpc.add_AuthServiceServicer_to_server(
        AuthServicer(factory, FakeAsyncRedis(decode_responses=True)), server
    )
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    async with grpc.aio.insecure_channel(f"127.0.0.1:{port}") as channel:
        yield auth_pb2_grpc.AuthServiceStub(channel)
    await server.stop(None)
    await engine.dispose()
