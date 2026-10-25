import asyncio
import logging

import grpc
from faststream.rabbit import RabbitBroker

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

WATCHDOG_INTERVAL_SECONDS = 60

logger = logging.getLogger("runs")


async def watch_stale_runs() -> None:
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
                )
                if expired := await service.expire_stale_runs():
                    logger.warning("зависших прогонов переведено в ошибку: %s", expired)
        except Exception:
            logger.exception("сторож зависших прогонов упал, попробуем позже")
        await asyncio.sleep(WATCHDOG_INTERVAL_SECONDS)


async def serve() -> None:
    """Запускает gRPC-сервер прогонов и держит его, пока процесс не остановят."""
    broker = RabbitBroker(settings.rabbitmq_url)
    await broker.start()
    server = grpc.aio.server()
    runs_pb2_grpc.add_RunsServiceServicer_to_server(
        RunsServicer(session_factory, RabbitRunEvents(broker)), server
    )
    address = f"{settings.grpc_host}:{settings.grpc_port}"
    server.add_insecure_port(address)
    await server.start()
    logger.info("runs gRPC слушает %s", address)
    watchdog = asyncio.create_task(watch_stale_runs())
    try:
        await server.wait_for_termination()
    finally:
        watchdog.cancel()
        await broker.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(serve())
