import asyncio
import logging

import grpc

from app.api.servicer import RunsServicer
from app.config import settings
from app.grpc_gen import runs_pb2_grpc
from app.infra.database.connection import session_factory

logger = logging.getLogger("runs")


async def serve() -> None:
    """Запускает gRPC-сервер прогонов и держит его, пока процесс не остановят."""
    server = grpc.aio.server()
    runs_pb2_grpc.add_RunsServiceServicer_to_server(RunsServicer(session_factory), server)
    address = f"{settings.grpc_host}:{settings.grpc_port}"
    server.add_insecure_port(address)
    await server.start()
    logger.info("runs gRPC слушает %s", address)
    await server.wait_for_termination()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(serve())
