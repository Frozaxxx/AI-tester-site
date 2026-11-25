import asyncio
import os
import uuid
from contextlib import asynccontextmanager

import grpc
import pytest
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.schema import CreateSchema, DropSchema

from app.api.servicer import RunsServicer
from app.domain.exceptions import InvalidRunStateError
from app.grpc_gen import runs_pb2 as pb
from app.grpc_gen import runs_pb2_grpc
from app.infra import leases as lease_store
from app.infra.database.models import Base


@pytest.fixture
async def lease_backend(monkeypatch):
    postgres_url = os.getenv("TEST_RUNS_DATABASE_URL")
    redis_url = os.getenv("TEST_RUNS_REDIS_URL")
    if not postgres_url or not redis_url:
        pytest.skip("Set TEST_RUNS_DATABASE_URL and TEST_RUNS_REDIS_URL for the concurrency test")

    schema = f"lease_test_{uuid.uuid4().hex}"
    key = f"runs:{schema}"
    monkeypatch.setattr(lease_store, "LEASE_KEY", key)
    engine = create_async_engine(
        postgres_url, connect_args={"server_settings": {"search_path": schema}}
    )
    async with Redis.from_url(redis_url, decode_responses=True) as redis:
        try:
            async with engine.begin() as connection:
                await connection.execute(CreateSchema(schema))
                await connection.run_sync(Base.metadata.create_all)
            factory = async_sessionmaker(engine, expire_on_commit=False)
            yield factory, redis
        finally:
            await redis.delete(key)
            async with engine.begin() as connection:
                await connection.execute(DropSchema(schema, cascade=True, if_exists=True))
            await engine.dispose()


@asynccontextmanager
async def replica(factory, redis):
    servicer = RunsServicer(factory, leases=lease_store.RedisRunLeases(redis))
    server = grpc.aio.server()
    runs_pb2_grpc.add_RunsServiceServicer_to_server(servicer, server)
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    try:
        async with grpc.aio.insecure_channel(f"127.0.0.1:{port}") as channel:
            yield servicer, runs_pb2_grpc.RunsServiceStub(channel)
    finally:
        await server.stop(None)


async def test_lost_runner_releases_active_slot_across_replicas(lease_backend):
    factory, redis = lease_backend
    async with (
        replica(factory, redis) as (first, worker),
        replica(factory, redis) as (second, peer),
    ):
        create = pb.CreateRunRequest(owner_id=str(uuid.uuid4()), project_id=str(uuid.uuid4()))
        run = await worker.CreateRun(create)
        a, b = await asyncio.gather(worker.ClaimRun(pb.Empty()), peer.ClaimRun(pb.Empty()))
        assert [claim.run.id for claim in (a, b) if claim.HasField("run")] == [run.id]

        ref = pb.RunnerRequest(run_id=run.id)
        await worker.AddStep(pb.AddStepRequest(run_id=run.id, index=0, action="goto", ok=True))
        before = await redis.zscore(lease_store.LEASE_KEY, run.id)
        await redis.zincrby(lease_store.LEASE_KEY, -1_000, run.id)
        await peer.HeartbeatRun(ref)
        assert await redis.zscore(lease_store.LEASE_KEY, run.id) >= before

        await redis.zadd(lease_store.LEASE_KEY, {run.id: 0})
        with pytest.raises(grpc.aio.AioRpcError) as lost:
            await worker.HeartbeatRun(ref)
        assert lost.value.code() == grpc.StatusCode.FAILED_PRECONDITION
        with pytest.raises(grpc.aio.AioRpcError) as late:
            await worker.FinishRun(ref)
        assert late.value.code() == grpc.StatusCode.FAILED_PRECONDITION

        async with first._service() as left, second._service() as right:
            assert sum(await asyncio.gather(left.expire_leases(), right.expire_leases())) == 1
            with pytest.raises(InvalidRunStateError):
                await left.heartbeat(run.id)

        result = await peer.GetRun(pb.RunRequest(owner_id=create.owner_id, run_id=run.id))
        assert result.run.status == "error" and result.steps[0].action == "goto"
        assert not (await peer.ClaimRun(pb.Empty())).HasField("run")
        for _ in range(3):
            assert (await peer.CreateRun(create)).status == "queued"
