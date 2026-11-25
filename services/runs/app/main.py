import asyncio
import logging
from collections.abc import Awaitable, Callable

import grpc
from faststream.rabbit import RabbitBroker
from redis.asyncio import Redis

from app.api.servicer import RunsServicer
from app.application.services import RunService
from app.config import settings
from app.grpc_gen import runs_pb2_grpc
from app.infra.broker import RabbitRunEvents
from app.infra.database.connection import session_factory
from app.infra.database.repos import (
    SqlFindingRepository,
    SqlGeneratedTestRepository,
    SqlRunRepository,
    SqlStepRepository,
)
from app.infra.leases import RedisRunLeases

WATCHDOG_INTERVAL_SECONDS = 60
LEASE_SWEEP_SECONDS = 5

logger = logging.getLogger("runs")


async def watch_stale_runs(
    leases: RedisRunLeases,
    expire: Callable[[RunService], Awaitable[int]],
    interval: int,
) -> None:
    """Раз в минуту переводит зависшие прогоны в ошибку, чтобы они не висели вечно."""
    while True:
        try:
            async with session_factory() as session:
                service = RunService(
                    session,
                    SqlRunRepository(session),
                    SqlStepRepository(session),
                    SqlFindingRepository(session),
                    SqlGeneratedTestRepository(session),
                    leases=leases,
                )
                if expired := await expire(service):
                    logger.warning("зависших прогонов переведено в ошибку: %s", expired)
        except Exception:
            logger.exception("сторож зависших прогонов упал, попробуем позже")
        await asyncio.sleep(interval)


async def serve() -> None:
    """Запускает gRPC-сервер прогонов и держит его, пока процесс не остановят."""
    broker = RabbitBroker(settings.rabbitmq_url)
    await broker.start()
    server = grpc.aio.server()
    redis = Redis.from_url(
        settings.redis_url, decode_responses=True, socket_connect_timeout=2, socket_timeout=2
    )
    leases = RedisRunLeases(redis)
    runs_pb2_grpc.add_RunsServiceServicer_to_server(
        RunsServicer(session_factory, RabbitRunEvents(broker), leases), server
    )
    address = f"{settings.grpc_host}:{settings.grpc_port}"
    server.add_insecure_port(address)
    await server.start()
    logger.info("runs gRPC слушает %s", address)
    watchdogs = [
        asyncio.create_task(
            watch_stale_runs(leases, RunService.expire_leases, LEASE_SWEEP_SECONDS)
        ),
        asyncio.create_task(
            watch_stale_runs(leases, RunService.expire_stale_runs, WATCHDOG_INTERVAL_SECONDS)
        ),
    ]
    try:
        await server.wait_for_termination()
    finally:
        await server.stop(grace=5)
        for watchdog in watchdogs:
            watchdog.cancel()
        await asyncio.gather(*watchdogs, return_exceptions=True)
        await redis.aclose()
        await broker.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(serve())
