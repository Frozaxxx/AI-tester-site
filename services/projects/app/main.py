import asyncio
import logging

import grpc

from app.api.servicer import ProjectsServicer
from app.config import settings
from app.grpc_gen import projects_pb2_grpc
from app.infra.database.connection import session_factory

logger = logging.getLogger("projects")


async def serve() -> None:
    """Запускает gRPC-сервер проектов и держит его, пока процесс не остановят."""
    server = grpc.aio.server()
    projects_pb2_grpc.add_ProjectsServiceServicer_to_server(
        ProjectsServicer(session_factory, settings.allow_internal_urls), server
    )
    address = f"{settings.grpc_host}:{settings.grpc_port}"
    server.add_insecure_port(address)
    await server.start()
    logger.info("projects gRPC слушает %s", address)
    await server.wait_for_termination()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(serve())
