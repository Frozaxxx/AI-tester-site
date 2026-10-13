from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import grpc
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from app.api.v1.auth import router as auth_router
from app.clients.auth import AuthClient
from app.config import settings
from app.exceptions import GatewayError


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Подключается к auth и Redis при старте и закрывает соединения при остановке."""
    channel = grpc.aio.insecure_channel(settings.auth_grpc_address)
    app.state.auth_client = AuthClient(channel)
    app.state.redis = Redis.from_url(settings.redis_url, decode_responses=True)
    app.state.public_key = await app.state.auth_client.get_public_key()
    yield
    await channel.close()
    await app.state.redis.aclose()


app = FastAPI(title="AI-tester gateway", lifespan=lifespan)
app.include_router(auth_router, prefix="/api/v1")


@app.exception_handler(GatewayError)
async def gateway_error_handler(request: Request, exc: GatewayError) -> JSONResponse:
    """Отдаёт ошибку клиенту в виде JSON с нужным статусом."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error_code": exc.error_code, "message": exc.message},
    )


@app.get("/health", include_in_schema=False)
async def health() -> dict[str, str]:
    """Сообщает, что gateway работает."""
    return {"status": "ok"}
