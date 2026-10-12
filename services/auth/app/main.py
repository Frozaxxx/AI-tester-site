import asyncio
import logging

import grpc

from app.api.servicer import AuthServicer
from app.config import settings
from app.grpc_gen import auth_pb2_grpc
from app.infra.database.connection import session_factory
from app.infra.redis import redis_client

logger = logging.getLogger("auth")


async def serve() -> None:
    """Запускает gRPC-сервер авторизации и держит его, пока процесс не остановят."""
    server = grpc.aio.server()
    auth_pb2_grpc.add_AuthServiceServicer_to_server(
        AuthServicer(session_factory, redis_client), server
    )
    address = f"{settings.grpc_host}:{settings.grpc_port}"
    server.add_insecure_port(address)
    await server.start()
    logger.info("auth gRPC слушает %s", address)
    await server.wait_for_termination()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(serve())
